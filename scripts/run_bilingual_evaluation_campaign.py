"""Run the bounded bilingual campaign when a provider window is available.

Without ``--execute`` this command only verifies the registered manifest and
prints the resume instructions. Provider execution is explicit, uses no SDK
retries, reserves every transport slot in a durable ledger, and writes
append-only checkpoints. A quota/transport interruption is INCOMPLETE; it is
never converted into a passing result. After a new provider window is granted,
start a new campaign id rather than mutating an incomplete campaign.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.diagnostics import bilingual_evaluation_manifest as protocol
from scripts.run_answerability_stability_sentinel import (
    ARTIFACT_PATH,
    EXPECTED_ARTIFACT_FINGERPRINT,
    load_bound_artifact,
)
from scripts.run_evaluation_phase2 import EVAL_MODEL
from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V7, render_case_context
from src.evaluation.evidence_contract_v3 import build_judge_prompt, calibration_cases, reference_for
from src.evaluation.evidence_provenance import read_jsonl
from src.evaluation.generation_checkpoint import sha256_text
from src.evaluation.phase2_runtime import (
    PHASE2_MAX_TOKENS,
    generation_pool_keys,
    judging_pool_keys,
    make_answer_completion_postprocessor,
)
from src.evaluation.provider_budget import ProviderBudgetLedger
from src.evaluation.request_ledger import CampaignIncomplete, ProviderOperationError, RequestLedger, read_records
from src.evaluation.test_set import TEST_SET
from configs.settings import settings
from src.generation.generator import Generator, system_prompt_for_language
from src.generation.provider_policy import configured_groq_keys
from src.generation.comparative_answer_renderer import (
    render_deterministic_growth_comparison,
    render_deterministic_international_risk_answer,
    render_dependency_comparison_v3_localized,
)
from src.generation.risk_answer_shape import render_deterministic_risk_answer_localized


BASE_REQUESTS = protocol.CALIBRATION_REQUESTS + protocol.SENTINEL_REQUESTS
BILINGUAL_RUBRIC = (
    "The answer must use the requested language while preserving company names, "
    "numbers, currencies, periods, scopes, and source citations. Do not reward a "
    "translation that introduces a claim absent from the supplied evidence. "
    "A bounded limitation is acceptable when the evidence is not comparable."
)
# Judges commonly serialize two relevant blocks out of three as 0.6667. Treat
# that rounded representation as the protocol's documented 0.67 floor without
# weakening the faithfulness/relevancy gates.
MIN_CONTEXT_PRECISION = (2 / 3) - 0.001


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _read_checkpoint(path: Path, *, run_id: str, expected: set[str]) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows, errors = read_jsonl(path)
    if errors:
        raise CampaignIncomplete("; ".join(errors))
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("run_id") != run_id:
            raise CampaignIncomplete(f"checkpoint run identity mismatch: {path}")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or case_id not in expected or case_id in indexed:
            raise CampaignIncomplete(f"checkpoint has duplicate or unknown case: {case_id!r}")
        indexed[case_id] = row
    return indexed


def _assert_checkpoint_ledger(rows: list[dict[str, Any]], ledger: RequestLedger) -> None:
    """Reject copied checkpoints that have no matching completed ledger slot."""
    completed = {
        (row.get("operation"), row.get("run_id"), row.get("request_sha256"))
        for row in read_records(ledger.path)
        if row.get("event") == "completed"
    }
    for row in rows:
        identity = (row.get("operation"), row.get("run_id"), row.get("request_sha256"))
        if not all(isinstance(value, str) for value in identity) or identity not in completed:
            raise CampaignIncomplete("checkpoint is not backed by a completed ledger operation")


def _parse_json_object(content: str) -> dict[str, Any]:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ProviderOperationError("judge_parse_error", None, retryable=False) from error
    if not isinstance(value, dict):
        raise ProviderOperationError("judge_shape_error", None, retryable=False)
    return value


def _retryable(error: Exception, status_code: int | None) -> bool:
    return status_code in {408, 429, 500, 502, 503, 504} or isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in {"APITimeoutError", "APIConnectionError"}


def _provider_wrappers(
    ledger: RequestLedger,
    round_budget: ProviderBudgetLedger | None = None,
) -> tuple[Callable[[str, str, str, str], str], Callable[[str, str, str], dict[str, Any]]]:
    # This campaign is deliberately stricter than the legacy pool-compatible
    # helpers: every generation and judge attempt must resolve to KEY5.
    generation = Generator(
        model=EVAL_MODEL,
        api_keys=generation_pool_keys(policy="key5_only"),
        client_max_retries=0,
        key_policy="key5_only",
    )
    judge = Generator(
        model=EVAL_MODEL,
        api_keys=judging_pool_keys(policy="key5_only"),
        client_max_retries=0,
        key_policy="key5_only",
    )

    def counted(
        *,
        campaign_id: str,
        operation: str,
        request_sha256: str,
        send: Callable[[], Any],
    ) -> Any:
        if round_budget is None:
            return send()
        return round_budget.call(
            campaign_id=campaign_id,
            operation=operation,
            request_sha256=request_sha256,
            send=send,
        )

    def raw_generator(prompt: str, language: str) -> str:
        try:
            response = generation._create_groq_chat_completion(
                _retry_limit=0,
                model=EVAL_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt_for_language(language)},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=PHASE2_MAX_TOKENS,
                temperature=0,
            )
            return response.choices[0].message.content or ""
        except Exception as error:
            metadata = dict(generation.last_transport_metadata)
            raise ProviderOperationError(metadata.get("error_type", type(error).__name__), metadata.get("status_code"), metadata, retryable=_retryable(error, metadata.get("status_code"))) from error

    def generate(run_id: str, operation: str, prompt: str, language: str) -> str:
        request_sha256 = sha256_text(prompt)
        response = ledger.call(
            operation=operation,
            run_id=run_id,
            request_sha256=request_sha256,
            send=lambda: counted(
                campaign_id=run_id,
                operation=operation,
                request_sha256=request_sha256,
                send=lambda: {"content": raw_generator(prompt, language)},
            ),
        )
        content = response.get("content") if isinstance(response, dict) else None
        if not isinstance(content, str):
            raise CampaignIncomplete("generation response is malformed")
        return content

    def score(run_id: str, operation: str, prompt: str) -> dict[str, Any]:
        def send() -> dict[str, Any]:
            try:
                response = judge._create_groq_chat_completion(
                    _retry_limit=0,
                    model=EVAL_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt_for_language("en")},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=PHASE2_MAX_TOKENS,
                    temperature=0,
                )
                return {"scores": _parse_json_object(response.choices[0].message.content or "")}
            except ProviderOperationError:
                raise
            except Exception as error:
                metadata = dict(judge.last_transport_metadata)
                raise ProviderOperationError(metadata.get("error_type", type(error).__name__), metadata.get("status_code"), metadata, retryable=_retryable(error, metadata.get("status_code"))) from error

        request_sha256 = sha256_text(prompt)
        response = ledger.call(
            operation=operation,
            run_id=run_id,
            request_sha256=request_sha256,
            send=lambda: counted(
                campaign_id=run_id,
                operation=operation,
                request_sha256=request_sha256,
                send=send,
            ),
        )
        scores = response.get("scores") if isinstance(response, dict) else None
        if not isinstance(scores, dict):
            raise CampaignIncomplete("judge response is malformed")
        return scores

    return generate, score


def _bounded_call(ledger: RequestLedger, operation: Callable[[], Any]) -> Any:
    """Keep eight slots available for explicit transport retries."""
    if ledger.used >= BASE_REQUESTS + protocol.RESERVED_RETRY_BUDGET:
        raise CampaignIncomplete("reserved retry budget exhausted")
    return operation()


def _contexts(artifact: dict[str, Any]) -> dict[str, str]:
    by_question = {case["question"]: case for case in artifact["cases"]}
    test_cases = {case.question: case for case in TEST_SET}
    return {
        source_question: render_case_context(by_question[source_question], required_keywords=test_cases[source_question].required_keywords, strategy=CONTEXT_STRATEGY_SELECTIVE_V7)
        for source_question in {case["source_question"] for case in protocol.BILINGUAL_CASES}
    }


def _run_calibration(ledger: RequestLedger, score: Callable[[str, str, str], dict[str, Any]], path: Path, campaign_id: str) -> dict[str, Any]:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("campaign_id") != campaign_id or payload.get("provider_requests") != protocol.CALIBRATION_REQUESTS:
            raise CampaignIncomplete("calibration checkpoint identity mismatch")
        _assert_checkpoint_ledger(payload.get("cases", []), ledger)
        return payload
    rows: list[dict[str, Any]] = []
    for round_number in (1, 2):
        for case in calibration_cases():
            prompt = build_judge_prompt(case["question"], case["answer"], case["context"], reference_for(case["question"]))
            scores = _bounded_call(ledger, lambda: score(f"{campaign_id}-calibration", f"calibration:{round_number}:{case['id']}", prompt))
            expected = case["expected"]
            passed = (
                scores.get("faithfulness", 0) >= expected.get("faithfulness_min", 1.0) and scores.get("answer_relevancy", 0) >= expected.get("answer_relevancy_min", 1.0)
                if expected.get("accept")
                else scores.get("faithfulness", 1.0) <= expected.get("faithfulness_max", 1.0) or scores.get("answer_relevancy", 1.0) <= expected.get("answer_relevancy_max", 1.0)
            )
            rows.append({"round": round_number, "id": case["id"], "operation": f"calibration:{round_number}:{case['id']}", "run_id": f"{campaign_id}-calibration", "request_sha256": sha256_text(prompt), "scores": scores, "expected": expected, "passed": passed})
    payload = {"schema_version": 1, "campaign_id": campaign_id, "provider_requests": len(rows), "cases": rows, "passed": len(rows) == 12 and all(row["passed"] for row in rows)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not payload["passed"]:
        raise CampaignIncomplete("calibration failed; sentinel stage was not started")
    return payload


def _run_replicate(replicate: str, artifact: dict[str, Any], contexts: dict[str, str], ledger: RequestLedger, generate: Callable[[str, str, str, str], str], score: Callable[[str, str, str], dict[str, Any]], campaign_id: str) -> dict[str, Any]:
    run_id = f"{campaign_id}-{replicate}"
    generation_path = Path(f"data/diagnostics/{campaign_id}_{replicate}_generation.jsonl")
    judge_path = Path(f"data/diagnostics/{campaign_id}_{replicate}_judge.jsonl")
    cases = {case["case_id"]: case for case in protocol.case_records()}
    generations = _read_checkpoint(generation_path, run_id=run_id, expected=set(cases))
    judges = _read_checkpoint(judge_path, run_id=run_id, expected=set(cases))
    _assert_checkpoint_ledger(list(generations.values()) + list(judges.values()), ledger)
    for case_id, case in cases.items():
        if case_id in generations:
            continue
        context = contexts[case["source_question"]]
        prompt = "Use only the supplied filing excerpts. Preserve numbers, periods, units, and citations. Answer in the requested language.\n\nRETRIEVED CONTEXT:\n" + context + "\n\nQUESTION (" + case["language"] + "): " + case["question"]
        generation_operation = f"generation:{replicate}:{case_id}"
        draft = _bounded_call(ledger, lambda: generate(run_id, generation_operation, prompt, case["language"]))
        completion = make_answer_completion_postprocessor(
            lambda correction_prompt: generate(
                run_id,
                f"correction:{replicate}:{case_id}",
                correction_prompt,
                case["language"],
            ),
            deterministic_risk_renderer=True,
            deterministic_comparative_renderer=True,
        )
        answer = completion(case["question"], context, draft)
        if case["intent"] == "dependency" and case["language"] == "vi":
            localized = render_dependency_comparison_v3_localized(
                case["source_question"], context, "vi"
            )
            if localized:
                answer = localized
        elif case["intent"] == "major-risk" and case["language"] == "vi":
            localized = render_deterministic_risk_answer_localized(
                case["source_question"], context, "vi"
            )
            if localized:
                answer = localized
        elif case["intent"] == "international-risk":
            bounded = render_deterministic_international_risk_answer(
                case["source_question"], context, case["language"]
            )
            if bounded:
                answer = bounded
        elif case["intent"] == "growth-comparison":
            bounded = render_deterministic_growth_comparison(
                case["source_question"], context, case["language"]
            )
            if bounded:
                answer = bounded
        record = {"schema_version": 1, "campaign_id": campaign_id, "run_id": run_id, "case_id": case_id, "operation": generation_operation, "request_sha256": sha256_text(prompt), "language": case["language"], "intent": case["intent"], "question": case["question"], "source_question": case["source_question"], "answer": answer, "draft_answer_sha256": sha256_text(draft), "context_sha256": sha256_text(context), "prompt_sha256": sha256_text(prompt), "profile_fingerprint": sha256_text(BILINGUAL_RUBRIC + case["language"]), "status": "OK"}
        _append_jsonl(generation_path, record)
        generations[case_id] = record
    for case_id, case in cases.items():
        if case_id in judges:
            continue
        generation = generations[case_id]
        context = contexts[case["source_question"]]
        prompt = build_judge_prompt(case["question"], generation["answer"], context, reference_for(case["source_question"])) + "\n\nBILINGUAL REQUIREMENT: " + BILINGUAL_RUBRIC + "\nREQUESTED LANGUAGE: " + case["language"]
        scores = _bounded_call(ledger, lambda: score(run_id, f"judge:{replicate}:{case_id}", prompt))
        record = {"schema_version": 1, "campaign_id": campaign_id, "run_id": run_id, "case_id": case_id, "operation": f"judge:{replicate}:{case_id}", "request_sha256": sha256_text(prompt), "language": case["language"], "question": case["question"], "answer_sha256": sha256_text(generation["answer"]), "context_sha256": sha256_text(context), "prompt_sha256": sha256_text(prompt), "scores": scores, "profile_fingerprint": sha256_text(BILINGUAL_RUBRIC + case["language"]), "status": "OK"}
        _append_jsonl(judge_path, record)
        judges[case_id] = record
    output_cases = [{**generations[case_id], "scores": judges[case_id]["scores"]} for case_id in cases]
    passed = all(
        item["status"] == "OK"
        and float(item["scores"].get("faithfulness", 0)) == 1.0
        and float(item["scores"].get("answer_relevancy", 0)) == 1.0
        and float(item["scores"].get("context_precision", 0)) >= MIN_CONTEXT_PRECISION
        for item in output_cases
    )
    return {"schema_version": 1, "campaign_id": campaign_id, "run_id": run_id, "cases": output_cases, "passed": passed}


def _write_status(path: Path, *, campaign_id: str, status: str, decision: str, stage: str, error: str | None, ledger: RequestLedger) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "campaign_id": campaign_id, "status": status, "candidate_decision": decision, "stage": stage, "error": error, "request_count": ledger.used, "request_limit": protocol.MAX_REQUESTS}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--campaign-id", default=protocol.CAMPAIGN_ID)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(
        "--round-budget-path",
        type=Path,
        default=Path("data/diagnostics/improvement_round_provider_budget.jsonl"),
    )
    parser.add_argument("--round-id", default="enterprise_improvement_round_20260907")
    parser.add_argument("--round-budget-limit", type=int, default=2_000)
    parser.add_argument("--execute", action="store_true", help="Allow provider requests; omit for a provider-free preflight")
    args = parser.parse_args(argv)
    manifest_path = args.manifest or Path(f"data/diagnostics/{args.campaign_id}_manifest.json")
    if not manifest_path.exists():
        manifest = protocol.build_manifest(ARTIFACT_PATH, args.campaign_id)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors = protocol.verify_manifest(manifest_path, ARTIFACT_PATH, args.campaign_id)
    if errors:
        print(json.dumps({"status": "NO-GO", "manifest_errors": list(errors)}, indent=2))
        return 1
    if not args.execute:
        print(json.dumps({"status": "NOT_STARTED", "provider_calls": 0, "campaign_id": args.campaign_id, "manifest": str(manifest_path), "resume": f"python scripts/run_bilingual_evaluation_campaign.py --campaign-id {args.campaign_id} --execute"}, indent=2))
        return 0
    try:
        configured_groq_keys(settings, policy="key5_only")
    except ValueError as error:
        print(json.dumps({"status": "NO-GO", "error": str(error)}, indent=2))
        return 1
    status_path = Path(f"data/diagnostics/{args.campaign_id}_status.json")
    if status_path.exists():
        previous = json.loads(status_path.read_text(encoding="utf-8"))
        if previous.get("status") == "INCOMPLETE":
            print(json.dumps({"status": "NO-GO", "error": "incomplete campaign is immutable; create a new campaign id after provider authorization"}, indent=2))
            return 1
    ledger = RequestLedger(Path(f"data/diagnostics/{args.campaign_id}_campaign_ledger.jsonl"), args.campaign_id, protocol.MAX_REQUESTS)
    round_budget = ProviderBudgetLedger(
        args.round_budget_path,
        args.round_id,
        args.round_budget_limit,
    )
    try:
        artifact, _ = load_bound_artifact(ARTIFACT_PATH, EXPECTED_ARTIFACT_FINGERPRINT, CONTEXT_STRATEGY_SELECTIVE_V7)
        generate, score = _provider_wrappers(ledger, round_budget)
        calibration = _run_calibration(ledger, score, Path(f"data/diagnostics/{args.campaign_id}_calibration.json"), args.campaign_id)
        contexts = _contexts(artifact)
        r1 = _run_replicate("r1", artifact, contexts, ledger, generate, score, args.campaign_id)
        r2 = _run_replicate("r2", artifact, contexts, ledger, generate, score, args.campaign_id)
        decision = "GO" if calibration["passed"] and r1["passed"] and r2["passed"] and ledger.used <= protocol.MAX_REQUESTS else "NO-GO"
        _write_status(status_path, campaign_id=args.campaign_id, status="COMPLETE", decision=decision, stage="complete", error=None if decision == "GO" else "one or more bilingual gates failed", ledger=ledger)
        print(json.dumps({"status": "COMPLETE", "candidate_decision": decision, "request_count": ledger.used, "request_limit": protocol.MAX_REQUESTS, "replicates": [r1["passed"], r2["passed"]]}, indent=2))
        return 0 if decision == "GO" else 1
    except CampaignIncomplete as error:
        _write_status(status_path, campaign_id=args.campaign_id, status="INCOMPLETE", decision="UNDECIDED", stage="provider", error=str(error), ledger=ledger)
        print(json.dumps({"status": "INCOMPLETE", "candidate_decision": "UNDECIDED", "request_count": ledger.used, "request_limit": protocol.MAX_REQUESTS, "error": str(error), "next_step": "obtain a new provider window and start a new campaign id"}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
