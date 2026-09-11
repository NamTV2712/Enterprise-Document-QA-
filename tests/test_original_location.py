from __future__ import annotations

import hashlib
from types import SimpleNamespace

from src.api.original_location import locate_chunk, whitespace_literal_matches


def _snapshot(texts: list[str], status: str = "available") -> SimpleNamespace:
    sources = tuple(
        SimpleNamespace(
            source_document_id=f"source-{index}",
            document_revision=f"revision-{index}",
            status="available",
            normalized_text=text,
        )
        for index, text in enumerate(texts)
    )
    return SimpleNamespace(source_set_revision="set-1", status=status, reason=None, sources=sources)


def test_whitespace_match_is_case_sensitive_and_reports_overlaps() -> None:
    assert whitespace_literal_matches("Revenue\n$100 Revenue", "Revenue") == [(0, 7), (13, 20)]
    assert whitespace_literal_matches("Revenue", "revenue") == []


def test_location_requires_one_full_chunk_match() -> None:
    chunk = "Revenue $100"
    result = locate_chunk(_snapshot(["Heading\nRevenue   $100\nTail"]), chunk, hashlib.sha256(chunk.encode()).hexdigest(), "set-1")
    assert result["status"] == "exact"
    assert result["location"]["method"] == "full_text_whitespace"


def test_location_is_ambiguous_or_not_found_without_guessing() -> None:
    chunk = "Revenue"
    digest = hashlib.sha256(chunk.encode()).hexdigest()
    assert locate_chunk(_snapshot(["Revenue Revenue"]), chunk, digest, "set-1")["status"] == "ambiguous"
    assert locate_chunk(_snapshot(["Other text"]), chunk, digest, "set-1")["status"] == "not_found"
    assert locate_chunk(_snapshot(["Revenue"]), chunk, "0" * 64, "set-1")["status"] == "unavailable"


def test_location_is_unavailable_when_inventory_is_incomplete() -> None:
    chunk = "Revenue"
    digest = hashlib.sha256(chunk.encode()).hexdigest()
    result = locate_chunk(_snapshot(["Revenue"], status="partial"), chunk, digest, "set-1")
    assert result["status"] == "unavailable"

