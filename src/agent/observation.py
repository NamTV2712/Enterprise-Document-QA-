"""Deterministic bounded projections of untrusted tool output."""

from __future__ import annotations

import math
import re

from src.agent.models import ToolObservation
from src.agent.state import (
    AgentLimits, AgentObservation, EvidenceRecord, EvidenceRef, StageFact,
    contains_sensitive_text,
)
from src.api.schemas import (
    DiscoveryGroup, DiscoveryHit, DiscoverySnapshotResponse, QueryResponse,
)
from src.agent.models import DocumentObservation, RetrievalObservation


class ObservationLimitError(Exception):
    """Even a minimum structured projection does not fit the remaining budget."""


class ObservationIntegrityError(Exception):
    """A tool returned an unsafe or noncanonical identity or score."""


_REDACTIONS = (
    (re.compile(r"(?i)\bbearer\s+[^\s,;]+"), "[redacted credential]"),
    (re.compile(r"(?i)\bauthorization\s*:\s*[^\s,;]+(?:\s+[^\s,;]+)?"), "[redacted credential]"),
    (re.compile(r"(?i)\b(?:groq_)?api[_-]?key\d*\s*[:=]\s*[^\s,;]+"), "[redacted credential]"),
    (re.compile(r"(?i)\blocal_workspace_token\s*[:=]\s*[^\s,;]+"), "[redacted credential]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"), "[redacted credential]"),
    (re.compile(r"(?i)(?:\b[A-Z]:[\\/]|/home/|/Users/|file://)[^\s,;]*"), "[redacted path]"),
)


def _safe_text(value: str | None, limit: int) -> tuple[str, bool]:
    text = value or ""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text[:limit], len(text) > limit or text != (value or "")


def _scores(**values: float | None) -> dict[str, float | None]:
    if any(value is not None and not math.isfinite(value) for value in values.values()):
        raise ObservationIntegrityError("non-finite source score")
    return values


def _canonical(kind: str, value: str | None) -> str | None:
    if value is None:
        return None
    try:
        EvidenceRef(kind=kind, value=value)
    except (ValueError, TypeError) as error:
        raise ObservationIntegrityError("invalid canonical identity") from error
    return value


def _record(
    *, document_id: str | None = None, chunk_id: str | None = None,
    source_label: str | None = None, citation: str | None = None,
    score_kind: str | None = None, scores: dict[str, float | None] | None = None,
    excerpt: str = "", excerpt_limit: int,
) -> tuple[EvidenceRecord, bool]:
    if score_kind is not None and (len(score_kind) > 64 or contains_sensitive_text(score_kind)):
        raise ObservationIntegrityError("unsafe score family")
    bounded_excerpt, truncated = _safe_text(excerpt, excerpt_limit)
    bounded_citation, citation_truncated = _safe_text(citation, 256)
    return EvidenceRecord(
        document_id=_canonical("document_id", document_id),
        chunk_id=_canonical("chunk_id", chunk_id),
        source_label=source_label, citation=bounded_citation or None,
        score_kind=score_kind, scores=scores or {}, excerpt=bounded_excerpt,
    ), truncated or citation_truncated


def _extract(observation: ToolObservation, limits: AgentLimits) -> tuple[
    str | None, list[EvidenceRecord], list[StageFact], int, bool,
]:
    data = observation.data
    records: list[EvidenceRecord] = []
    stages: list[StageFact] = []
    truncated = False
    search_id: str | None = None
    reported_items = 0

    if isinstance(data, DiscoverySnapshotResponse):
        search_id = _canonical("search_id", data.search_id)
        reported_items = data.total
        hits: list[DiscoveryHit] = []
        for item in data.items:
            if isinstance(item, DiscoveryGroup):
                hits.extend(item.hits)
            else:
                hits.append(item)
        for hit in hits[:limits.max_evidence_per_observation]:
            record, cut = _record(
                document_id=hit.document_id, chunk_id=hit.chunk_id,
                score_kind=data.engine.key, scores=_scores(score=hit.score),
                excerpt=hit.snippet.text, excerpt_limit=limits.max_excerpt_chars,
            )
            records.append(record)
            truncated |= cut
        truncated |= len(hits) > limits.max_evidence_per_observation
    elif isinstance(data, RetrievalObservation):
        reported_items = data.trace.candidate_count
        for candidate in data.trace.candidates[:limits.max_evidence_per_observation]:
            record, cut = _record(
                document_id=candidate.document_id, chunk_id=candidate.chunk_id,
                citation=candidate.citation,
                scores=_scores(
                    bm25_score=candidate.bm25_score, dense_score=candidate.dense_score,
                    rrf_score=candidate.rrf_score, cross_encoder_score=candidate.cross_encoder_score,
                ),
                excerpt=candidate.text_preview, excerpt_limit=limits.max_excerpt_chars,
            )
            records.append(record)
            truncated |= cut
        truncated |= len(data.trace.candidates) > limits.max_evidence_per_observation
        stages = [
            StageFact(name=stage.name, status=stage.status, elapsed_ms=stage.elapsed_ms)
            for stage in data.trace.stages[:8]
        ]
        if any(len(stage.name) > 64 or contains_sensitive_text(stage.name) for stage in stages):
            raise ObservationIntegrityError("unsafe stage name")
        if any(stage.elapsed_ms is not None and not math.isfinite(stage.elapsed_ms) for stage in stages):
            raise ObservationIntegrityError("non-finite stage timing")
        truncated |= len(data.trace.stages) > 8
    elif isinstance(data, DocumentObservation):
        reported_items = data.total
        for chunk in data.items[:limits.max_evidence_per_observation]:
            record, cut = _record(
                document_id=data.document_id, chunk_id=chunk.chunk_id,
                excerpt=chunk.text_preview, excerpt_limit=limits.max_excerpt_chars,
            )
            records.append(record)
            truncated |= cut
        if not data.items:
            records.append(EvidenceRecord(document_id=_canonical("document_id", data.document_id)))
        truncated |= len(data.items) > limits.max_evidence_per_observation
    elif isinstance(data, QueryResponse):
        reported_items = data.num_chunks_retrieved
        for source in data.sources[:limits.max_evidence_per_observation]:
            source_label = f"[Source {source.rank}]" if source.rank is not None and source.rank > 0 else None
            record, cut = _record(
                document_id=source.document_id, chunk_id=source.chunk_id,
                source_label=source_label, citation=source.citation,
                score_kind=source.score_kind,
                scores=_scores(score=source.score, reranker_score=source.reranker_score),
                excerpt=source.text_preview, excerpt_limit=limits.max_excerpt_chars,
            )
            records.append(record)
            truncated |= cut
        truncated |= len(data.sources) > limits.max_evidence_per_observation
    else:  # pragma: no cover - AGENT-001's typed union excludes other outputs
        raise ObservationLimitError("unsupported tool observation")
    return search_id, records, stages, reported_items, truncated


def project_observation(
    observation: ToolObservation, limits: AgentLimits, remaining_bytes: int,
) -> AgentObservation:
    """Keep whole identities and score fields; discard text or records at a boundary."""
    budget = min(limits.max_observation_bytes, remaining_bytes)
    search_id, records, stages, reported_items, truncated = _extract(observation, limits)

    def build() -> AgentObservation:
        return AgentObservation(
            tool_name=observation.tool_name, search_id=search_id,
            evidence=tuple(records), stages=tuple(stages),
            reported_items=reported_items, truncated=truncated,
        )

    projected = build()
    while len(projected.model_dump_json().encode("utf-8")) > budget:
        truncated = True
        if records and records[-1].excerpt:
            records[-1] = records[-1].model_copy(update={"excerpt": ""})
        elif records:
            records.pop()
        elif stages:
            stages.pop()
        else:
            raise ObservationLimitError("minimum observation exceeds byte budget")
        projected = build()
    return projected
