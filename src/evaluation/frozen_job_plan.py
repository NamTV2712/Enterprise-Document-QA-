"""Canonical, credential-free native execution plans over registered Phase 1 evidence."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.evaluation.dataset_binding import EVALUATION_DATASET_ID, EVALUATION_DATASET_VERSION, evaluation_dataset_revision
from src.evaluation.answer_postprocessor_profile import ANSWER_POSTPROCESSOR_PROFILE_PROVIDER_DRAFT
from src.evaluation.evaluator import JUDGE_PROMPT_TEMPLATE, JUDGE_SYSTEM_PROMPT, _parse_judge_response
from src.evaluation.generation_checkpoint import (
    ANSWER_COMPLETION_FINGERPRINT,
    CONTEXT_STRATEGY_FULL_EVIDENCE,
    DEFAULT_GENERATION_PROMPT_TEMPLATE,
    GENERATION_CONTEXT_BUILDER_FINGERPRINT,
    GenerationUpstream,
    build_evidence_context,
    sha256_text,
)
from src.evaluation.native_protocol import (
    METRIC_DEFINITIONS, PROTOCOL_NAME, PROTOCOL_VERSION, NativeCaseInput,
    NativeReportBinding, NativeProtocolError, _unique_object, evaluate_case,
)
from src.evaluation.phase2_runtime import (
    GENERATION_SYSTEM_PROMPT_FINGERPRINT, JUDGE_CONTEXT_BUILDER_FINGERPRINT,
    PHASE2_MAX_TOKENS, build_production_judge_prompt,
    make_answer_completion_postprocessor, make_generation_call, make_judge_call,
)
from src.evaluation.retrieval_artifact import ARTIFACT_SCHEMA_VERSION, canonical_json
from src.evaluation.test_set import TEST_SET, TestCase
from src.generation.generator import DEFAULT_GENERATOR_MODEL_ID, Generator
from src.generation.answer_completion import correct_answer_once
from src.generation.period_value_completeness import render_chunk_evidence
from src.generation.prompt_contracts import answer_completion_contract_for_question
from src.retrieval.canonical_json import canonical_json_bytes


ARTIFACT_DIRECTORY = Path("data/eval_artifacts")
MAX_JOB_CASES = 200  # leaves a bounded DATA-004 payload with three case digests
_ARTIFACT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class FrozenPlanError(ValueError):
    """A registered evidence artifact cannot be used as a native frozen plan."""


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _runtime_code_fingerprints() -> dict[str, str]:
    """Bind actual local semantics, not just manually maintained version tags."""
    functions = {
        "render_chunk_evidence": render_chunk_evidence,
        "build_evidence_context": build_evidence_context,
        "answer_focus_contract": answer_completion_contract_for_question,
        "answer_completion": correct_answer_once,
        "answer_completion_adapter": make_answer_completion_postprocessor,
        "judge_prompt_builder": build_production_judge_prompt,
        "judge_response_parser": _parse_judge_response,
        "generation_transport_adapter": make_generation_call,
        "judge_transport_adapter": make_judge_call,
        "provider_transport": Generator._create_groq_chat_completion,
        "native_case_evaluation": evaluate_case,
    }
    return {
        name: sha256_text(inspect.getsource(function).replace("\r\n", "\n"))
        for name, function in functions.items()
    }


def _runtime_source_digest() -> str:
    """Conservatively bind transitive local generation helpers and constants."""
    project = Path(__file__).resolve().parents[2]
    paths = list((project / "src/generation").glob("*.py"))
    paths.extend(project / relative for relative in (
        "src/company_entities.py", "configs/tickers.py",
        "src/evaluation/answer_contract.py", "src/evaluation/revenue_intent_contract.py",
        "src/evaluation/phase2_runtime.py", "src/evaluation/evaluator.py",
        "src/evaluation/native_protocol.py", "src/evaluation/generation_checkpoint.py",
    ))
    return _digest({
        path.relative_to(project).as_posix(): sha256_text(path.read_text(encoding="utf-8").replace("\r\n", "\n"))
        for path in sorted(paths)
    })


def registered_artifact_bytes(artifact_id: str, *, directory: Path = ARTIFACT_DIRECTORY) -> bytes:
    if not _ARTIFACT_ID.fullmatch(artifact_id) or artifact_id.endswith(".json"):
        raise FrozenPlanError("artifact ID is not a registered opaque name")
    root = directory.resolve()
    target = (root / f"{artifact_id}.json").resolve()
    if target.parent != root or not target.is_file() or target.is_symlink():
        raise FrozenPlanError("registered Phase 1 artifact was not found")
    if target.stat().st_size > 16_000_000:
        raise FrozenPlanError("registered Phase 1 artifact is too large")
    return target.read_bytes()


def validate_artifact(content: bytes, *, verify_dataset: bool = True) -> dict[str, Any]:
    try:
        artifact = json.loads(content, object_pairs_hook=_unique_object)
        fingerprints = artifact["fingerprints"]
        embedded = fingerprints["artifact"]
        unsigned = dict(artifact)
        unsigned["fingerprints"] = {key: value for key, value in fingerprints.items() if key != "artifact"}
        expected = sha256_text(canonical_json(unsigned).decode("utf-8"))
        if artifact["schema_version"] != ARTIFACT_SCHEMA_VERSION or embedded != expected:
            raise FrozenPlanError("Phase 1 artifact fingerprint is invalid")
        cases = artifact["cases"]
        if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_JOB_CASES:
            raise FrozenPlanError("Phase 1 artifact case count is invalid")
        by_question = {case.question: case for case in TEST_SET} if verify_dataset else {}
        seen: set[str] = set()
        for case in cases:
            question = case["question"]
            source = by_question.get(question)
            if question in seen or (verify_dataset and source is None):
                raise FrozenPlanError("Phase 1 artifact contains unknown or duplicate cases")
            seen.add(question)
            if verify_dataset and (
                case["ground_truth"] != source.ground_truth
                or case["required_keywords"] != source.required_keywords
                or case["expects_fallback"] != source.expects_fallback
                or case["category"] != source.category
            ):
                raise FrozenPlanError("Phase 1 artifact case differs from registered dataset")
        return artifact
    except (KeyError, TypeError, IndexError, json.JSONDecodeError, UnicodeDecodeError, NativeProtocolError) as error:
        raise FrozenPlanError("Phase 1 artifact is malformed") from error


def case_id(source: TestCase) -> str:
    """Stable identity of the complete canonical API-006 case, not its position."""
    return hashlib.sha256(canonical_json_bytes(asdict(source))).hexdigest()


def creation_request_fingerprint(artifact_id: str, budget: int) -> str:
    return _digest({
        "artifact_id": artifact_id, "engine": "native", "mode": "provider_backed",
        "metrics": [item.metric_id for item in METRIC_DEFINITIONS], "budget": budget,
    })


def freeze_plan(artifact_id: str, content: bytes, budget: int) -> dict[str, Any]:
    artifact = validate_artifact(content)
    cases = artifact["cases"]
    sources = {case.question: case for case in TEST_SET}
    identifiers = [case_id(sources[case["question"]]) for case in cases]
    if type(budget) is not int or not 3 * len(cases) <= budget <= 15000:
        raise FrozenPlanError("provider attempt budget must cover at most three calls per frozen case")
    artifact_digest = "sha256:" + hashlib.sha256(content).hexdigest()
    fingerprints = artifact["fingerprints"]
    for key in ("retrieval_config", "embedding", "reranker"):
        if not isinstance(fingerprints.get(key), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprints[key]):
            raise FrozenPlanError("Phase 1 retrieval binding is incomplete")
    upstream = GenerationUpstream(
        artifact_path=Path("registered-artifact"),
        artifact_sha256=artifact_digest,
        artifact_schema_version=ARTIFACT_SCHEMA_VERSION,
        model=DEFAULT_GENERATOR_MODEL_ID,
        system_prompt_sha256=GENERATION_SYSTEM_PROMPT_FINGERPRINT,
    )
    context_binding = _digest({
        "artifact": artifact_digest,
        "renderer": GENERATION_CONTEXT_BUILDER_FINGERPRINT,
        "strategy": CONTEXT_STRATEGY_FULL_EVIDENCE,
    })
    judge_definition = _digest({
        "model": DEFAULT_GENERATOR_MODEL_ID,
        "system_prompt": sha256_text(JUDGE_SYSTEM_PROMPT),
        "prompt": sha256_text(JUDGE_PROMPT_TEMPLATE),
        "context_builder": JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        "max_tokens": PHASE2_MAX_TOKENS,
        "generation_binding": upstream.binding,
        "context_binding": context_binding,
    })
    binding = NativeReportBinding(
        engine_id="native", engine_version=1,
        dataset_id=EVALUATION_DATASET_ID,
        dataset_version=EVALUATION_DATASET_VERSION,
        dataset_revision=evaluation_dataset_revision(TEST_SET),
        generator_model_id=DEFAULT_GENERATOR_MODEL_ID,
        generator_model_fingerprint=_digest({"model": DEFAULT_GENERATOR_MODEL_ID}),
        generation_prompt_sha256=upstream.prompt_template_sha256,
        generation_binding=upstream.binding,
        retrieval_binding=artifact_digest,
        retrieval_config_fingerprint=fingerprints["retrieval_config"],
        embedding_fingerprint=fingerprints["embedding"],
        reranker_fingerprint=fingerprints["reranker"],
        context_binding=context_binding,
        judge_model_id=DEFAULT_GENERATOR_MODEL_ID,
        judge_prompt_sha256=sha256_text(JUDGE_PROMPT_TEMPLATE),
        judge_binding=judge_definition,
    )
    contexts = [build_evidence_context(case) for case in cases]
    for case, context, identifier in zip(cases, contexts, identifiers, strict=True):
        # Provider-free native validation rejects oversized/malformed evidence
        # before any generation or judge attempt is possible.
        evaluate_case(NativeCaseInput(
            case_id=identifier, answer=None, rendered_context=context,
            ground_truth=case["ground_truth"],
            required_keywords=tuple(case["required_keywords"]),
            expects_fallback=case["expects_fallback"], judge_scores=None,
        ), binding)
    snapshot = {
        "schema_version": 1,
        "request_fingerprint": creation_request_fingerprint(artifact_id, budget),
        "protocol": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "engine": "native",
        "engine_version": 1,
        "mode": "provider_backed",
        "metric_versions": {item.metric_id: item.metric_version for item in METRIC_DEFINITIONS},
        "metric_definitions_digest": _digest([asdict(item) for item in METRIC_DEFINITIONS]),
        "artifact_id": artifact_id,
        "artifact_digest": artifact_digest,
        "retrieval_fingerprints": {
            key: fingerprints.get(key) for key in (
                "artifact_schema_version", "plan_schema_version", "test_set",
                "plan", "corpus", "index_manifest", "embedding", "reranker",
                "query_shaper", "lexical_ladder", "retrieval_config", "artifact",
            )
        },
        "case_ids": identifiers,
        "case_hashes": [_digest(case) for case in cases],
        "context_hashes": [sha256_text(context) for context in contexts],
        "budget_unit": "provider_attempt_slot",
        "budget_limit": budget,
        "maximum_required_attempts": 3 * len(cases),
        "binding": asdict(binding),
        "generation_system_prompt_sha256": GENERATION_SYSTEM_PROMPT_FINGERPRINT,
        "generation_context_builder_fingerprint": GENERATION_CONTEXT_BUILDER_FINGERPRINT,
        "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        "answer_postprocessor_profile_sha256": ANSWER_POSTPROCESSOR_PROFILE_PROVIDER_DRAFT,
        "generation_prompt_template_sha256": sha256_text(DEFAULT_GENERATION_PROMPT_TEMPLATE),
        "judge_system_prompt_sha256": sha256_text(JUDGE_SYSTEM_PROMPT),
        "judge_context_builder_fingerprint": JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        "judge_max_tokens": PHASE2_MAX_TOKENS,
        "runtime_code_fingerprints": _runtime_code_fingerprints(),
        "runtime_source_digest": _runtime_source_digest(),
        "judge_prompt_template_sha256": sha256_text(JUDGE_PROMPT_TEMPLATE),
    }
    snapshot["snapshot_digest"] = _digest(snapshot)
    return snapshot


def assert_runtime_binding(snapshot: dict[str, Any]) -> None:
    """Fail closed if code-owned prompt/renderer semantics drift after creation."""
    checks = {
        "generation_system_prompt_sha256": GENERATION_SYSTEM_PROMPT_FINGERPRINT,
        "generation_context_builder_fingerprint": GENERATION_CONTEXT_BUILDER_FINGERPRINT,
        "answer_completion_fingerprint": ANSWER_COMPLETION_FINGERPRINT,
        "answer_postprocessor_profile_sha256": ANSWER_POSTPROCESSOR_PROFILE_PROVIDER_DRAFT,
        "generation_prompt_template_sha256": sha256_text(DEFAULT_GENERATION_PROMPT_TEMPLATE),
        "judge_system_prompt_sha256": sha256_text(JUDGE_SYSTEM_PROMPT),
        "judge_context_builder_fingerprint": JUDGE_CONTEXT_BUILDER_FINGERPRINT,
        "judge_max_tokens": PHASE2_MAX_TOKENS,
        "metric_definitions_digest": _digest([asdict(item) for item in METRIC_DEFINITIONS]),
        "runtime_code_fingerprints": _runtime_code_fingerprints(),
        "runtime_source_digest": _runtime_source_digest(),
        "judge_prompt_template_sha256": sha256_text(JUDGE_PROMPT_TEMPLATE),
    }
    unsigned = {key: value for key, value in snapshot.items() if key != "snapshot_digest"}
    if snapshot.get("snapshot_digest") != _digest(unsigned) or any(snapshot.get(key) != value for key, value in checks.items()):
        raise FrozenPlanError("frozen evaluation runtime binding has changed")
