"""Phase 2A: generation checkpoint bound to a frozen retrieval artifact.

The generation phase consumes ONLY the Phase 1 artifact — it never
touches the retriever. Every checkpoint record stores the upstream
artifact hash, model id, system/user prompt hashes, and context strategy, and
resume accepts records only when all inputs match exactly, so interrupted
runs can never silently mix different evidence, prompts, or models.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.generation.prompt_contracts import (
    NUMERIC_PAIR_CONTRACT,
    answer_completion_contract_for_question,
)
from src.generation.period_value_completeness import (
    PeriodValueCorrectionError,
    render_chunk_evidence,
)
from src.generation.answer_completion import (
    ANSWER_COMPLETION_FINGERPRINT,
    AnswerCompletionError,
)
from src.generation.enumeration_context import ENUMERATION_CONSENSUS_FINGERPRINT
from src.generation.fact_context import FACT_CONTEXT_SELECTOR_FINGERPRINT
logger = logging.getLogger(__name__)

GENERATION_SCHEMA_VERSION = 5
GEN_STATUS_OK = "OK"
GEN_STATUS_SKIPPED_QUOTA = "GEN_SKIPPED_QUOTA"
GEN_STATUS_ERROR = "GEN_ERROR"

# Frozen prompt template; changing one character changes its fingerprint
# and invalidates every previous generation checkpoint by design.
DEFAULT_GENERATION_PROMPT_TEMPLATE = (
    "You are a financial research assistant answering strictly from the "
    "provided SEC filing excerpts.\n"
    "\n"
    "Context:\n{context_blocks}\n"
    "\n"
    "Question: {question}\n"
    "{answer_focus_contract} "
    "Use only canonical inline [Source N] citations; do not use line-number "
    "citation formats such as 【1†L1-L3】. Cite every factual claim. Quote "
    "numeric values exactly as shown, including the period and sign. "
    f"{NUMERIC_PAIR_CONTRACT} If the "
    "excerpts do not contain the answer, say you cannot find it in the filings "
    "without describing retrieved sources as relevant."
)

CONTEXT_STRATEGY_FULL_EVIDENCE = "full_evidence_v1"


def sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


GENERATION_CONTEXT_BUILDER_FINGERPRINT = sha256_text(
    "generation-context-renderer-v4-shared-source-adapter-canonical-trim-"
    "enumeration-selector-"
    + ENUMERATION_CONSENSUS_FINGERPRINT
    + "-fact-selector-"
    + FACT_CONTEXT_SELECTOR_FINGERPRINT
)


def compute_generation_binding(
    upstream_artifact_sha256: str,
    artifact_schema_version: int,
    model: str,
    prompt_template_sha256: str,
    context_strategy: str,
    context_builder_fingerprint: str,
    system_prompt_sha256: str,
    answer_completion_fingerprint: str = ANSWER_COMPLETION_FINGERPRINT,
) -> str:
    """Stable identity of everything that must not drift across resume."""
    payload = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "upstream_artifact_sha256": upstream_artifact_sha256,
        "upstream_schema_version": artifact_schema_version,
        "model": model,
        "prompt_template_sha256": prompt_template_sha256,
        "context_strategy": context_strategy,
        "context_builder_fingerprint": context_builder_fingerprint,
        "system_prompt_sha256": system_prompt_sha256,
        "answer_completion_fingerprint": answer_completion_fingerprint,
    }
    return sha256_text(json.dumps(payload, sort_keys=True))


@dataclass
class GenerationUpstream:
    """The frozen Phase 1 binding for one generation phase run."""

    artifact_path: Path
    artifact_sha256: str
    artifact_schema_version: int
    model: str
    system_prompt_sha256: str
    prompt_template: str = DEFAULT_GENERATION_PROMPT_TEMPLATE
    context_strategy: str = CONTEXT_STRATEGY_FULL_EVIDENCE
    context_builder_fingerprint: str = GENERATION_CONTEXT_BUILDER_FINGERPRINT
    answer_completion_fingerprint: str = ANSWER_COMPLETION_FINGERPRINT

    @property
    def prompt_template_sha256(self) -> str:
        return sha256_text(self.prompt_template)

    @property
    def binding(self) -> str:
        return compute_generation_binding(
            self.artifact_sha256,
            self.artifact_schema_version,
            self.model,
            self.prompt_template_sha256,
            self.context_strategy,
            self.context_builder_fingerprint,
            self.system_prompt_sha256,
            self.answer_completion_fingerprint,
        )


class GenerationCheckpointStore:
    """Append-only JSONL store with strict-binding resume semantics."""

    def __init__(self, path: Path):
        self.path = path

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_compatible(self, upstream: GenerationUpstream) -> dict[str, dict]:
        """Return OK records whose stored binding matches exactly."""
        if not self.path.exists():
            return {}
        compatible: dict[str, dict] = {}
        with self.path.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("status") != GEN_STATUS_OK:
                    continue
                if record.get("binding") != upstream.binding:
                    continue
                question = record.get("question")
                if isinstance(question, str):
                    compatible[question] = record
        return compatible


def _looks_like_quota_error(error: str) -> bool:
    lowered = error.lower()
    return any(
        token in lowered
        for token in ("429", "rate limit", "quota", "too many requests")
    )


def build_evidence_context(
    case_payload: dict[str, Any],
) -> str:
    """Render frozen artifact evidence into deterministic context blocks."""
    chunks: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for query_entry in case_payload.get("queries", []):
        for chunk in query_entry.get("chunks", []):
            chunk_id = chunk.get("chunk_id")
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            chunks.append(chunk)
    return render_chunk_evidence(chunks)


def parse_evidence_context(evidence_context: str) -> list[dict[str, str]]:
    """Parse canonical source blocks without splitting internal blank lines."""
    matches = re.finditer(
        r"(?ms)^\[Source (?P<number>\d+)\] (?P<citation>[^\n]*)\n"
        r"(?P<text>.*?)(?=^\[Source \d+\] |\Z)",
        evidence_context,
    )
    return [
        {
            "number": match.group("number"),
            "citation": match.group("citation"),
            "text": match.group("text").rstrip(),
        }
        for match in matches
        if match.group("text").strip()
    ]


def run_generation_phase(
    selected_questions: list[str],
    artifact_cases: dict[str, dict[str, Any]],
    upstream: GenerationUpstream,
    generate_fn: Callable[[str], str],
    checkpoint_store: GenerationCheckpointStore,
    max_retries: int = 2,
    retry_backoff_seconds: tuple[float, ...] = (5.0, 15.0),
    sleep_fn: Callable[[float], None] = time.sleep,
    evidence_context_fn: Callable[[dict[str, Any]], str] | None = None,
    answer_postprocessor: Callable[[str, str, str], str] | None = None,
    answer_completion_metadata: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate answers for the selected questions from frozen evidence.

    ``generate_fn`` is the only provider touchpoint (injected so tests can
    prove no retriever or network is involved). Quota failures are
    checkpointed separately from completed answers so judge-side quota
    problems later cannot destroy finished generations. ``answer_postprocessor``
    runs after the draft provider call and receives the exact rendered context;
    its own bounded correction failures are not retried by this outer loop.
    """
    done = checkpoint_store.load_compatible(upstream)
    render_context = evidence_context_fn or build_evidence_context
    records: list[dict[str, Any]] = []

    for question in selected_questions:
        if question in done:
            logger.info("GEN resume OK: %s", question[:60])
            record = done[question]
            if answer_completion_metadata is not None:
                metadata = record.get("answer_completion")
                if not isinstance(metadata, dict):
                    metadata = record.get("period_value_correction")
                if isinstance(metadata, dict):
                    answer_completion_metadata[question] = metadata
            records.append(record)
            continue

        case_payload = artifact_cases.get(question)
        if case_payload is None:
            raise ValueError(
                f"Artifact has no evidence for selected question: {question!r}"
            )

        evidence_context = render_context(case_payload)
        prompt = upstream.prompt_template.format(
            context_blocks=evidence_context,
            question=question,
            answer_focus_contract=answer_completion_contract_for_question(question),
        )

        answer: str | None = None
        error: str | None = None
        attempts = [0.0] + list(retry_backoff_seconds[:max_retries])
        for attempt_index, wait in enumerate(attempts, start=1):
            if wait:
                sleep_fn(wait)
            try:
                answer = generate_fn(prompt)
                if answer_postprocessor is not None:
                    answer = answer_postprocessor(
                        question,
                        evidence_context,
                        answer,
                    )
                break
            except AnswerCompletionError as exc:
                # The bounded correction owns its single provider attempt. Do
                # not retry the whole draft+correction pair here.
                answer = None
                error = str(exc)
                logger.warning("Answer completion failed: %s", error[:180])
                break
            except PeriodValueCorrectionError as exc:
                # Backward compatibility for legacy numeric-only postprocessors.
                answer = None
                error = str(exc)
                logger.warning("Period/value correction failed: %s", error[:180])
                break
            except Exception as exc:  # noqa: BLE001 - provider errors are data here
                error = str(exc)
                logger.warning(
                    "Generation attempt %d failed: %s",
                    attempt_index,
                    error[:180],
                )

        record: dict[str, Any] = {
            "question": question,
            "binding": upstream.binding,
            "model": upstream.model,
            "prompt_template_sha256": upstream.prompt_template_sha256,
            "context_strategy": upstream.context_strategy,
            "context_builder_fingerprint": upstream.context_builder_fingerprint,
            "answer_completion_fingerprint": upstream.answer_completion_fingerprint,
            "system_prompt_sha256": upstream.system_prompt_sha256,
            "upstream_artifact_sha256": upstream.artifact_sha256,
        }
        if answer is not None:
            record.update({"status": GEN_STATUS_OK, "answer": answer})
            if answer_completion_metadata is not None:
                metadata = answer_completion_metadata.get(question)
                if isinstance(metadata, dict):
                    record["answer_completion"] = metadata
                    record["period_value_correction"] = metadata
        elif error is not None and _looks_like_quota_error(error):
            record.update({"status": GEN_STATUS_SKIPPED_QUOTA, "error": error})
        else:
            record.update({"status": GEN_STATUS_ERROR, "error": error})
        checkpoint_store.append(record)
        records.append(record)

    return records


def aggregate_generation(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Official aggregates include OK records only."""
    ok = [r for r in records if r["status"] == GEN_STATUS_OK]
    skipped = [
        r for r in records
        if r["status"] in {GEN_STATUS_SKIPPED_QUOTA, GEN_STATUS_ERROR}
    ]
    return {
        "num_selected": len(records),
        "num_ok": len(ok),
        "num_skipped": len(skipped),
        "ok_records": ok,
        "skipped_records": skipped,
    }
