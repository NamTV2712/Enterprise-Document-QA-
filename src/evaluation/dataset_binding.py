"""Canonical API-006 identity and revision for the built-in evaluation set."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import asdict

from src.evaluation.test_set import TestCase
from src.retrieval.canonical_json import canonical_json_bytes

EVALUATION_DATASET_ID = "evaluation-test-set"
EVALUATION_DATASET_VERSION = "evaluation-test-set-v1"


def evaluation_dataset_revision(cases: Sequence[TestCase]) -> str:
    """Preserve API-006's ordered full-TestCase SHA-256 revision exactly."""
    encoded = canonical_json_bytes([asdict(case) for case in cases])
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
