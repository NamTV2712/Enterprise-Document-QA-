"""Provider-free, fail-closed primitives for evidence receipt verifiers."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable


def file_same(first: Path | str, second: Path | str) -> bool:
    """Compare normalized paths and filesystem identity (including hardlinks)."""
    left, right = Path(first), Path(second)
    if os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve())):
        return True
    try:
        return left.samefile(right)
    except FileNotFoundError:
        return False


def file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def read_json(path: Path) -> Any:
    """Read strict JSON; callers turn IO/schema failures into NO-GO evidence."""
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object,
                      parse_constant=_invalid_constant)


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError) as error:
        return [], (f"cannot read checkpoint {path}: {error}",)
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line, object_pairs_hook=_object,
                                parse_constant=_invalid_constant)
            if not isinstance(record, dict):
                raise ValueError("record is not an object")
            records.append(record)
        except (ValueError, RecursionError) as error:
            errors.append(f"{path}:{number}: invalid JSON record ({error})")
    return records, tuple(errors)


def exact_records(
    records: Any,
    questions: Iterable[str],
    label: str = "records",
) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    """Index exactly one object per registered question without latest-wins loss."""
    expected = set(questions)
    indexed: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if not isinstance(records, list):
        return {}, (f"{label} must be a list",)
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get("question"), str):
            errors.append(f"{label}[{index}] must be an object with a string question")
            continue
        question = record["question"]
        if question not in expected:
            errors.append(f"{label} has extra question: {question}")
        elif question in indexed:
            errors.append(f"{label} has duplicate question: {question}")
        else:
            indexed[question] = record
    for question in sorted(expected - indexed.keys()):
        errors.append(f"{label} has missing question: {question}")
    return indexed, tuple(errors)


def valid_score(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
