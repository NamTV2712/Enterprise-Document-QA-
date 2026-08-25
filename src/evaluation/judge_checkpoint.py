"""Phase 2B: judge checkpoint consuming frozen generations and evidence.

Judging runs strictly after generation: it reads answers from the
generation checkpoint (never from a live provider conversation) plus the
frozen evidence blocks, and stores its own upstream binding over the
generation records so a judge rerun can never attach scores to answers
produced under different artifacts, prompts, or models. Quota-skipped or
invalid judge responses are recorded but excluded from official
aggregates.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

from src.evaluation.generation_checkpoint import (
    GEN_STATUS_OK,
    GenerationCheckpointStore,
    aggregate_generation,
    sha256_text,
)
from src.evaluation.evaluator import JUDGE_MAX_TOKENS

logger = logging.getLogger(__name__)

JUDGE_SCHEMA_VERSION = 1
JUDGE_STATUS_OK = "OK"
JUDGE_STATUS_PARSE_INVALID = "JUDGE_PARSE_INVALID"
JUDGE_STATUS_SKIPPED_QUOTA = "JUDGE_SKIPPED_QUOTA"


def compute_judge_binding(
    generation_binding: str,
    generation_answer_sha256s: str,
    judge_model: str,
    judge_prompt_template_sha256: str,
    judge_max_tokens: int = JUDGE_MAX_TOKENS,
) -> str:
    """Identity tying judge scores to exactly these generated answers.

    The completion budget participates in the binding: changing it can
    change whether long rationales survive truncation, so scores produced
    under different caps are never mixed.
    """
    payload = {
        "schema_version": JUDGE_SCHEMA_VERSION,
        "generation_binding": generation_binding,
        "generation_answer_sha256s": generation_answer_sha256s,
        "judge_model": judge_model,
        "judge_prompt_template_sha256": judge_prompt_template_sha256,
        "judge_max_tokens": judge_max_tokens,
    }
    return sha256_text(json.dumps(payload, sort_keys=True))


class JudgeCheckpointStore:
    def __init__(self, path: Path):
        self.path = path

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_compatible(self, binding: str) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        compatible: dict[str, dict] = {}
        with self.path.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("status") != JUDGE_STATUS_OK:
                    continue
                if record.get("binding") != binding:
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


def run_judge_phase(
    selected_questions: list[str],
    generation_records_by_question: dict[str, dict[str, Any]],
    evidence_context_by_question: dict[str, str],
    ground_truth_by_question: dict[str, str],
    judge_model: str,
    judge_prompt_template_sha256: str,
    judge_fn: Callable[[str], Any],
    checkpoint_store: JudgeCheckpointStore,
    max_retries: int = 2,
    retry_backoff_seconds: tuple[float, ...] = (5.0, 15.0),
    sleep_fn: Callable[[float], None] = time.sleep,
    judge_prompt_builder: Callable[[str, str, str, str], str] | None = None,
    judge_max_tokens: int = JUDGE_MAX_TOKENS,
) -> list[dict[str, Any]]:
    """Judge frozen answers; ``judge_fn`` is the only provider touchpoint.

    ``judge_prompt_builder`` optionally overrides the naive prompt
    composition with production judging instructions; it receives
    (question, answer, evidence_context, ground_truth). A judge failure
    never destroys the underlying generation record — failures are
    checkpointed with their own status and can be retried by rerunning
    this phase against the same generation store.
    """
    ok_generations = [
        question for question in selected_questions
        if question in generation_records_by_question
        and generation_records_by_question[question]["status"] == GEN_STATUS_OK
    ]
    answer_hashes = sha256_text(json.dumps(
        [
            sha256_text(generation_records_by_question[q]["answer"])
            for q in sorted(ok_generations)
        ],
        separators=(",", ":"),
    ))
    # All selected questions share one generation binding by construction.
    bindings = {
        generation_records_by_question[q]["binding"]
        for q in ok_generations
    }
    if len(bindings) > 1:
        raise ValueError(
            f"Generation records span multiple bindings; refusing to judge: {bindings}"
        )
    generation_binding = next(iter(bindings), "")

    binding = compute_judge_binding(
        generation_binding=generation_binding,
        generation_answer_sha256s=answer_hashes,
        judge_model=judge_model,
        judge_prompt_template_sha256=judge_prompt_template_sha256,
        judge_max_tokens=judge_max_tokens,
    )

    done = checkpoint_store.load_compatible(binding)
    records: list[dict[str, Any]] = []

    for question in selected_questions:
        if question not in generation_records_by_question:
            raise ValueError(f"No generation record for question: {question!r}")
        generation_record = generation_records_by_question[question]
        if generation_record["status"] != GEN_STATUS_OK:
            logger.warning(
                "Judge skipped for non-OK generation (%s): %s",
                generation_record["status"],
                question[:60],
            )
            continue

        if question in done:
            logger.info("JUDGE resume OK: %s", question[:60])
            records.append(done[question])
            continue

        if judge_prompt_builder is not None:
            prompt = judge_prompt_builder(
                question,
                generation_record["answer"],
                evidence_context_by_question[question],
                ground_truth_by_question[question],
            )
        else:
            prompt = (
                f"{evidence_context_by_question[question]}\n\n"
                f"Question: {question}\n"
                f"Answer: {generation_record['answer']}\n"
                f"Ground truth: {ground_truth_by_question[question]}"
            )

        scores: Any = None
        error: str | None = None
        parse_invalid = False
        attempts = [0.0] + list(retry_backoff_seconds[:max_retries])
        for attempt_index, wait in enumerate(attempts, start=1):
            if wait:
                sleep_fn(wait)
            try:
                scores = judge_fn(prompt)
                break
            except JudgeParseErrorStub as exc:
                error = str(exc)
                parse_invalid = True
                logger.error("Judge response invalid; not retrying: %s", error)
                break
            except Exception as exc:  # noqa: BLE001 - provider errors are data here
                error = str(exc)
                logger.warning(
                    "Judge attempt %d failed: %s", attempt_index, error[:180]
                )

        record: dict[str, Any] = {
            "question": question,
            "binding": binding,
            "model": judge_model,
            "judge_prompt_template_sha256": judge_prompt_template_sha256,
            "judge_max_tokens": judge_max_tokens,
        }
        if scores is not None:
            record.update({"status": JUDGE_STATUS_OK, "scores": scores})
        elif parse_invalid:
            record.update({"status": JUDGE_STATUS_PARSE_INVALID, "error": error})
        elif error is not None and _looks_like_quota_error(error):
            record.update({"status": JUDGE_STATUS_SKIPPED_QUOTA, "error": error})
        else:
            record.update({"status": JUDGE_STATUS_ERROR, "error": error})
        checkpoint_store.append(record)
        records.append(record)

    return records


class JudgeParseErrorStub(Exception):
    """Marker exception judges raise for schema-invalid responses."""


def build_official_aggregate(
    generation_records: list[dict[str, Any]],
    judge_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Official results require complete OK coverage across both phases."""
    generation_summary = aggregate_generation(generation_records)
    judged_ok = [r for r in judge_records if r["status"] == JUDGE_STATUS_OK]
    judged_bad = [r for r in judge_records if r["status"] != JUDGE_STATUS_OK]

    num_ok = generation_summary["num_ok"]
    if num_ok == 0:
        return {
            "official": False,
            "reason": "no completed generations",
            "num_generation_ok": 0,
            "num_judged_ok": 0,
            "excluded_records": generation_summary["skipped_records"] + judged_bad,
        }
    if num_ok != generation_summary["num_selected"]:
        return {
            "official": False,
            "reason": (
                "generation phase incomplete; skipped/quota records are "
                "never merged into official aggregates"
            ),
            "num_generation_ok": num_ok,
            "num_judged_ok": len(judged_ok),
            "excluded_records": generation_summary["skipped_records"] + judged_bad,
        }
    if len(judged_ok) != num_ok:
        return {
            "official": False,
            "reason": (
                "judging incomplete for completed generations; rerun the "
                "judge phase to finish before publishing"
            ),
            "num_generation_ok": num_ok,
            "num_judged_ok": len(judged_ok),
            "excluded_records": judged_bad,
        }

    return {
        "official": True,
        "num_cases": num_ok,
        "records": judged_ok,
    }


def load_generation_records(path: Path) -> dict[str, dict[str, Any]]:
    """Latest-wins map of question -> record from a generation store."""
    return _latest_by_question(GenerationCheckpointStore(path))


def load_judge_records(path: Path) -> dict[str, dict[str, Any]]:
    return _latest_by_question(JudgeCheckpointStore(path))


def _latest_by_question(store) -> dict[str, dict[str, Any]]:
    if not store.path.exists():
        return {}
    latest: dict[str, dict[str, Any]] = {}
    with store.path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            question = record.get("question")
            if isinstance(question, str):
                latest[question] = record
    return latest
