"""Conservative whitespace-only correspondence for normalized original text."""
from __future__ import annotations

import hashlib
from typing import Any


MATCHER_VERSION = "sec-viewer-location-v1"


def _fold_with_map(value: str) -> tuple[str, list[tuple[int, int]]]:
    folded: list[str] = []
    mapping: list[tuple[int, int]] = []
    index = 0
    while index < len(value):
        if value[index].isspace():
            end = index + 1
            while end < len(value) and value[end].isspace():
                end += 1
            if folded and folded[-1] != " ":
                folded.append(" ")
                mapping.append((index, end))
            index = end
            continue
        folded.append(value[index])
        mapping.append((index, index + 1))
        index += 1
    while folded and folded[-1] == " ":
        folded.pop()
        mapping.pop()
    return "".join(folded), mapping


def whitespace_literal_matches(source_text: str, query: str) -> list[tuple[int, int]]:
    """Find case-sensitive literal matches after folding whitespace only."""
    folded_source, mapping = _fold_with_map(source_text)
    folded_query, _ = _fold_with_map(query.strip())
    if not folded_query:
        return []
    matches: list[tuple[int, int]] = []
    cursor = 0
    while True:
        found = folded_source.find(folded_query, cursor)
        if found < 0:
            break
        end = found + len(folded_query)
        matches.append((mapping[found][0], mapping[end - 1][1]))
        cursor = found + 1
    return matches


def bounded_preview(text: str, start: int, end: int, maximum: int = 240) -> str:
    if maximum <= 0:
        return ""
    left = max(0, start - min(80, maximum // 3))
    right = min(len(text), max(end, left) + maximum)
    if right - left > maximum:
        right = left + maximum
    if right - left < maximum and left > 0:
        left = max(0, right - maximum)
    return text[left:right]


def locate_chunk(
    snapshot: Any,
    chunk_text: str,
    chunk_text_hash: str,
    source_set_revision: str,
) -> dict[str, Any]:
    """Return exact/not-found/ambiguous/unavailable without guessing a source."""
    if snapshot.source_set_revision != source_set_revision:
        return {
            "status": "unavailable",
            "reason": "The original source set changed.",
            "match_count": 0,
            "match_count_capped": False,
            "location": None,
        }
    actual_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
    if actual_hash != chunk_text_hash:
        return {
            "status": "unavailable",
            "reason": "The indexed chunk changed.",
            "match_count": 0,
            "match_count_capped": False,
            "location": None,
        }
    if snapshot.status != "available" or any(source.status != "available" for source in snapshot.sources):
        return {
            "status": "unavailable",
            "reason": snapshot.reason or "The complete local source set is not available.",
            "match_count": 0,
            "match_count_capped": False,
            "location": None,
        }
    matches: list[tuple[Any, int, int]] = []
    for source in snapshot.sources:
        if source.normalized_text is None:
            continue
        for start, end in whitespace_literal_matches(source.normalized_text, chunk_text):
            matches.append((source, start, end))
            if len(matches) >= 2:
                return {
                    "status": "ambiguous",
                    "reason": "The indexed chunk matches more than one source interval.",
                    "match_count": 2,
                    "match_count_capped": True,
                    "location": None,
                }
    if not matches:
        return {
            "status": "not_found",
            "reason": "The full indexed chunk was not found in the admitted normalized sources.",
            "match_count": 0,
            "match_count_capped": False,
            "location": None,
        }
    source, start, end = matches[0]
    return {
        "status": "exact",
        "reason": None,
        "match_count": 1,
        "match_count_capped": False,
        "location": {
            "source_document_id": source.source_document_id,
            "document_revision": source.document_revision,
            "method": "full_text_whitespace",
            "start": start,
            "end": end,
        },
    }

