"""Conservative, provider-free fact evidence selection.

The selector narrows one fact lookup only when a single frozen chunk
self-contains the query's entity scope, metric anchors, and requested periods.
It deliberately treats partial and fuzzy lexical matches as diagnostic
evidence, never as authority for removing context.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from src.retrieval.lexical_ladder import lexical_ladder_candidates


FACT_CONTEXT_SELECTOR_VERSION = 1
FACT_CONTEXT_STRATEGY = "fact_evidence_sufficiency_v1"
FACT_CONTEXT_SELECTOR_FINGERPRINT = "sha256:" + hashlib.sha256(
    json.dumps(
        {
            "version": FACT_CONTEXT_SELECTOR_VERSION,
            "tier_order": [
                "structured_exact",
                "exact_phrase",
                "full_terms",
                "partial_terms_support_only",
                "fuzzy_diagnostic_only",
            ],
            "structured_score": 10.0,
            "entity_scope": "query-ticker-or-chunk-id-prefix",
            "periods": "all query years must occur in selected text",
            "metric_value_anchor": "metric alias within 35 normalized tokens of a number",
            "auditor_anchor": "auditor plus signature marker",
            "partial_authority": False,
            "fuzzy_authority": False,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()

# V1 remains frozen for historical artifacts. V2 only broadens safe profile
# normalization for generalization cases; it is selected explicitly by a new
# context strategy and therefore receives a new binding fingerprint.
FACT_CONTEXT_SELECTOR_VERSION_V2 = 2
FACT_CONTEXT_STRATEGY_V2 = "fact_evidence_sufficiency_v2"
FACT_CONTEXT_SELECTOR_FINGERPRINT_V2 = "sha256:" + hashlib.sha256(
    json.dumps(
        {
            "version": FACT_CONTEXT_SELECTOR_VERSION_V2,
            "based_on": FACT_CONTEXT_SELECTOR_FINGERPRINT,
            "owner_scope": "remove possessive owner terms after ticker/section scoping",
            "scaffolding": "years is non-semantic question scaffolding",
            "metric_precedence": ["net_income", "operating_income", "income"],
            "tier_order": [
                "structured_exact",
                "exact_phrase",
                "full_terms",
                "partial_terms_support_only",
                "fuzzy_diagnostic_only",
            ],
            "partial_authority": False,
            "fuzzy_authority": False,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()

STRUCTURED_EXACT_SCORE = 10.0

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_TOKEN_RE = re.compile(r"[a-z0-9]+")

_QUESTION_STOPWORDS = {
    "a",
    "about",
    "all",
    "an",
    "and",
    "as",
    "at",
    "be",
    "change",
    "company",
    "did",
    "does",
    "fiscal",
    "for",
    "from",
    "had",
    "how",
    "in",
    "is",
    "its",
    "of",
    "on",
    "or",
    "report",
    "signed",
    "the",
    "total",
    "to",
    "was",
    "what",
    "when",
    "were",
    "which",
    "who",
    "year",
}
_QUESTION_STOPWORDS_V2 = _QUESTION_STOPWORDS | {"years"}

_ENTITY_ALIASES = {
    "aapl": {"aapl", "apple", "apples"},
    "amzn": {"amzn", "amazon", "amazons"},
    "msft": {"msft", "microsoft", "microsofts"},
}

# Each group is an OR set, while all groups are required for a full match.
# These are generic semantic aliases, not evaluation labels or answer values.
_METRIC_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("net_sales", ("net sales", "sales")),
    ("total_assets", ("total assets", "assets")),
    ("operating_income", ("operating income",)),
    ("auditor", ("auditor", "audited", "audit", "accounting firm")),
    (
        "financial_statements",
        ("financial statements", "financial statement"),
    ),
    ("revenue", ("revenue", "net sales", "sales")),
    ("segments", ("business segments", "segments")),
    ("income", ("income",)),
)

_METRIC_GROUPS_V2: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("net_sales", ("net sales", "sales")),
    ("total_assets", ("total assets", "assets")),
    ("operating_income", ("operating income",)),
    ("net_income", ("net income", "income")),
    ("auditor", ("auditor", "audited", "audit", "accounting firm")),
    (
        "financial_statements",
        ("financial statements", "financial statement"),
    ),
    ("revenue", ("revenue", "net sales", "sales")),
    ("segments", ("business segments", "segments")),
    ("income", ("income",)),
)


def _normalise(text: str) -> str:
    return " ".join(_TOKEN_RE.findall(text.casefold()))


def _entry_ticker(entry: dict[str, Any]) -> str | None:
    ticker = entry.get("ticker")
    if isinstance(ticker, str) and ticker:
        return ticker.upper()
    chunk_id = entry.get("chunk_id")
    if isinstance(chunk_id, str) and "_" in chunk_id:
        return chunk_id.split("_", 1)[0].upper()
    return None


def _dedupe_entries(case_payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query_entry in case_payload.get("queries", []):
        for entry in query_entry.get("chunks", []):
            chunk_id = entry.get("chunk_id")
            if not isinstance(chunk_id, str) or chunk_id in seen:
                continue
            seen.add(chunk_id)
            entries.append(entry)
    return entries


def _query_entry(case_payload: dict[str, Any]) -> dict[str, Any] | None:
    query_entries = [
        entry
        for entry in case_payload.get("queries", [])
        if isinstance(entry.get("query"), dict)
    ]
    if not query_entries:
        return None
    return query_entries[0]


@dataclass(frozen=True)
class FactQueryProfile:
    ticker: str | None
    section: str | None
    periods: tuple[str, ...]
    metric_groups: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def exact_phrases(self) -> tuple[str, ...]:
        return tuple(
            alias
            for _, aliases in self.metric_groups
            for alias in aliases
        )

    @property
    def full_terms(self) -> tuple[str, ...]:
        return tuple(
            [aliases[0] for _, aliases in self.metric_groups]
            + list(self.periods)
        )

    @property
    def partial_terms(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                [
                    token
                    for _, aliases in self.metric_groups
                    for alias in aliases
                    for token in _TOKEN_RE.findall(alias)
                ]
                + list(self.periods)
            )
        )

    @property
    def fuzzy_terms(self) -> tuple[str, ...]:
        return self.partial_terms


def _possessive_owner_tokens(text: str) -> set[str]:
    """Return owner words already enforced by query ticker/section scope."""
    match = re.search(
        r"(?P<owner>[A-Za-z][A-Za-z .&-]*?)['’]s\b",
        text,
    )
    if match is None:
        return set()
    scaffolding = {
        "a",
        "an",
        "are",
        "did",
        "does",
        "how",
        "is",
        "the",
        "what",
        "was",
        "were",
    }
    return {
        token
        for token in _TOKEN_RE.findall(match.group("owner").casefold())
        if token not in scaffolding
    }


def _profile(
    case_payload: dict[str, Any],
    *,
    selector_version: int = FACT_CONTEXT_SELECTOR_VERSION,
) -> FactQueryProfile:
    query_entry = _query_entry(case_payload)
    query = (query_entry or {}).get("query") or {}
    text = (
        query.get("effective_query")
        or query.get("retrieval_query")
        or case_payload.get("question")
        or ""
    )
    normalised = _normalise(text)
    ticker = query.get("ticker")
    ticker = ticker.upper() if isinstance(ticker, str) and ticker else None
    section = query.get("section")
    section = section if isinstance(section, str) and section else None
    periods = tuple(dict.fromkeys(_YEAR_RE.findall(normalised)))
    groups: list[tuple[str, tuple[str, ...]]] = []
    metric_groups = (
        _METRIC_GROUPS_V2
        if selector_version >= FACT_CONTEXT_SELECTOR_VERSION_V2
        else _METRIC_GROUPS
    )
    for name, aliases in metric_groups:
        if any(_normalise(alias) in normalised for alias in aliases):
            if name == "revenue" and any(
                group_name == "net_sales" for group_name, _ in groups
            ):
                continue
            if name == "income" and any(
                group_name in {"operating_income", "net_income"}
                for group_name, _ in groups
            ):
                continue
            selected_aliases = aliases
            if name == "net_sales" and "net sales" in normalised:
                selected_aliases = ("net sales",)
            elif name == "total_assets" and "total assets" in normalised:
                selected_aliases = ("total assets",)
            elif name == "net_income" and "net income" in normalised:
                selected_aliases = ("net income",)
            groups.append((name, selected_aliases))

    # Preserve meaningful residual terms such as "AWS" that are not a
    # generic metric alias. Entity names and question scaffolding are excluded.
    entity_words = _ENTITY_ALIASES.get((ticker or "").casefold(), set())
    if selector_version >= FACT_CONTEXT_SELECTOR_VERSION_V2:
        entity_words = entity_words | _possessive_owner_tokens(text)
    question_stopwords = (
        _QUESTION_STOPWORDS_V2
        if selector_version >= FACT_CONTEXT_SELECTOR_VERSION_V2
        else _QUESTION_STOPWORDS
    )
    residual_tokens = []
    for token in _TOKEN_RE.findall(normalised):
        if (
            token in question_stopwords
            or token in entity_words
            or token in periods
            or len(token) < 3
        ):
            continue
        if any(token in _TOKEN_RE.findall(" ".join(aliases)) for _, aliases in groups):
            continue
        residual_tokens.append(token)
    for token in dict.fromkeys(residual_tokens):
        groups.append((f"term:{token}", (token,)))

    return FactQueryProfile(
        ticker=ticker,
        section=section,
        periods=periods,
        metric_groups=tuple(groups),
    )


def _scoped_entries(
    entries: Iterable[dict[str, Any]], profile: FactQueryProfile
) -> list[dict[str, Any]]:
    scoped: list[dict[str, Any]] = []
    for entry in entries:
        if profile.ticker and _entry_ticker(entry) != profile.ticker:
            continue
        if profile.section and entry.get("section") != profile.section:
            continue
        scoped.append(entry)
    return scoped


def _matches_group(text: str, aliases: tuple[str, ...]) -> bool:
    return any(_normalise(alias) in text for alias in aliases)


def _has_value_anchor(text: str, aliases: tuple[str, ...]) -> bool:
    """Require a metric mention to be close to a numeric value."""
    number = r"(?:\$\s*)?\(?\d[\d,]*(?:\.\d+)?%?"
    return any(
        re.search(
            rf"{re.escape(_normalise(alias))}(?:\s+\S+){{0,35}}\s+{number}",
            text,
        )
        for alias in aliases
    )


def _self_contained(entry: dict[str, Any], profile: FactQueryProfile) -> bool:
    text = _normalise(entry.get("text", ""))
    if not profile.metric_groups or not all(period in text for period in profile.periods):
        return False
    if {name for name, _ in profile.metric_groups} >= {
        "auditor",
        "financial_statements",
    }:
        # Auditor signatures may be in the report's opinion section without
        # repeating the phrase "financial statements" in the same chunk.
        auditor_ok = _matches_group(
            text, dict(profile.metric_groups)["auditor"]
        )
        signature_ok = bool(
            re.search(
                r"/s/|served as the company.?s auditor|public accounting firm",
                text,
            )
        )
        return auditor_ok and signature_ok
    for name, aliases in profile.metric_groups:
        if not _matches_group(text, aliases):
            return False
        if name in {
            "net_sales",
            "total_assets",
            "operating_income",
            "net_income",
            "revenue",
            "income",
        }:
            if not _has_value_anchor(text, aliases):
                return False
    return True


def _score(entry: dict[str, Any]) -> float:
    value = entry.get("score")
    return float(value) if isinstance(value, (int, float)) else float("-inf")


def _rank_safe(
    candidates: Iterable[dict[str, Any]],
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    index = {entry.get("chunk_id"): position for position, entry in enumerate(entries)}
    return sorted(
        candidates,
        key=lambda entry: (
            -_score(entry),
            index.get(entry.get("chunk_id"), len(entries)),
        ),
    )


def _ladder_candidates(
    scoped: list[dict[str, Any]],
    profile: FactQueryProfile,
    *,
    tier: str,
) -> list[dict[str, Any]]:
    kwargs = {
        "chunks": scoped,
        "ticker": None,
        "section": None,
        "max_candidates": len(scoped),
    }
    if tier == "exact_phrase":
        kwargs["exact_phrases"] = profile.exact_phrases
    elif tier == "full_terms":
        kwargs["full_terms"] = profile.full_terms
    elif tier == "partial_terms":
        kwargs["partial_terms"] = profile.partial_terms
    elif tier == "fuzzy":
        kwargs["fuzzy_terms"] = profile.fuzzy_terms
    return [match.chunk for match in lexical_ladder_candidates(**kwargs)]


@dataclass(frozen=True)
class FactContextSelection:
    """Selection plus audit metadata for one fact case."""

    tier: str
    profile: FactQueryProfile
    all_ids: tuple[str, ...]
    kept_ids: tuple[str, ...]
    partial_ids: tuple[str, ...] = ()
    fuzzy_ids: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.kept_ids != self.all_ids

    @property
    def safe(self) -> bool:
        return self.tier in {"structured_exact", "exact_phrase", "full_terms"}


def _select_fact_context(
    case_payload: dict[str, Any],
    *,
    selector_version: int,
) -> FactContextSelection:
    """Select one self-contained fact chunk, or preserve all evidence."""
    entries = _dedupe_entries(case_payload)
    all_ids = tuple(entry.get("chunk_id") for entry in entries)
    profile = _profile(case_payload, selector_version=selector_version)
    if case_payload.get("category") != "fact_lookup" or not entries:
        return FactContextSelection("not_applicable", profile, all_ids, all_ids)

    scoped = _scoped_entries(entries, profile)
    structured = [
        entry
        for entry in scoped
        if _score(entry) >= STRUCTURED_EXACT_SCORE
        and _self_contained(entry, profile)
    ]
    if structured:
        winner = _rank_safe(structured, entries)[0]
        return FactContextSelection(
            "structured_exact", profile, all_ids, (winner.get("chunk_id"),)
        )

    exact = [
        entry
        for entry in _ladder_candidates(scoped, profile, tier="exact_phrase")
        if _self_contained(entry, profile)
    ]
    if exact:
        winner = _rank_safe(exact, entries)[0]
        return FactContextSelection(
            "exact_phrase", profile, all_ids, (winner.get("chunk_id"),)
        )

    full = [
        entry
        for entry in _ladder_candidates(scoped, profile, tier="full_terms")
        if _self_contained(entry, profile)
    ]
    if full:
        winner = _rank_safe(full, entries)[0]
        return FactContextSelection(
            "full_terms", profile, all_ids, (winner.get("chunk_id"),)
        )

    partial = _ladder_candidates(scoped, profile, tier="partial_terms")
    fuzzy = _ladder_candidates(scoped, profile, tier="fuzzy")
    tier = "partial_terms_support_only" if partial else "no_safe_candidate"
    if fuzzy and not partial:
        tier = "fuzzy_diagnostic_only"
    return FactContextSelection(
        tier,
        profile,
        all_ids,
        all_ids,
        partial_ids=tuple(entry.get("chunk_id") for entry in partial),
        fuzzy_ids=tuple(entry.get("chunk_id") for entry in fuzzy),
    )


def select_fact_context(case_payload: dict[str, Any]) -> FactContextSelection:
    """Select one self-contained fact chunk using the frozen V1 profile."""
    return _select_fact_context(
        case_payload,
        selector_version=FACT_CONTEXT_SELECTOR_VERSION,
    )


def select_fact_context_v2(case_payload: dict[str, Any]) -> FactContextSelection:
    """Select one self-contained fact chunk using the explicit V2 profile."""
    return _select_fact_context(
        case_payload,
        selector_version=FACT_CONTEXT_SELECTOR_VERSION_V2,
    )


def selected_fact_entries(
    case_payload: dict[str, Any],
    selection: FactContextSelection | None = None,
) -> list[dict[str, Any]]:
    """Return selected entries in their original frozen source order."""
    selection = selection or select_fact_context(case_payload)
    selected = set(selection.kept_ids)
    return [entry for entry in _dedupe_entries(case_payload) if entry.get("chunk_id") in selected]


def selected_fact_entries_v2(case_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return entries selected by the explicit V2 fact selector."""
    return selected_fact_entries(case_payload, select_fact_context_v2(case_payload))
