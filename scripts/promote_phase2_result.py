"""Promote one admitted Phase 2 candidate without rerunning providers.

The command is intentionally dry-run by default.  Promotion is allowed only
when the candidate, admission report, and protected official result still
match caller-supplied SHA-256 digests.  Applying the promotion first preserves
the previous official bytes in an immutable content-addressed archive, then
atomically replaces the protected result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V2


DEFAULT_CANDIDATE = Path(
    "data/eval_artifacts/phase2_results_grounded_completion_v3_v2_candidate.json"
)
DEFAULT_ADMISSION = Path(
    "data/diagnostics/phase2_admission_grounded_completion_v3_v2_candidate.json"
)
DEFAULT_OFFICIAL = Path(
    "data/eval_artifacts/phase2_results_packed_selective_v2.json"
)
DEFAULT_ARCHIVE_DIR = Path("data/eval_artifacts/archive")
DEFAULT_RECEIPT = Path(
    "data/diagnostics/phase2_promotion_grounded_completion_v3_v2.json"
)
ADMISSION_METRIC_KEYS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "overall_judge_average",
)


def _sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _normalise_digest(value: str) -> str:
    value = value.strip().lower()
    return value if value.startswith("sha256:") else f"sha256:{value}"


def _require_digest(path: Path, expected: str, label: str) -> str:
    actual = _file_sha256(path)
    expected = _normalise_digest(expected)
    if actual != expected:
        raise RuntimeError(
            f"{label} drift: expected {expected}, observed {actual}; "
            "refusing promotion before any write"
        )
    return actual


def _load_object(path: Path, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must contain one JSON object")
    return payload


def _same_path(recorded: Any, actual: Path) -> bool:
    if not isinstance(recorded, str) or not recorded:
        return False
    return Path(recorded).resolve() == actual.resolve()


def _all_true(mapping: Any) -> bool:
    return (
        isinstance(mapping, dict)
        and bool(mapping)
        and all(value is True for value in mapping.values())
    )


def _admission_metrics(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result.get("metrics")
    if not isinstance(metrics, dict):
        return {key: None for key in ADMISSION_METRIC_KEYS}
    return {key: metrics.get(key) for key in ADMISSION_METRIC_KEYS}


def _validate_contract(
    candidate: dict[str, Any],
    admission: dict[str, Any],
    official: dict[str, Any],
    *,
    candidate_path: Path,
    official_path: Path,
    candidate_sha256: str,
    admission_sha256: str,
    official_sha256: str,
    expected_binding: str,
    expected_candidate_strategy: str,
    expected_official_strategy: str,
) -> None:
    del admission_sha256  # Bound into promotion provenance after validation.
    failures: list[str] = []

    if candidate.get("official") is not False:
        failures.append("candidate must still be non-official")
    if candidate.get("provider_complete") is not True:
        failures.append("candidate must be provider-complete")
    if candidate.get("benchmark_eligible") is not True:
        failures.append("candidate must be benchmark-eligible")
    if candidate.get("stopped_reason") is not None:
        failures.append("candidate has a stopped_reason")
    if not (
        candidate.get("num_selected")
        == candidate.get("num_generation_ok")
        == candidate.get("num_judged_ok")
        == 30
    ):
        failures.append("candidate must have 30/30 generation and judging")

    cases = candidate.get("cases")
    if not isinstance(cases, list) or len(cases) != 30:
        failures.append("candidate must contain exactly 30 cases")
    elif (
        len({case.get("question") for case in cases if isinstance(case, dict)})
        != 30
        or not all(
            isinstance(case, dict)
            and case.get("generation_status") == "OK"
            and case.get("judge_status") == "OK"
            for case in cases
        )
    ):
        failures.append("candidate case set/statuses are not complete and unique")

    if candidate.get("binding") != expected_binding:
        failures.append("candidate binding does not match the pinned binding")
    if candidate.get("context_strategy") != expected_candidate_strategy:
        failures.append("candidate context strategy does not match the pinned strategy")

    if official.get("official") is not True:
        failures.append("protected baseline is not marked official")
    if official.get("context_strategy") != expected_official_strategy:
        failures.append("protected baseline context strategy does not match the pinned strategy")

    if admission.get("admission") is not True or admission.get("passed") is not True:
        failures.append("admission report is not a passing decision")
    if not _all_true(admission.get("gates")):
        failures.append("admission report does not have an all-true gate set")
    if not _same_path(admission.get("candidate_path"), candidate_path):
        failures.append("admission report points to a different candidate")
    if not _same_path(admission.get("baseline_path"), official_path):
        failures.append("admission report points to a different official baseline")
    if admission.get("candidate_sha256") != candidate_sha256:
        failures.append("admission report candidate SHA-256 does not match")
    if admission.get("baseline_sha256") != official_sha256:
        failures.append("admission report baseline SHA-256 does not match")
    if admission.get("binding") != expected_binding:
        failures.append("admission report binding does not match")
    if admission.get("context_strategy") != expected_candidate_strategy:
        failures.append("admission report context strategy does not match")
    if admission.get("expected_cases") != 30:
        failures.append("admission report is not for the official N=30 set")
    if admission.get("candidate_metrics") != _admission_metrics(candidate):
        failures.append("admission metrics differ from candidate metrics")
    if admission.get("baseline_metrics") != _admission_metrics(official):
        failures.append("admission metrics differ from protected baseline metrics")
    if admission.get("artifact_fingerprint") != candidate.get(
        "bound_artifact_fingerprint"
    ):
        failures.append("candidate and admission artifact fingerprints differ")

    if failures:
        raise RuntimeError("promotion contract failed: " + "; ".join(failures))


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _preserve_archive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != payload:
            raise RuntimeError(
                f"immutable archive collision at {path}; refusing official write"
            ) from None


def promote(
    *,
    candidate_path: Path,
    admission_path: Path,
    official_path: Path,
    archive_dir: Path,
    receipt_path: Path | None,
    expected_candidate_sha256: str,
    expected_admission_sha256: str,
    expected_official_sha256: str,
    expected_binding: str,
    expected_strategy: str | None = None,
    expected_candidate_strategy: str | None = None,
    expected_official_strategy: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Validate and optionally apply one exact, previously admitted promotion."""
    if expected_strategy is not None:
        if (
            expected_candidate_strategy is not None
            and expected_candidate_strategy != expected_strategy
        ) or (
            expected_official_strategy is not None
            and expected_official_strategy != expected_strategy
        ):
            raise RuntimeError(
                "promotion contract failed: conflicting strategy expectations"
            )
        expected_candidate_strategy = expected_candidate_strategy or expected_strategy
        expected_official_strategy = expected_official_strategy or expected_strategy
    expected_candidate_strategy = (
        expected_candidate_strategy or CONTEXT_STRATEGY_SELECTIVE_V2
    )
    expected_official_strategy = (
        expected_official_strategy or CONTEXT_STRATEGY_SELECTIVE_V2
    )
    candidate_sha256 = _require_digest(
        candidate_path, expected_candidate_sha256, "candidate"
    )
    admission_sha256 = _require_digest(
        admission_path, expected_admission_sha256, "admission report"
    )
    official_sha256 = _require_digest(
        official_path, expected_official_sha256, "protected official"
    )

    candidate = _load_object(candidate_path, "candidate")
    admission = _load_object(admission_path, "admission report")
    official = _load_object(official_path, "protected official")
    _validate_contract(
        candidate,
        admission,
        official,
        candidate_path=candidate_path,
        official_path=official_path,
        candidate_sha256=candidate_sha256,
        admission_sha256=admission_sha256,
        official_sha256=official_sha256,
        expected_binding=expected_binding,
        expected_candidate_strategy=expected_candidate_strategy,
        expected_official_strategy=expected_official_strategy,
    )

    promoted = deepcopy(candidate)
    promoted["official"] = True
    promoted["provider_complete"] = True
    promoted["benchmark_eligible"] = True
    promoted["reason"] = "promoted after provider-free admission audit"
    promoted["promotion"] = {
        "schema_version": 1,
        "candidate_path": admission["candidate_path"],
        "candidate_sha256": candidate_sha256,
        "admission_path": admission_path.as_posix(),
        "admission_sha256": admission_sha256,
        "previous_official_path": admission["baseline_path"],
        "previous_official_sha256": official_sha256,
        "binding": expected_binding,
        "context_strategy": expected_candidate_strategy,
        "candidate_context_strategy": expected_candidate_strategy,
        "previous_official_context_strategy": expected_official_strategy,
    }
    promoted_bytes = _canonical_json_bytes(promoted)
    promoted_sha256 = _sha256_bytes(promoted_bytes)
    archive_name = (
        f"{official_path.stem}_{official_sha256.removeprefix('sha256:')}"
        f"{official_path.suffix}"
    )
    archive_path = archive_dir / archive_name

    receipt = {
        "schema_version": 1,
        "applied": apply,
        "candidate_path": admission["candidate_path"],
        "candidate_sha256": candidate_sha256,
        "admission_path": admission_path.as_posix(),
        "admission_sha256": admission_sha256,
        "previous_official_path": admission["baseline_path"],
        "previous_official_sha256": official_sha256,
        "archive_path": archive_path.as_posix(),
        "promoted_official_sha256": promoted_sha256,
        "binding": expected_binding,
        "context_strategy": expected_candidate_strategy,
        "candidate_context_strategy": expected_candidate_strategy,
        "previous_official_context_strategy": expected_official_strategy,
        "metrics": promoted.get("metrics"),
    }

    if apply:
        old_official_bytes = official_path.read_bytes()
        if _sha256_bytes(old_official_bytes) != official_sha256:
            raise RuntimeError(
                "protected official changed after validation; refusing official write"
            )
        _preserve_archive(archive_path, old_official_bytes)
        if _file_sha256(official_path) != official_sha256:
            raise RuntimeError(
                "protected official changed after archival; refusing official write"
            )
        _write_atomic(official_path, promoted_bytes)
        if _file_sha256(official_path) != promoted_sha256:
            raise RuntimeError("post-write official SHA-256 verification failed")
        if receipt_path is not None:
            _write_atomic(receipt_path, _canonical_json_bytes(receipt))

    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--admission", type=Path, default=DEFAULT_ADMISSION)
    parser.add_argument("--official", type=Path, default=DEFAULT_OFFICIAL)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--expected-admission-sha256", required=True)
    parser.add_argument("--expected-official-sha256", required=True)
    parser.add_argument("--expected-binding", required=True)
    parser.add_argument(
        "--expected-strategy",
        default=None,
        help=(
            "Backward-compatible same-strategy expectation. Prefer the separate "
            "candidate and official strategy flags for cross-strategy promotion."
        ),
    )
    parser.add_argument("--expected-candidate-strategy", default=None)
    parser.add_argument("--expected-official-strategy", default=None)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply the validated promotion; omission performs a read-only dry run",
    )
    args = parser.parse_args(argv)

    receipt = promote(
        candidate_path=args.candidate,
        admission_path=args.admission,
        official_path=args.official,
        archive_dir=args.archive_dir,
        receipt_path=args.receipt,
        expected_candidate_sha256=args.expected_candidate_sha256,
        expected_admission_sha256=args.expected_admission_sha256,
        expected_official_sha256=args.expected_official_sha256,
        expected_binding=args.expected_binding,
        expected_strategy=args.expected_strategy,
        expected_candidate_strategy=args.expected_candidate_strategy,
        expected_official_strategy=args.expected_official_strategy,
        apply=args.apply,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
