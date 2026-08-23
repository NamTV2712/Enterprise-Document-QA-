"""Shared deterministic JSON serialization used by fingerprint helpers."""

from __future__ import annotations

import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize to stable UTF-8 bytes for hashing (sorted keys, compact)."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
