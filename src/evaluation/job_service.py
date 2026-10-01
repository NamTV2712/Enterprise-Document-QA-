"""Bounded native evaluation worker over DATA-004, never a public publisher."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from src.evaluation.frozen_job_plan import (
    FrozenPlanError, assert_runtime_binding, creation_request_fingerprint, freeze_plan,
    registered_artifact_bytes, validate_artifact,
)
from src.evaluation.generation_checkpoint import DEFAULT_GENERATION_PROMPT_TEMPLATE, build_evidence_context, sha256_text
from src.evaluation.job_store import EvaluationBudgetExhausted, EvaluationJobStore, EvaluationStoreError
from src.evaluation.native_protocol import NativeCaseInput, NativeReportBinding, NativeProtocolError, build_native_report, evaluate_case
from src.evaluation.phase2_runtime import (
    UsageTracker, build_production_judge_prompt, generation_pool_keys,
    judging_pool_keys, make_answer_completion_postprocessor,
    make_generation_call, make_judge_call,
)
from src.generation.generator import Generator
from src.generation.prompt_contracts import answer_completion_contract_for_question
from src.retrieval.canonical_json import canonical_json_bytes
from src.workspace.jobs import (
    DurableJob, JobConflictError, JobNotFoundError, JobState,
    JobTransitionError, SQLiteJobRepository,
)


EVALUATION_JOB_TYPE = "frozen_native_evaluation"
EVALUATION_STEPS = ("execute_cases", "aggregate_report")
_METRIC_IDS = (
    "native.faithfulness", "native.answer_relevancy", "native.context_precision",
    "native.citation_index_validity", "native.keyword_recall_proxy", "native.fallback_correctness",
)


class EvaluationRequestError(ValueError):
    """A bounded evaluation creation request is invalid."""


class _Cancelled(Exception):
    pass


class _ProviderFailed(Exception):
    pass


class _ReportFailed(Exception):
    pass


class EvaluationJobService:
    def __init__(
        self,
        repository: SQLiteJobRepository,
        *,
        artifact_loader: Callable[[str], bytes] = registered_artifact_bytes,
        provider_factory: Callable[[str], tuple[Callable[[str], str], Callable[[str], dict[str, Any]]]] | None = None,
    ) -> None:
        self.repository = repository
        self.store = EvaluationJobStore(repository.database)
        self.artifact_loader = artifact_loader
        self._uses_runtime_provider = provider_factory is None
        self.provider_factory = provider_factory or self._provider_factory

    @staticmethod
    def _provider_factory(model: str) -> tuple[Callable[[str], str], Callable[[str], dict[str, Any]]]:
        tracker = UsageTracker()
        generation = Generator(model=model, api_keys=generation_pool_keys(), client_max_retries=0)
        judging = Generator(model=model, api_keys=judging_pool_keys(), client_max_retries=0)
        return (
            make_generation_call(generation, tracker, transport_retries=0),
            make_judge_call(judging, tracker, transport_retries=0),
        )

    def create(
        self, *, artifact_id: str, engine: str, metrics: list[str], mode: str,
        budget: int, idempotency_key: str,
    ) -> DurableJob:
        if engine != "native" or mode != "provider_backed" or len(metrics) != len(_METRIC_IDS) or set(metrics) != set(_METRIC_IDS):
            raise EvaluationRequestError("only the complete native provider-backed metric set is registered")
        existing = self.repository.find_idempotent_job("evaluation", idempotency_key)
        if existing is not None:
            if (existing.job_type != EVALUATION_JOB_TYPE
                    or existing.payload.get("request_fingerprint") != creation_request_fingerprint(artifact_id, budget)):
                raise JobConflictError("idempotency key was already used for a different evaluation request")
            return existing
        if self._uses_runtime_provider and (not generation_pool_keys() or not judging_pool_keys()):
            raise EvaluationRequestError("configured generation and judge credentials are required")
        content = self.artifact_loader(artifact_id)
        snapshot = freeze_plan(artifact_id, content, budget)
        digest = self.store.register_artifact(content)
        if digest != snapshot["artifact_digest"]:
            raise EvaluationStoreError("registered artifact identity changed during freezing")
        return self.repository.create_job(
            namespace="evaluation", job_type=EVALUATION_JOB_TYPE,
            idempotency_key=idempotency_key,
            configuration_fingerprint=snapshot["snapshot_digest"].split(":", 1)[1],
            payload=snapshot,
            artifact_references=(f"frozen-artifact-{digest.split(':', 1)[1]}",),
            steps=EVALUATION_STEPS,
        )

    def _job(self, job_id: str) -> DurableJob:
        job = self.repository.get_job(job_id)
        if job.namespace != "evaluation" or job.job_type != EVALUATION_JOB_TYPE:
            raise JobNotFoundError("evaluation job does not exist")
        return job

    def get(self, job_id: str) -> dict[str, Any]:
        job = self._job(job_id)
        report = self.store.report(job_id)
        return self._view(job, report_digest=report.digest if report else None)

    def list(self, *, state: JobState | None, page: int, page_size: int) -> dict[str, Any]:
        rows = self.repository.list_jobs(
            namespace="evaluation", state=state, limit=page_size, offset=(page - 1) * page_size,
        )
        jobs = [job for job in rows.items if job.job_type == EVALUATION_JOB_TYPE]
        views = []
        for job in jobs:
            report = self.store.report(job.job_id)
            views.append(self._view(job, report_digest=report.digest if report else None))
        return {"items": views, "total": rows.total, "page": page, "page_size": page_size}

    def results(self, job_id: str, *, page: int, page_size: int) -> dict[str, Any]:
        self._job(job_id)
        cases, total = self.store.list_cases(job_id, limit=page_size, offset=(page - 1) * page_size)
        report = self.store.report(job_id)
        return {
            "job_id": job_id, "items": cases, "total": total, "page": page, "page_size": page_size,
            "report_status": report.status if report else None,
            "report_digest": report.digest if report else None,
            "metric_definitions": [asdict(item) | {"required_inputs": list(item.required_inputs)} for item in report.metric_definitions] if report else [],
            "aggregates": [asdict(item) for item in report.aggregates] if report else [],
        }

    def cancel(self, job_id: str, *, expected_revision: int) -> dict[str, Any]:
        job = self._job(job_id)
        updated = self.repository.request_cancellation(job_id, expected_revision=expected_revision)
        return self._view(updated)

    def events(self, job_id: str, *, after_sequence: int) -> tuple[dict[str, Any], ...]:
        self._job(job_id)
        return tuple(asdict(event) for event in self.repository.list_events(job_id, after_sequence=after_sequence, limit=100))

    def _view(self, job: DurableJob, *, report_digest: str | None = None) -> dict[str, Any]:
        snapshot = job.payload
        return {
            "id": job.job_id, "state": job.state, "revision": job.revision,
            "created_at": job.created_at, "updated_at": job.updated_at,
            "started_at": job.started_at, "finished_at": job.finished_at,
            "cancellation_requested_at": job.cancellation_requested_at,
            "configuration_fingerprint": job.configuration_fingerprint,
            "frozen": snapshot, "progress": asdict(job.progress),
            "steps": [asdict(step) for step in job.steps],
            "artifact_references": list(job.artifact_references),
            "budget_consumed": self.store.attempted_count(job.job_id),
            "publication_status": "not_published",
            "report_digest": report_digest,
            "result": job.result,
            "failure": {"code": job.failure_code, "message": job.failure_message} if job.failure_code else None,
        }

    def _check_cancel(self, job_id: str) -> None:
        if self._job(job_id).state == "cancelling":
            raise _Cancelled

    def _attempt(self, job_id: str, case_id_value: str, phase: str, invoke: Callable[[], Any]) -> Any:
        self._check_cancel(job_id)
        self.store.reserve_attempt(job_id, case_id_value, phase)
        try:
            return invoke()
        except Exception as error:  # provider details are never persisted
            raise _ProviderFailed from error

    def _finish_failure(self, job_id: str, code: str, message: str) -> None:
        """Resolve a cancellation/failed-terminal race without retrying work."""
        for _ in range(3):
            current = self._job(job_id)
            try:
                if current.state == "cancelling":
                    self.repository.acknowledge_cancellation(job_id, expected_revision=current.revision)
                elif current.state == "running":
                    self.repository.transition_job(
                        job_id, expected_revision=current.revision, target_state="failed",
                        failure_code=code, failure_message=message,
                    )
                return
            except JobConflictError:
                continue
        raise JobConflictError("evaluation terminal revision conflict")

    def run(self, job_id: str) -> None:
        """Claim a queued job once; queued idempotent replays may re-dispatch safely."""
        job = self._job(job_id)
        if job.state != "queued":
            return
        try:
            job = self.repository.transition_job(job_id, expected_revision=job.revision, target_state="running")
        except (JobConflictError, JobTransitionError):
            return
        try:
            snapshot = dict(job.payload)
            assert_runtime_binding(snapshot)
            try:
                content = self.store.artifact(snapshot["artifact_digest"])
            except EvaluationStoreError as error:
                raise FrozenPlanError("frozen artifact is unavailable or corrupt") from error
            artifact = validate_artifact(content, verify_dataset=False)
            cases = artifact["cases"]
            if ["sha256:" + hashlib.sha256(canonical_json_bytes(case)).hexdigest() for case in cases] != snapshot["case_hashes"]:
                raise FrozenPlanError("frozen case identity changed")
            binding = NativeReportBinding(**snapshot["binding"])
            try:
                generate, judge = self.provider_factory(binding.generator_model_id)
            except Exception as error:
                raise _ProviderFailed from error
            job = self.repository.transition_step(
                job_id, job.steps[0].step_id, expected_job_revision=job.revision,
                expected_step_revision=job.steps[0].revision, target_state="running",
            )
            job = self.repository.report_progress(
                job_id, expected_revision=job.revision, stage="execute_cases", current=0, total=len(cases),
            )
            for ordinal, case in enumerate(cases):
                self._check_cancel(job_id)
                identifier = snapshot["case_ids"][ordinal]
                context = build_evidence_context(case)
                if sha256_text(context) != snapshot["context_hashes"][ordinal]:
                    raise FrozenPlanError("frozen rendered evidence changed")
                question = case["question"]
                prompt = DEFAULT_GENERATION_PROMPT_TEMPLATE.format(
                    context_blocks=context, question=question,
                    answer_focus_contract=answer_completion_contract_for_question(question),
                )
                draft = self._attempt(job_id, identifier, "generation", lambda: generate(prompt))

                def corrected_call(correction_prompt: str) -> str:
                    return self._attempt(
                        job_id, identifier, "correction",
                        lambda: generate(correction_prompt),
                    )

                answer = make_answer_completion_postprocessor(corrected_call)(question, context, draft)
                judge_prompt = build_production_judge_prompt(question, answer, context, case["ground_truth"])
                raw_scores = self._attempt(job_id, identifier, "judging", lambda: judge(judge_prompt))
                scores = {
                    "native.faithfulness": raw_scores["faithfulness"],
                    "native.answer_relevancy": raw_scores["answer_relevancy"],
                    "native.context_precision": raw_scores["context_precision"],
                }
                context_hash = sha256_text(context)
                native_input = NativeCaseInput(
                    case_id=identifier, answer=answer, rendered_context=context,
                    ground_truth=case["ground_truth"],
                    required_keywords=tuple(case["required_keywords"]),
                    expects_fallback=case["expects_fallback"], judge_scores=scores,
                    generation_context_sha256=context_hash, judge_context_sha256=context_hash,
                    generation_binding=binding.generation_binding, judge_binding=binding.judge_binding,
                )
                result = evaluate_case(native_input, binding)
                self.store.commit_case(job_id, ordinal, identifier, {
                    "case_id": identifier, "question": question,
                    "input": asdict(native_input), "metrics": [asdict(metric) for metric in result.metrics],
                    "judge_prompt_sha256": sha256_text(judge_prompt),
                })
                self._check_cancel(job_id)
                current = self._job(job_id)
                job = self.repository.report_progress(
                    job_id, expected_revision=current.revision, stage="execute_cases",
                    current=ordinal + 1, total=len(cases),
                )
            job = self.repository.transition_step(
                job_id, job.steps[0].step_id, expected_job_revision=job.revision,
                expected_step_revision=job.steps[0].revision, target_state="succeeded",
            )
            job = self.repository.transition_step(
                job_id, job.steps[1].step_id, expected_job_revision=job.revision,
                expected_step_revision=job.steps[1].revision, target_state="running",
            )
            rows = self.store.all_cases(job_id)
            if len(rows) != len(cases):
                raise EvaluationStoreError("frozen cases are incomplete")
            native_inputs = [NativeCaseInput(**{
                **row["input"], "required_keywords": tuple(row["input"]["required_keywords"]),
            }) for row in rows]
            try:
                report = build_native_report(job_id, native_inputs, binding)
                if report.status != "complete":
                    raise _ReportFailed("native report is incomplete")
                self.store.commit_report(job_id, report)
            except (NativeProtocolError, EvaluationStoreError) as error:
                raise _ReportFailed from error
            self._check_cancel(job_id)
            job = self.repository.transition_step(
                job_id, job.steps[1].step_id, expected_job_revision=job.revision,
                expected_step_revision=job.steps[1].revision, target_state="succeeded",
            )
            self.repository.transition_job(
                job_id, expected_revision=job.revision, target_state="succeeded",
                result={"report_digest": report.digest, "budget_consumed": self.store.attempted_count(job_id)},
            )
        except _Cancelled:
            self._finish_failure(job_id, "infrastructure_failure", "Evaluation worker stopped")
        except Exception as error:  # persist only fixed, safe error categories
            current = self._job(job_id)
            if current.state == "cancelling":
                self._finish_failure(job_id, "infrastructure_failure", "Evaluation worker stopped")
                return
            if current.state != "running":
                return
            chain: list[BaseException] = []
            cause: BaseException | None = error
            while cause is not None and len(chain) < 4:
                chain.append(cause)
                cause = cause.__cause__
            if any(isinstance(item, EvaluationBudgetExhausted) for item in chain):
                code, message = "budget_exhausted", "Frozen provider attempt budget exhausted"
            elif any(isinstance(item, FrozenPlanError) for item in chain):
                code, message = "invalid_frozen_snapshot", "Frozen evaluation binding is invalid"
            elif any(isinstance(item, _ProviderFailed) for item in chain):
                code, message = "provider_failure", "Evaluation provider call failed"
            elif any(isinstance(item, _ReportFailed) for item in chain):
                code, message = "report_validation_failure", "Native evaluation report did not validate"
            elif isinstance(error, (KeyError, TypeError, ValueError)):
                code, message = "case_failure", "Evaluation case result is invalid"
            else:
                code, message = "infrastructure_failure", "Evaluation worker failed"
            self._finish_failure(job_id, code, message)
