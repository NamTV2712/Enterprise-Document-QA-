"""Provider-free discovery search over the already-loaded serving corpus.

Discovery is deliberately separate from RAG retrieval and from the diagnostic
Retrieval Lab: it scores indexed chunk text with the in-memory BM25 model the
retriever already built at startup, so a search never embeds a query, runs a
cross-encoder, calls a provider, touches Qdrant, or reads SEC. It is read-only:
no corpus, index, evaluation, or workspace state is written.

The module is pure apart from the bounded in-process snapshot store, which is
given an injectable clock so expiry is testable without sleeping.
"""

from __future__ import annotations

import re
import secrets
import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from src.api.catalog import build_facets, filter_documents

# Bounds. Every value is a hard ceiling enforced here, not a UI convention.
MAX_QUERY_LENGTH = 200
MIN_QUERY_LENGTH = 2
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50
CANDIDATE_CEILING = 200
SNIPPET_MAX_LENGTH = 240
SNIPPET_MAX_RANGES = 8
SNAPSHOT_TTL_SECONDS = 900
MAX_SNAPSHOTS = 50

SUPPORTED_MODES = ("keyword",)
SUPPORTED_GROUPINGS = ("document", "chunk")
RANKING_ENGINE = {
    "key": "bm25_lexical",
    "version": "v1",
    "definition": (
        "Chunks that contain at least one query term match; BM25 lexical score over "
        "indexed chunk text orders them. The score is a ranking signal for keyword "
        "matching, not a confidence, accuracy, or probability, and a zero score means "
        "the term occurs without being discriminative."
    ),
}
# A bounded result set must never be read as a corpus total.
COUNT_SCOPE_BOUNDED = "bounded_candidates"
COUNT_SCOPE_EMPTY = "no_matches"

_SNAPSHOT_ID = re.compile(r"^search-[0-9a-f]{16}$")
_SNIPPET_WINDOW = 24


class DiscoveryError(ValueError):
    """A bounded, content-free discovery validation error."""


def normalize_query(raw: str) -> str:
    """Return the deterministic retrieval form of a user query.

    Only whitespace and case are normalized; no synonym expansion, stemming, or
    provider rewriting is applied, so the same input always searches the same
    terms. Unicode is preserved.
    """
    if not isinstance(raw, str):
        raise DiscoveryError("discovery query must be text")
    collapsed = " ".join(raw.split())
    if len(collapsed) < MIN_QUERY_LENGTH:
        raise DiscoveryError(
            f"discovery query must contain at least {MIN_QUERY_LENGTH} non-space characters"
        )
    if len(collapsed) > MAX_QUERY_LENGTH:
        raise DiscoveryError(
            f"discovery query must be at most {MAX_QUERY_LENGTH} characters"
        )
    return collapsed.casefold()


def validate_mode(mode: str) -> str:
    if mode not in SUPPORTED_MODES:
        raise DiscoveryError(
            f"unsupported discovery mode. Supported modes: {', '.join(SUPPORTED_MODES)}"
        )
    return mode


def validate_grouping(group_by: str) -> str:
    if group_by not in SUPPORTED_GROUPINGS:
        raise DiscoveryError(
            "unsupported discovery grouping. Supported groupings: "
            + ", ".join(SUPPORTED_GROUPINGS)
        )
    return group_by


def validate_page(page: int, page_size: int) -> tuple[int, int]:
    if page < 1:
        raise DiscoveryError("discovery page must be at least 1")
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise DiscoveryError(
            f"discovery page size must be between 1 and {MAX_PAGE_SIZE}"
        )
    return page, page_size


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class DiscoveryScope:
    """The exact scope one snapshot was computed under."""

    ticker: str | None = None
    section: str | None = None
    year: int | None = None
    filing_date: str | None = None

    def as_payload(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "section": self.section,
            "year": self.year,
            "filing_date": self.filing_date,
        }


@dataclass(frozen=True)
class Snippet:
    """Bounded real-text excerpt with safe character ranges."""

    text: str
    ranges: tuple[tuple[int, int], ...]
    truncated: bool

    def as_payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "ranges": [[start, end] for start, end in self.ranges],
            "truncated": self.truncated,
        }


@dataclass(frozen=True)
class DiscoveryHit:
    """One ranked chunk hit with its canonical identity preserved."""

    chunk_id: str
    document_id: str
    ticker: str | None
    section: str | None
    filing_date: str | None
    report_date: str | None
    chunk_index: int | None
    score: float
    snippet: Snippet

    def as_payload(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "ticker": self.ticker,
            "section": self.section,
            "filing_date": self.filing_date,
            "report_date": self.report_date,
            "chunk_index": self.chunk_index,
            "score": round(self.score, 6),
            "snippet": self.snippet.as_payload(),
        }


@dataclass(frozen=True)
class DiscoveryGroup:
    """One grouped result (a document) with its best-matching hits."""

    document_id: str
    ticker: str | None
    filing_date: str | None
    report_date: str | None
    sections: tuple[str, ...]
    best_score: float
    hit_count: int
    hits: tuple[DiscoveryHit, ...]

    def as_payload(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "ticker": self.ticker,
            "filing_date": self.filing_date,
            "report_date": self.report_date,
            "sections": list(self.sections),
            "best_score": round(self.best_score, 6),
            "hit_count": self.hit_count,
            "hits": [hit.as_payload() for hit in self.hits],
        }


@dataclass(frozen=True)
class DiscoveryResult:
    """One immutable ranked result set for a snapshot."""

    hits: tuple[DiscoveryHit, ...]
    groups: tuple[DiscoveryGroup, ...]
    matched_documents: int
    matched_chunks: int
    limited_by_ceiling: bool


def build_snippet(text: str, query_terms: Sequence[str]) -> Snippet:
    """Return a bounded real-text excerpt with the matched term ranges.

    The window starts at the first matched term when one exists, otherwise at
    the beginning of the chunk. Ranges index into the returned text, so the
    frontend can highlight without receiving HTML.
    """
    collapsed = " ".join(text.split())
    if not collapsed:
        return Snippet(text="", ranges=(), truncated=False)

    lowered = collapsed.casefold()
    first_match = -1
    for term in query_terms:
        if not term:
            continue
        position = lowered.find(term)
        if position != -1 and (first_match == -1 or position < first_match):
            first_match = position

    start = 0 if first_match == -1 else max(0, first_match - _SNIPPET_WINDOW)
    window = collapsed[start : start + SNIPPET_MAX_LENGTH]
    truncated = start + SNIPPET_MAX_LENGTH < len(collapsed)
    if start > 0 and window:
        window = f"…{window}"
    if truncated:
        window = f"{window}…"

    window_lowered = window.casefold()
    ranges: list[tuple[int, int]] = []
    for term in query_terms:
        if not term:
            continue
        cursor = 0
        while len(ranges) < SNIPPET_MAX_RANGES:
            position = window_lowered.find(term, cursor)
            if position == -1:
                break
            ranges.append((position, position + len(term)))
            cursor = position + len(term)
    ranges.sort()
    merged: list[tuple[int, int]] = []
    for start_offset, end_offset in ranges[:SNIPPET_MAX_RANGES]:
        if merged and start_offset <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end_offset))
            continue
        merged.append((start_offset, end_offset))
    return Snippet(text=window, ranges=tuple(merged), truncated=truncated)


def rank_chunks(
    chunks: Sequence[dict[str, Any]],
    score_terms: Sequence[str],
    highlight_terms: Sequence[str],
    score_for: Callable[[Sequence[str]], Sequence[float]],
    *,
    present_for: Callable[[Sequence[str]], Sequence[bool]] | None = None,
    allowed_documents: set[str] | None,
    document_id_of: Callable[[dict[str, Any]], str],
    ceiling: int = CANDIDATE_CEILING,
) -> DiscoveryResult:
    """Return the bounded ranked result set for one scope.

    ``score_terms`` are in the index tokenizer's space (so scoring agrees with
    the BM25 model the retriever built), while ``highlight_terms`` are the
    literal query words, which is what a reader expects to see highlighted.
    ``score_for`` returns the retriever's own BM25 scores for every loaded
    chunk, so nothing here re-implements scoring and no model is ever called.

    Matching uses real term presence (``present_for``) and ranking uses the
    BM25 score, so a term that occurs in most of the corpus still matches even
    though its inverse document frequency — and therefore its score — is zero.
    """
    if not score_terms:
        return DiscoveryResult(hits=(), groups=(), matched_documents=0, matched_chunks=0, limited_by_ceiling=False)

    scores = score_for(list(score_terms))
    present = (
        present_for(list(score_terms))
        if present_for is not None
        else [score > 0 for score in scores]
    )
    ranked: list[tuple[float, dict[str, Any]]] = []
    for chunk, score, has_term in zip(chunks, scores, present):
        if not has_term:
            continue
        if allowed_documents is not None and document_id_of(chunk) not in allowed_documents:
            continue
        ranked.append((float(score), chunk))

    # Deterministic order: score, then the canonical chunk and document ids.
    ranked.sort(
        key=lambda item: (
            -item[0],
            str(item[1].get("chunk_id") or ""),
            document_id_of(item[1]),
        )
    )
    limited = len(ranked) > ceiling
    bounded = ranked[:ceiling]

    hits = tuple(
        DiscoveryHit(
            chunk_id=str(chunk.get("chunk_id") or ""),
            document_id=document_id_of(chunk),
            ticker=chunk.get("ticker"),
            section=chunk.get("section"),
            filing_date=chunk.get("filing_date"),
            report_date=chunk.get("report_date"),
            chunk_index=chunk.get("chunk_index"),
            score=score,
            snippet=build_snippet(str(chunk.get("text") or ""), highlight_terms),
        )
        for score, chunk in bounded
    )

    grouped: dict[str, list[DiscoveryHit]] = {}
    order: list[str] = []
    for hit in hits:
        if hit.document_id not in grouped:
            grouped[hit.document_id] = []
            order.append(hit.document_id)
        grouped[hit.document_id].append(hit)

    groups: list[DiscoveryGroup] = []
    for document_id in order:
        document_hits = grouped[document_id]
        first = document_hits[0]
        section_values = tuple(
            sorted({hit.section for hit in document_hits if hit.section})
        )
        groups.append(
            DiscoveryGroup(
                document_id=document_id,
                ticker=first.ticker,
                filing_date=first.filing_date,
                report_date=first.report_date,
                sections=section_values,
                best_score=max(hit.score for hit in document_hits),
                hit_count=len(document_hits),
                hits=tuple(document_hits),
            )
        )

    return DiscoveryResult(
        hits=hits,
        groups=tuple(groups),
        matched_documents=len(groups),
        matched_chunks=len(hits),
        limited_by_ceiling=limited,
    )


@dataclass
class DiscoverySnapshot:
    """One stored, immutable discovery result set with its expiry."""

    search_id: str
    query_text: str
    normalized_query: str
    query_terms: tuple[str, ...]
    mode: str
    group_by: str
    scope: DiscoveryScope
    scope_documents: int
    facets: list[dict[str, Any]]
    result: DiscoveryResult
    created_at: datetime
    expires_at: datetime

    def as_payload(self, page: int, page_size: int) -> dict[str, Any]:
        total = len(self.result.groups) if self.group_by == "document" else len(self.result.hits)
        items = (
            [group.as_payload() for group in self.result.groups]
            if self.group_by == "document"
            else [hit.as_payload() for hit in self.result.hits]
        )
        start = (page - 1) * page_size
        return {
            "search_id": self.search_id,
            "query": {
                "text": self.query_text,
                "normalized": self.normalized_query,
                "mode": self.mode,
            },
            "grouping": {
                "group_by": self.group_by,
                "group_count": len(self.result.groups),
                "hit_count": len(self.result.hits),
            },
            "engine": dict(RANKING_ENGINE),
            "scope": {
                **self.scope.as_payload(),
                "documents": self.scope_documents,
                "count_scope": COUNT_SCOPE_BOUNDED if total else COUNT_SCOPE_EMPTY,
                "candidate_ceiling": CANDIDATE_CEILING,
                "limited_by_ceiling": self.result.limited_by_ceiling,
                "matched_documents": self.result.matched_documents,
                "matched_chunks": self.result.matched_chunks,
            },
            "items": items[start : start + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
            "facets": self.facets,
            "created_at": _timestamp(self.created_at),
            "expires_at": _timestamp(self.expires_at),
            "ttl_seconds": SNAPSHOT_TTL_SECONDS,
        }


class DiscoverySnapshotStore:
    """Bounded in-process snapshot store for the single-worker topology.

    It holds at most ``MAX_SNAPSHOTS`` entries and evicts the earliest expiring
    entry first, so the resident set cannot grow without bound. Expiry is
    computed from an injectable clock and never extended by a read.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = SNAPSHOT_TTL_SECONDS,
        max_entries: int = MAX_SNAPSHOTS,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._lock = threading.RLock()
        self._snapshots: dict[str, DiscoverySnapshot] = {}

    def _evict_expired(self, now: datetime) -> None:
        for search_id in [
            key
            for key, snapshot in self._snapshots.items()
            if snapshot.expires_at <= now
        ]:
            self._snapshots.pop(search_id, None)

    def _enforce_bound(self) -> None:
        while len(self._snapshots) > self.max_entries:
            oldest = min(
                self._snapshots,
                key=lambda key: (self._snapshots[key].expires_at, key),
            )
            self._snapshots.pop(oldest, None)

    def store(
        self,
        *,
        query_text: str,
        normalized_query: str,
        query_terms: Sequence[str],
        mode: str,
        group_by: str,
        scope: DiscoveryScope,
        scope_documents: int,
        facets: list[dict[str, Any]],
        result: DiscoveryResult,
    ) -> DiscoverySnapshot:
        now = self._clock()
        with self._lock:
            self._evict_expired(now)
            snapshot = DiscoverySnapshot(
                search_id=f"search-{secrets.token_hex(8)}",
                query_text=query_text,
                normalized_query=normalized_query,
                query_terms=tuple(query_terms),
                mode=mode,
                group_by=group_by,
                scope=scope,
                scope_documents=scope_documents,
                facets=facets,
                result=result,
                created_at=now,
                expires_at=now + timedelta(seconds=self.ttl_seconds),
            )
            self._snapshots[snapshot.search_id] = snapshot
            self._enforce_bound()
            return snapshot

    def get(self, search_id: str) -> DiscoverySnapshot | None:
        """Return a live snapshot, or None for an unknown or expired id."""
        if not _SNAPSHOT_ID.fullmatch(search_id):
            return None
        now = self._clock()
        with self._lock:
            snapshot = self._snapshots.get(search_id)
            if snapshot is None:
                return None
            if snapshot.expires_at <= now:
                self._snapshots.pop(search_id, None)
                return None
            return snapshot

    def status(self, search_id: str) -> str:
        """Return ``live``, ``expired``, or ``unknown`` for one snapshot id.

        Expired entries are dropped here, so the distinction is only available
        to the request that observes the expiry first; afterwards the id reads
        as unknown, which is the truthful state for a rejected snapshot.
        """
        if not _SNAPSHOT_ID.fullmatch(search_id):
            return "unknown"
        now = self._clock()
        with self._lock:
            snapshot = self._snapshots.get(search_id)
            if snapshot is None:
                return "unknown"
            if snapshot.expires_at <= now:
                self._snapshots.pop(search_id, None)
                return "expired"
            return "live"

    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)


def discovery_scope_documents(
    rows: Iterable[dict[str, Any]],
    scope: DiscoveryScope,
) -> list[dict[str, Any]]:
    """Return catalog rows for a discovery scope using the API-003 filters."""
    return filter_documents(
        rows,
        ticker=scope.ticker,
        section=scope.section,
        year=scope.year,
        filing_date=scope.filing_date,
    )


def discovery_query_terms(normalized_query: str) -> tuple[str, ...]:
    """Return the literal query words used for snippet highlight ranges.

    Unicode-aware so accented and Vietnamese words stay whole, and casefolded
    defensively so a caller that skipped normalization cannot silently drop a
    leading capital. Scoring uses the index tokenizer separately.
    """
    terms = [
        term
        for term in re.findall(r"[^\W_]+", normalized_query.casefold(), re.UNICODE)
        if term
    ]
    return tuple(dict.fromkeys(terms))


class DiscoveryService:
    """Provider-free keyword discovery over the loaded serving corpus.

    The service receives everything it needs from the application boundary —
    the loaded chunks, the retriever's index tokenizer and BM25 scorer, the
    catalog rows, and the document-id function — so it never constructs a
    model, store, or provider and never mutates corpus or workspace state.
    """

    def __init__(
        self,
        *,
        chunks: Callable[[], Sequence[dict[str, Any]]],
        catalog_rows: Callable[[], Sequence[dict[str, Any]]],
        tokenize: Callable[[str], list[str]],
        score: Callable[[list[str]], Sequence[float]],
        document_id_of: Callable[[dict[str, Any]], str],
        present: Callable[[list[str]], Sequence[bool]] | None = None,
        snapshot_store: DiscoverySnapshotStore | None = None,
        ceiling: int = CANDIDATE_CEILING,
    ) -> None:
        self._chunks = chunks
        self._catalog_rows = catalog_rows
        self._tokenize = tokenize
        self._score = score
        self._present = present
        self._document_id_of = document_id_of
        self.snapshots = snapshot_store or DiscoverySnapshotStore()
        self.ceiling = ceiling

    def search(
        self,
        *,
        query: str,
        mode: str = "keyword",
        group_by: str = "document",
        ticker: str | None = None,
        section: str | None = None,
        year: int | None = None,
        filing_date: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> DiscoverySnapshot:
        """Run one discovery search and store its snapshot."""
        validate_mode(mode)
        validate_grouping(group_by)
        validate_page(page, page_size)
        normalized = normalize_query(query)
        query_text = " ".join(query.split())
        scope = DiscoveryScope(
            ticker=ticker, section=section, year=year, filing_date=filing_date
        )

        rows = list(self._catalog_rows())
        scope_rows = discovery_scope_documents(rows, scope)
        allowed_documents = {str(row["document_id"]) for row in scope_rows}

        chunks = list(self._chunks())
        result = rank_chunks(
            chunks,
            self._tokenize(normalized),
            discovery_query_terms(normalized),
            self._score,
            present_for=self._present,
            allowed_documents=allowed_documents,
            document_id_of=self._document_id_of,
            ceiling=self.ceiling,
        )
        # The facet payload is API-003's own aggregation for the same scope, so
        # discovery counts and catalog counts cannot disagree.
        facets = build_facets(
            rows,
            ticker=ticker,
            section=section,
            year=year,
            filing_date=filing_date,
        )["facets"]

        return self.snapshots.store(
            query_text=query_text,
            normalized_query=normalized,
            query_terms=discovery_query_terms(normalized),
            mode=mode,
            group_by=group_by,
            scope=scope,
            scope_documents=len(scope_rows),
            facets=facets,
            result=result,
        )
