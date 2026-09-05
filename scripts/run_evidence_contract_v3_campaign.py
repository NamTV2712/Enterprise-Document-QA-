"""Run the pre-registered Evidence Contract v3 candidate campaign.

The runner is deliberately separate from the production Phase 2 command. It
uses the frozen V7 context, an opt-in v3 renderer, a durable 60-request ledger,
and fresh output paths. Resume never reissues an operation whose transport
outcome is unknown.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable

from scripts.diagnostics.evidence_contract_v3_manifest import (
    CAMPAIGN_ID as DEFAULT_CAMPAIGN_ID,
    MAX_REQUESTS,
    build_manifest,
    campaign_output_paths,
    verify_manifest,
)
from scripts.run_answerability_stability_sentinel import (
    ARTIFACT_PATH,
    EVAL_MODEL,
    EXPECTED_ARTIFACT_FINGERPRINT,
    EXPECTED_REFERENCE_SHA256,
    REFERENCE_PATH,
    SENTINEL_QUESTIONS,
    TARGET_QUESTION,
    RISK_CONTROL_QUESTION,
    OUT_OF_CORPUS_QUESTION,
    load_bound_artifact,
)
from scripts.diagnostics.answerability_stability_v1_reproducibility import (
    build_report,
    validate_report,
)
from src.evaluation.context_packing import (
    CONTEXT_STRATEGY_SELECTIVE_V7,
    render_case_context,
)
from src.evaluation.evidence_contract_v3 import (
    PROFILE_FINGERPRINT,
    build_judge_prompt,
    calibration_cases,
    compute_generation_binding_v3,
    compute_judge_binding_v3,
    reference_for,
)
from src.evaluation.evidence_provenance import file_sha256, read_jsonl
from src.evaluation.generation_checkpoint import (
    DEFAULT_GENERATION_PROMPT_TEMPLATE,
    GENERATION_CONTEXT_BUILDER_FINGERPRINT,
    sha256_text,
)
from src.evaluation.phase2_runtime import (
    GENERATION_SYSTEM_PROMPT_FINGERPRINT,
    JUDGE_CONTEXT_BUILDER_FINGERPRINT,
    PHASE2_MAX_TOKENS,
    UsageTracker,
    generation_pool_keys,
    judging_pool_keys,
    make_generation_call,
    make_judge_call,
)
from src.evaluation.test_set import TEST_SET
from src.generation.answer_completion import ANSWER_COMPLETION_FINGERPRINT
from src.evaluation.answer_contract import audit_answer
from src.generation.comparative_answer_renderer import (
    COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT,
    render_dependency_comparison_v3,
)
from src.generation.comparative_answerability import (
    COMPARATIVE_ANSWERABILITY_V3_FINGERPRINT,
    assess_comparative_answerability_v3,
)
from src.generation.generator import Generator
from src.generation.risk_answer_shape import (
    RISK_ANSWER_SHAPE_FINGERPRINT,
    render_deterministic_risk_answer,
)
from src.evaluation.request_ledger import (
    CampaignIncomplete,
    ProviderOperationError,
    RequestLedger,
)


class CampaignSemanticFailure(RuntimeError):
    """A registered semantic protocol check failed after complete execution."""


# Checkpoint writes are kept separate from the request ledger so their schema
# remains explicit and independently auditable.
def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


CAMPAIGN_ROOT = Path("data/eval_artifacts")
DIAGNOSTIC_ROOT = Path("data/diagnostics")
CAMPAIGN_ID = DEFAULT_CAMPAIGN_ID
LEDGER_PATH = DIAGNOSTIC_ROOT / "evidence_contract_v3_retry_disabled_campaign_ledger.jsonl"
CALIBRATION_OUTPUT = DIAGNOSTIC_ROOT / "evidence_contract_v3_retry_disabled_calibration.json"
LEGACY_OUTPUT = DIAGNOSTIC_ROOT / "evidence_contract_v3_retry_disabled_legacy_comparison.json"
STATUS_OUTPUT = DIAGNOSTIC_ROOT / "evidence_contract_v3_retry_disabled_campaign_status.json"
REPRO_OUTPUT = DIAGNOSTIC_ROOT / "evidence_contract_v3_retry_disabled_reproducibility.json"
RUN_CONFIG = {
    "r1": {
        "run_id": "evidence-contract-v3-r1",
        "generation": CAMPAIGN_ROOT / "evidence_contract_v3_retry_disabled_r1_generation.jsonl",
        "judge": CAMPAIGN_ROOT / "evidence_contract_v3_retry_disabled_r1_judge.jsonl",
        "report": CAMPAIGN_ROOT / "evidence_contract_v3_retry_disabled_r1.json",
    },
    "r2": {
        "run_id": "evidence-contract-v3-r2",
        "generation": CAMPAIGN_ROOT / "evidence_contract_v3_retry_disabled_r2_generation.jsonl",
        "judge": CAMPAIGN_ROOT / "evidence_contract_v3_retry_disabled_r2_judge.jsonl",
        "report": CAMPAIGN_ROOT / "evidence_contract_v3_retry_disabled_r2.json",
    },
}


def configure_campaign(campaign_id: str) -> None:
    """Switch all campaign-owned paths and run IDs to one fresh identity."""
    global CAMPAIGN_ID, LEDGER_PATH, CALIBRATION_OUTPUT, LEGACY_OUTPUT, STATUS_OUTPUT, REPRO_OUTPUT, RUN_CONFIG
    if not campaign_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in campaign_id):
        raise ValueError("campaign id must contain only letters, numbers, '_' or '-'")
    CAMPAIGN_ID = campaign_id
    prefix = campaign_id
    LEDGER_PATH = DIAGNOSTIC_ROOT / f"{prefix}_campaign_ledger.jsonl"
    CALIBRATION_OUTPUT = DIAGNOSTIC_ROOT / f"{prefix}_calibration.json"
    LEGACY_OUTPUT = DIAGNOSTIC_ROOT / f"{prefix}_legacy_comparison.json"
    REPRO_OUTPUT = DIAGNOSTIC_ROOT / f"{prefix}_reproducibility.json"
    STATUS_OUTPUT = DIAGNOSTIC_ROOT / f"{prefix}_campaign_status.json"
    RUN_CONFIG = {
        "r1": {
            "run_id": "evidence-contract-v3-r1" if campaign_id == DEFAULT_CAMPAIGN_ID else f"{campaign_id}-r1",
            "generation": CAMPAIGN_ROOT / f"{prefix}_r1_generation.jsonl",
            "judge": CAMPAIGN_ROOT / f"{prefix}_r1_judge.jsonl",
            "report": CAMPAIGN_ROOT / f"{prefix}_r1.json",
        },
        "r2": {
            "run_id": "evidence-contract-v3-r2" if campaign_id == DEFAULT_CAMPAIGN_ID else f"{campaign_id}-r2",
            "generation": CAMPAIGN_ROOT / f"{prefix}_r2_generation.jsonl",
            "judge": CAMPAIGN_ROOT / f"{prefix}_r2_judge.jsonl",
            "report": CAMPAIGN_ROOT / f"{prefix}_r2.json",
        },
    }


def _same_file_identity(left: Path, right: Path) -> bool:
    """Accept a registered path plus a safe symlink/hardlink alias."""
    try:
        if left.resolve() == right.resolve():
            return True
        return left.exists() and right.exists() and os.path.samefile(left, right)
    except OSError:
        return False


def _transport_is_retryable(error: Exception, status_code: int | None) -> bool:
    return (
        status_code in {408, 429, 500, 502, 503, 504}
        or isinstance(error, (TimeoutError, ConnectionError))
        or type(error).__name__ in {"APITimeoutError", "APIConnectionError"}
    )


def _read_partial(path: Path, expected: set[str]) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    records, errors = read_jsonl(path)
    if errors:
        raise CampaignIncomplete("; ".join(errors))
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        question = record.get("question")
        if not isinstance(question, str) or question not in expected:
            raise CampaignIncomplete(f"checkpoint has an unknown question: {question!r}")
        if question in indexed:
            raise CampaignIncomplete(f"checkpoint has duplicate question: {question}")
        indexed[question] = record
    return indexed


def _mean(cases: dict[str, dict[str, Any]]) -> dict[str, float]:
    keys = ("faithfulness", "answer_relevancy", "context_precision")
    return {
        key: round(sum(float(case["scores"][key]) for case in cases.values()) / len(cases), 4)
        for key in keys
    }


def _reference_scores() -> dict[str, dict[str, float]]:
    if file_sha256(REFERENCE_PATH) != EXPECTED_REFERENCE_SHA256:
        raise CampaignIncomplete("protected official result hash changed")
    payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    result: dict[str, dict[str, float]] = {}
    for case in payload.get("cases", []):
        if not isinstance(case, dict) or case.get("question") not in SENTINEL_QUESTIONS:
            continue
        scores = case.get("scores")
        if isinstance(scores, dict) and all(isinstance(scores.get(key), (int, float)) for key in ("faithfulness", "answer_relevancy", "context_precision")):
            result[case["question"]] = {key: float(scores[key]) for key in ("faithfulness", "answer_relevancy", "context_precision")}
    if set(result) != set(SENTINEL_QUESTIONS):
        raise CampaignIncomplete("protected official result lacks sentinel scores")
    return result


def _context_rows(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_question = {case["question"]: case for case in artifact["cases"]}
    test_cases = {case.question: case for case in TEST_SET}
    rows: dict[str, dict[str, Any]] = {}
    for question in SENTINEL_QUESTIONS:
        payload = by_question[question]
        test_case = test_cases[question]
        context = render_case_context(
            payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        repeat = render_case_context(
            payload,
            required_keywords=test_case.required_keywords,
            strategy=CONTEXT_STRATEGY_SELECTIVE_V7,
        )
        rows[question] = {
            "context": context,
            "context_sha256": sha256_text(context),
            "source_count": context.count("[Source "),
            "context_deterministic": context == repeat,
            "context_fingerprint": GENERATION_CONTEXT_BUILDER_FINGERPRINT,
        }
    return rows


def _provider_wrappers(ledger: RequestLedger) -> tuple[Callable[[str, str, str], str], Callable[[str, str, str], dict[str, Any]], UsageTracker]:
    tracker = UsageTracker()
    generation = Generator(
        model=EVAL_MODEL,
        api_keys=generation_pool_keys(),
        client_max_retries=0,
    )
    judge = Generator(
        model=EVAL_MODEL,
        api_keys=judging_pool_keys(),
        client_max_retries=0,
    )
    generation_provider = make_generation_call(generation, tracker, transport_retries=0)
    judge_provider = make_judge_call(judge, tracker, transport_retries=0)

    def generate(run_id: str, operation: str, prompt: str) -> str:
        def send() -> dict[str, Any]:
            try:
                content = generation_provider(prompt)
            except Exception as error:
                metadata = dict(generation.last_transport_metadata)
                raise ProviderOperationError(
                    metadata.get("error_type", type(error).__name__),
                    metadata.get("status_code"),
                    metadata,
                    retryable=_transport_is_retryable(
                        error, metadata.get("status_code")
                    ),
                ) from error
            return {
                "content": content,
                "provider": dict(generation.last_transport_metadata),
            }

        response = ledger.call(
            operation=operation,
            run_id=run_id,
            request_sha256=sha256_text(prompt),
            send=send,
        )
        content = response.get("content") if isinstance(response, dict) else None
        if not isinstance(content, str):
            raise CampaignIncomplete("ledger generation response is malformed")
        return content

    def score(run_id: str, operation: str, prompt: str) -> dict[str, Any]:
        def send() -> dict[str, Any]:
            try:
                scores = judge_provider(prompt)
            except Exception as error:
                metadata = dict(judge.last_transport_metadata)
                raise ProviderOperationError(
                    metadata.get("error_type", type(error).__name__),
                    metadata.get("status_code"),
                    metadata,
                    retryable=_transport_is_retryable(
                        error, metadata.get("status_code")
                    ),
                ) from error
            return {
                "scores": scores,
                "provider": dict(judge.last_transport_metadata),
            }

        response = ledger.call(
            operation=operation,
            run_id=run_id,
            request_sha256=sha256_text(prompt),
            send=send,
        )
        scores = response.get("scores") if isinstance(response, dict) else None
        if not isinstance(scores, dict):
            raise CampaignIncomplete("ledger judge response is malformed")
        return scores

    return generate, score, tracker


def _candidate_answer(question: str, context: str, draft: str) -> str:
    if question == TARGET_QUESTION:
        rendered = render_dependency_comparison_v3(question, context)
        if rendered:
            return rendered
    if question == RISK_CONTROL_QUESTION:
        rendered = render_deterministic_risk_answer(question, context)
        if rendered:
            return rendered
    return draft


def _generation_binding_inputs(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact_path = ARTIFACT_PATH
    return {
        "artifact_sha256": file_sha256(artifact_path),
        "artifact_schema_version": int(artifact["schema_version"]),
        "model": EVAL_MODEL,
        "prompt_template_sha256": sha256_text(DEFAULT_GENERATION_PROMPT_TEMPLATE),
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V7,
        "context_builder_fingerprint": GENERATION_CONTEXT_BUILDER_FINGERPRINT,
        "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        "renderer_fingerprint": COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT,
        "system_prompt_sha256": GENERATION_SYSTEM_PROMPT_FINGERPRINT,
    }


def _run_replicate(
    name: str,
    artifact: dict[str, Any],
    ledger: RequestLedger,
    generate: Callable[[str, str, str], str],
    score: Callable[[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    config = RUN_CONFIG[name]
    run_id = config["run_id"]
    contexts = _context_rows(artifact)
    binding_inputs = _generation_binding_inputs(artifact)
    binding = compute_generation_binding_v3(**binding_inputs)
    expected = set(SENTINEL_QUESTIONS)
    generations = _read_partial(config["generation"], expected)
    judges = _read_partial(config["judge"], expected)

    for question in SENTINEL_QUESTIONS:
        if question in generations:
            if generations[question].get("binding") != binding or generations[question].get("run_id") != run_id:
                raise CampaignIncomplete(f"generation checkpoint binding/run mismatch: {question}")
            continue
        context = contexts[question]["context"]
        prompt = DEFAULT_GENERATION_PROMPT_TEMPLATE.format(
            context_blocks=context,
            question=question,
            answer_focus_contract="",
        )
        draft = generate(run_id, f"generation:{name}:{sha256_text(question)}", prompt)
        answer = _candidate_answer(question, context, draft)
        record = {
            "schema_version": 1,
            "question": question,
            "run_id": run_id,
            "status": "OK",
            "answer": answer,
            "model": EVAL_MODEL,
            "binding": binding,
            "binding_inputs": binding_inputs,
            "prompt_sha256": sha256_text(prompt),
            "context_sha256": contexts[question]["context_sha256"],
            "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V7,
            "context_builder_fingerprint": GENERATION_CONTEXT_BUILDER_FINGERPRINT,
            "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
            "renderer_fingerprint": COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT,
            "system_prompt_sha256": GENERATION_SYSTEM_PROMPT_FINGERPRINT,
            "upstream_artifact_sha256": binding_inputs["artifact_sha256"],
        }
        _append_jsonl(config["generation"], record)
        generations[question] = record

    for question in SENTINEL_QUESTIONS:
        if question in judges:
            if judges[question].get("run_id") != run_id:
                raise CampaignIncomplete(f"judge checkpoint run mismatch: {question}")
            continue
        answer = generations[question]["answer"]
        context = contexts[question]["context"]
        reference = reference_for(question)
        prompt = build_judge_prompt(question, answer, context, reference)
        scores = score(run_id, f"judge:{name}:{sha256_text(question)}", prompt)
        judge_binding = compute_judge_binding_v3(
            generation_binding=binding,
            question=question,
            answer=answer,
            context=context,
            reference=reference,
            judge_model=EVAL_MODEL,
            prompt_sha256=sha256_text(prompt),
            judge_max_tokens=PHASE2_MAX_TOKENS,
        )
        record = {
            "schema_version": 1,
            "question": question,
            "run_id": run_id,
            "status": "OK",
            "scores": scores,
            "binding": judge_binding,
            "model": EVAL_MODEL,
            "judge_max_tokens": PHASE2_MAX_TOKENS,
            "prompt_sha256": sha256_text(prompt),
            "context_sha256": sha256_text(context),
            "reference_sha256": sha256_text(reference),
            "profile_fingerprint": PROFILE_FINGERPRINT,
            "judge_context_fingerprint": JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        }
        _append_jsonl(config["judge"], record)
        judges[question] = record

    reference_scores = _reference_scores()
    cases: dict[str, dict[str, Any]] = {}
    for question in SENTINEL_QUESTIONS:
        answer = generations[question]["answer"]
        context = contexts[question]["context"]
        source_texts = [block.split("\n", 1)[1] for block in context.split("[Source ")[1:] if "\n" in block]
        audit = audit_answer(answer, source_texts)
        deterministic: dict[str, Any] = {
            "citation_passed": not (audit.uncited_answer or audit.malformed_line_citations or audit.out_of_range_citations or audit.unsupported_numeric_claims),
            "fallback": audit.fallback_answer,
        }
        if question == TARGET_QUESTION:
            assessment = assess_comparative_answerability_v3(question, context, answer)
            deterministic.update({"v3_status": assessment.status, "v3_passed": assessment.passed, "unsupported_ranking": assessment.unsupported_ranking})
        if question == RISK_CONTROL_QUESTION:
            from src.generation.risk_answer_shape import assess_risk_answer_shape
            risk = assess_risk_answer_shape(question, context, answer)
            deterministic.update({"risk_shape_passed": risk.passed, "risk_shape_fingerprint": RISK_ANSWER_SHAPE_FINGERPRINT})
        cases[question] = {
            "question": question,
            "answer": answer,
            "scores": judges[question]["scores"],
            "deterministic": deterministic,
        }

    metrics = _mean(cases)
    controls = [question for question in SENTINEL_QUESTIONS if question not in {TARGET_QUESTION, RISK_CONTROL_QUESTION, OUT_OF_CORPUS_QUESTION}]
    gates = {
        "all_generation_ok": len(generations) == len(SENTINEL_QUESTIONS) and all(row.get("status") == "OK" for row in generations.values()),
        "all_judge_ok": len(judges) == len(SENTINEL_QUESTIONS) and all(row.get("status") == "OK" for row in judges.values()),
        "all_faithfulness_exact_one": all(cases[q]["scores"].get("faithfulness") == 1.0 for q in SENTINEL_QUESTIONS),
        "dependency_answer_relevancy_exact_one": cases[TARGET_QUESTION]["scores"].get("answer_relevancy") == 1.0,
        "risk_answer_relevancy_floor": cases[RISK_CONTROL_QUESTION]["scores"].get("answer_relevancy", 0) >= 0.95,
        "controls_answer_relevancy_drift_bounded": all(cases[q]["scores"].get("answer_relevancy", 0) >= reference_scores[q]["answer_relevancy"] - 0.05 for q in controls),
        "out_of_corpus_fallback_preserved": "could not find sufficient information" in cases[OUT_OF_CORPUS_QUESTION]["answer"].casefold(),
        "aggregate_faithfulness_exact_one": metrics["faithfulness"] == 1.0,
        "aggregate_answer_relevancy_floor": metrics["answer_relevancy"] >= 0.975,
        "aggregate_context_precision_floor": metrics["context_precision"] >= 0.67,
    }
    report = {
        "schema_version": 3,
        "audit": "evidence_contract_v3_sentinel",
        "evaluation_profile": "evidence-contract-v3",
        "official": False,
        "campaign_id": CAMPAIGN_ID,
        "replicate_id": name,
        "run_id": run_id,
        "candidate_strategy": "selective_packed_v7_fact_generalization_candidate",
        "context_strategy": "selective_packed_v7_fact_generalization_candidate",
        "binding": binding,
        "render_context_strategy": CONTEXT_STRATEGY_SELECTIVE_V7,
        "sentinel_questions": list(SENTINEL_QUESTIONS),
        "artifact_path": str(ARTIFACT_PATH),
        "artifact_sha256": binding_inputs["artifact_sha256"],
        "artifact_fingerprint": artifact["fingerprints"]["artifact"],
        "context_builder_fingerprint": GENERATION_CONTEXT_BUILDER_FINGERPRINT,
        "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        "answerability_fingerprint": COMPARATIVE_ANSWERABILITY_V3_FINGERPRINT,
        "evidence_contract_fingerprint": PROFILE_FINGERPRINT,
        "reference_sha256": EXPECTED_REFERENCE_SHA256,
        "reference_scores": reference_scores,
        "context_rows": contexts,
        "cases": [cases[question] for question in SENTINEL_QUESTIONS],
        "metrics": metrics,
        "provider_complete": True,
        "stopped_reason": None,
        "checkpoint_provenance": {
            "generation_checkpoint": str(config["generation"]),
            "judge_checkpoint": str(config["judge"]),
            "generation_bindings": [binding],
            "judge_context_fingerprints": [JUDGE_CONTEXT_BUILDER_FINGERPRINT],
            "judge_bindings": sorted(judges[question]["binding"] for question in SENTINEL_QUESTIONS),
            "one_generation_binding": True,
            "one_judge_context_fingerprint": True,
        },
        "recomputed_gates": gates,
        "gates": gates,
        "passed": all(gates.values()),
    }
    config["report"].parent.mkdir(parents=True, exist_ok=True)
    config["report"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _run_calibration(ledger: RequestLedger, judge: Callable[[str, str, str], dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for round_number in (1, 2):
        for case in calibration_cases():
            prompt = build_judge_prompt(case["question"], case["answer"], case["context"], reference_for(case["question"]))
            scores = judge(
                f"calibration-{round_number}",
                f"calibration:{round_number}:{case['id']}",
                prompt,
            )
            expected = case["expected"]
            if expected.get("accept"):
                passed = scores.get("faithfulness", 0) >= expected.get("faithfulness_min", 1.0) and scores.get("answer_relevancy", 0) >= expected.get("answer_relevancy_min", 1.0)
            else:
                passed = scores.get("faithfulness", 1.0) <= expected.get("faithfulness_max", 1.0) or scores.get("answer_relevancy", 1.0) <= expected.get("answer_relevancy_max", 1.0)
            results.append({"round": round_number, "id": case["id"], "scores": scores, "expected": expected, "passed": passed})
    report = {
        "schema_version": 1,
        "campaign_id": CAMPAIGN_ID,
        "profile_fingerprint": PROFILE_FINGERPRINT,
        "cases": results,
        "provider_requests": len(results),
        "passed": len(results) == 12 and all(row["passed"] for row in results),
    }
    CALIBRATION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    CALIBRATION_OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not report["passed"]:
        raise CampaignSemanticFailure(
            "rubric calibration failed; sentinel stage was not started"
        )
    return report


def _run_legacy_comparison(
    reports: list[dict[str, Any]],
    ledger: RequestLedger,
    judge: Callable[[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    from src.evaluation.phase2_runtime import build_production_judge_prompt

    reference_payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    legacy_references = {case["question"]: case["ground_truth"] for case in reference_payload.get("cases", []) if case.get("question") in SENTINEL_QUESTIONS}
    rows: list[dict[str, Any]] = []
    for report in reports:
        run_id = report["run_id"]
        for case in report["cases"]:
            question = case["question"]
            context = report["context_rows"][question]["context"]
            prompt = build_production_judge_prompt(question, case["answer"], context, legacy_references[question])
            scores = judge(f"legacy-{report['replicate_id']}", f"legacy:{report['replicate_id']}:{sha256_text(question)}", prompt)
            rows.append({"run_id": run_id, "replicate_id": report["replicate_id"], "question": question, "answer_sha256": sha256_text(case["answer"]), "scores": scores})
    output = {"schema_version": 1, "campaign_id": CAMPAIGN_ID, "profile_fingerprint": PROFILE_FINGERPRINT, "rows": rows, "provider_requests": len(rows), "passed": len(rows) == 12}
    LEGACY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    LEGACY_OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def _write_campaign_status(
    execution_status: str,
    candidate_decision: str,
    stage: str,
    error: Exception | None,
    ledger: RequestLedger,
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "campaign_id": CAMPAIGN_ID,
                "execution_status": execution_status,
                "candidate_decision": candidate_decision,
                "stage": stage,
                "error_type": type(error).__name__ if error else None,
                "error": str(error) if error else None,
                "request_count": ledger.used,
                "request_limit": MAX_REQUESTS,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args(argv)
    if args.fresh:
        parser.error("--fresh is disabled; use a new --campaign-id to create a clean campaign")
    configure_campaign(args.campaign_id)
    manifest_path = args.manifest or (DIAGNOSTIC_ROOT / f"{CAMPAIGN_ID}_manifest.json")
    ledger_path = args.ledger or LEDGER_PATH
    registered_ledger_path = LEDGER_PATH
    if args.ledger and not _same_file_identity(ledger_path, registered_ledger_path):
        print(
            json.dumps(
                {
                    "status": "NO-GO",
                    "execution_status": "NOT_STARTED",
                    "candidate_decision": "UNDECIDED",
                    "error": "--ledger must reference the registered campaign ledger",
                    "registered_ledger": str(registered_ledger_path),
                    "requested_ledger": str(ledger_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    # The manifest is the immutable registration record and is expected to
    # exist before execution. Mutable outputs are what trigger collision checks.
    owned_paths = campaign_output_paths(CAMPAIGN_ID)
    protected_paths = (*owned_paths, ARTIFACT_PATH, REFERENCE_PATH)
    if any(_same_file_identity(manifest_path, path) for path in protected_paths):
        print(
            json.dumps(
                {
                    "status": "NO-GO",
                    "execution_status": "NOT_STARTED",
                    "candidate_decision": "UNDECIDED",
                    "error": "manifest path overlaps a protected artifact or campaign output",
                    "manifest": str(manifest_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    existing_paths = [path for path in owned_paths if path.exists()]
    if existing_paths and not args.resume:
        print(
            json.dumps(
                {
                    "status": "NO-GO",
                    "execution_status": "NOT_STARTED",
                    "candidate_decision": "UNDECIDED",
                    "error": "campaign outputs already exist; choose a new --campaign-id or pass --resume",
                    "existing_paths": [str(path) for path in existing_paths],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    if args.resume and manifest_path.exists():
        try:
            previous_status = json.loads(STATUS_OUTPUT.read_text(encoding="utf-8")) if STATUS_OUTPUT.exists() else {}
        except (OSError, ValueError) as error:
            print(json.dumps({"status": "NO-GO", "error": f"cannot inspect existing campaign status: {error}"}, indent=2))
            return 1
        if previous_status.get("execution_status") == "INCOMPLETE" or previous_status.get("status") == "INCOMPLETE":
            print(json.dumps({"status": "NO-GO", "error": "incomplete campaign cannot be resumed; use a new campaign id after provider authorization"}, indent=2))
            return 1
    if not manifest_path.exists():
        manifest = build_manifest(
            ARTIFACT_PATH,
            CAMPAIGN_ID,
            campaign_output_paths(CAMPAIGN_ID),
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_errors = verify_manifest(
        manifest_path,
        ARTIFACT_PATH,
        CAMPAIGN_ID,
        campaign_output_paths(CAMPAIGN_ID),
    )
    if manifest_errors:
        print(json.dumps({"status": "NO-GO", "manifest_errors": list(manifest_errors)}, indent=2))
        return 1
    ledger = RequestLedger(ledger_path, CAMPAIGN_ID, MAX_REQUESTS)
    stage = "calibration"
    try:
        artifact, _ = load_bound_artifact(ARTIFACT_PATH, EXPECTED_ARTIFACT_FINGERPRINT, CONTEXT_STRATEGY_SELECTIVE_V7)
        generate, judge, tracker = _provider_wrappers(ledger)
        calibration = _run_calibration(ledger, judge)
        stage = "sentinel-r1"
        r1 = _run_replicate("r1", artifact, ledger, generate, judge)
        stage = "sentinel-r2"
        r2 = _run_replicate("r2", artifact, ledger, generate, judge)
        stage = "legacy-comparison"
        legacy = _run_legacy_comparison([r1, r2], ledger, judge)
        stage = "reproducibility-verification"
        integrity = {
            "r1": list(validate_report(r1, RUN_CONFIG["r1"]["report"])),
            "r2": list(validate_report(r2, RUN_CONFIG["r2"]["report"])),
        }
        reproducibility = build_report(
            r1,
            r2,
            RUN_CONFIG["r1"]["report"],
            RUN_CONFIG["r2"]["report"],
        )
        reproducibility["campaign_id"] = CAMPAIGN_ID
        reproducibility["case_integrity_errors"] = integrity
        REPRO_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        REPRO_OUTPUT.write_text(
            json.dumps(reproducibility, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        stage = "complete"
        candidate_go = bool(
            r1["passed"]
            and r2["passed"]
            and not any(integrity.values())
            and reproducibility.get("passed") is True
            and ledger.used <= MAX_REQUESTS
        )
        output = {"schema_version": 2, "campaign_id": CAMPAIGN_ID, "status": "COMPLETE", "request_count": ledger.used, "request_limit": MAX_REQUESTS, "calibration": calibration, "replicates": [{"path": str(RUN_CONFIG["r1"]["report"]), "passed": r1["passed"]}, {"path": str(RUN_CONFIG["r2"]["report"]), "passed": r2["passed"]}], "legacy_comparison": str(LEGACY_OUTPUT), "reproducibility": str(REPRO_OUTPUT), "token_usage_totals": tracker.totals, "candidate_go": candidate_go}
        _write_campaign_status(
            "COMPLETE",
            "GO" if candidate_go else "NO-GO",
            stage,
            None if candidate_go else RuntimeError("one or more candidate gates failed"),
            ledger,
            STATUS_OUTPUT,
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0 if output["candidate_go"] else 1
    except CampaignSemanticFailure as error:
        _write_campaign_status(
            "COMPLETE",
            "NO-GO",
            stage,
            error,
            ledger,
            STATUS_OUTPUT,
        )
        print(json.dumps({"status": "COMPLETE", "candidate_decision": "NO-GO", "stage": stage, "error": str(error), "request_count": ledger.used, "request_limit": MAX_REQUESTS}, ensure_ascii=False, indent=2))
        return 1
    except CampaignIncomplete as error:
        _write_campaign_status(
            "INCOMPLETE",
            "UNDECIDED",
            stage,
            error,
            ledger,
            STATUS_OUTPUT,
        )
        print(json.dumps({"status": "INCOMPLETE", "stage": stage, "error": str(error), "request_count": ledger.used, "request_limit": MAX_REQUESTS}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
