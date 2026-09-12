"""Conservative correspondence from indexed chunks to structured reader blocks."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from src.api.content_presentation import build_chunk_presentation
from src.api.document_reader_models import EvidenceLocation, EvidenceRange
from src.api.original_location import whitespace_literal_matches
from src.api.original_viewer import OriginalViewer
from src.api.structured_document import StructuredDocument, StructuredDocumentService


MATCHER_VERSION = "sec-structured-location-v1"
_NUMBER_ONLY = re.compile(r"[\s$€£¥,().%+\-0-9]+")


def _same_text(left: str, right: str) -> bool:
    return " ".join(left.split()) == " ".join(right.split())


def _table_matches(block: Any, table: dict[str, Any]) -> bool:
    if block.kind != "table" or not _same_text(block.caption or "", table.get("caption") or ""):
        return False
    if table.get("units") and not _same_text(block.units or "", str(table["units"])):
        return False
    columns = table.get("columns") or []
    if len(block.columns) != len(columns) or any(not _same_text(actual, str(expected)) for actual, expected in zip(block.columns, columns)):
        return False
    rows = [[cell.text for cell in row] for row in block.rows]
    if rows and all(_same_text(cell, column) for cell, column in zip(rows[0], block.columns)) and len(rows[0]) == len(block.columns):
        rows = rows[1:]
    expected_rows = table.get("rows") or []
    return len(rows) == len(expected_rows) and all(
        len(actual) == len(expected) and all(_same_text(value, str(expected_value)) for value, expected_value in zip(actual, expected))
        for actual, expected in zip(rows, expected_rows)
    )


def _text_ranges(document: StructuredDocument, chunk_text: str) -> list[list[EvidenceRange]]:
    parts: list[tuple[int, Any, int, int]] = []
    cursor = 0
    for index, block in enumerate(document.blocks):
        if block.kind not in {"heading", "paragraph", "list", "table"}:
            continue
        text = block.source_text or block.text
        if not text:
            continue
        start = cursor
        end = start + len(text)
        parts.append((index, block, start, end))
        cursor = end + 2
    combined = "\n\n".join(block.source_text or block.text for _, block, _, _ in parts)
    results: list[list[EvidenceRange]] = []
    for match_start, match_end in whitespace_literal_matches(combined, chunk_text):
        ranges: list[EvidenceRange] = []
        for index, block, block_start, block_end in parts:
            if match_end <= block_start or match_start >= block_end:
                continue
            start = max(match_start, block_start) - block_start
            end = min(match_end, block_end) - block_start
            if end > start:
                ranges.append(EvidenceRange(block_id=block.block_id, block_index=index, kind=block.kind, start=start, end=end, method="text_whitespace"))
        if ranges:
            results.append(ranges)
            if len(results) >= 2:
                break
    return results


def _base(chunk_id: str, chunk_hash: str, document_id: str, source_set_revision: str, status: str, reason: str | None, **extra: Any) -> EvidenceLocation:
    return EvidenceLocation(
        chunk_id=chunk_id,
        chunk_text_hash=chunk_hash,
        document_id=document_id,
        source_set_revision=source_set_revision,
        status=status,
        reason_code=status,
        reason=reason,
        **extra,
    )


class StructuredLocationService:
    """Resolve exact correspondence without fuzzy matching or source guessing."""

    def __init__(self, viewer: OriginalViewer, reader: StructuredDocumentService) -> None:
        self.viewer = viewer
        self.reader = reader

    def locate(self, row: dict[str, Any], chunk_id: str, chunk_text: str, chunk_text_hash: str, source_set_revision: str, section: str | None = None) -> EvidenceLocation:
        document_id = str(row["document_id"])
        snapshot = self.viewer.snapshot(row)
        if snapshot.source_set_revision != source_set_revision:
            return _base(chunk_id, chunk_text_hash, document_id, source_set_revision, "stale", "The original source set changed.")
        if hashlib.sha256(chunk_text.encode("utf-8")).hexdigest() != chunk_text_hash:
            return _base(chunk_id, chunk_text_hash, document_id, source_set_revision, "stale", "The indexed chunk changed.")
        if snapshot.status != "available" or not snapshot.sources or any(source.status != "available" or not source.document_revision for source in snapshot.sources):
            return _base(chunk_id, chunk_text_hash, document_id, source_set_revision, "unavailable", snapshot.reason or "The complete declared source set is not available.")

        table = build_chunk_presentation(chunk_text, section)
        table_mode = table.get("kind") == "markdown_table"
        if section == "financial_table" and not table_mode and _NUMBER_ONLY.fullmatch(chunk_text.strip() or ""):
            return _base(chunk_id, chunk_text_hash, document_id, source_set_revision, "not_found", "A numeric-only value is not sufficient to prove table correspondence.")
        candidates: list[tuple[Any, StructuredDocument, list[EvidenceRange], str]] = []
        for source in snapshot.sources:
            document = self.reader.document(row, source.source_document_id, source_set_revision, source.document_revision or "")
            if table_mode:
                for index, block in enumerate(document.blocks):
                    if _table_matches(block, table):
                        ranges = [EvidenceRange(block_id=block.block_id, block_index=index, kind="table", start=0, end=max(1, len(block.source_text)), method="table_semantic")]
                        candidates.append((source, document, ranges, "table_semantic"))
                        if len(candidates) >= 2:
                            break
            else:
                for ranges in _text_ranges(document, chunk_text):
                    candidates.append((source, document, ranges, "text_whitespace"))
                    if len(candidates) >= 2:
                        break
            if len(candidates) >= 2:
                break

        if len(candidates) == 0:
            return _base(chunk_id, chunk_text_hash, document_id, source_set_revision, "not_found", "The full indexed chunk was not found in the admitted structured sources.")
        if len(candidates) > 1:
            return _base(chunk_id, chunk_text_hash, document_id, source_set_revision, "ambiguous", "The indexed chunk matches more than one structured source interval.", match_count=2, match_count_capped=True)
        source, document, ranges, _method = candidates[0]
        return _base(
            chunk_id,
            chunk_text_hash,
            document_id,
            source_set_revision,
            "exact",
            None,
            source_document_id=source.source_document_id,
            document_revision=source.document_revision,
            representation_revision=document.representation_revision,
            ranges=ranges,
            match_count=1,
        )
