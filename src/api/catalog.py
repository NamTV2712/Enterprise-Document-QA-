"""Provider-free catalog facets and statistics over loaded document metadata.

Every value here derives from the startup document catalog, which is built
from embedded chunk metadata. This module reads no filing text, constructs no
model, provider, client, or store, and never mutates corpus, index, evaluation,
or workspace state. It is pure aggregation so the same rows always produce the
same payload.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from configs.tickers import TICKERS

# Canonical section order for the loaded corpus. This is the single source of
# truth; ``src.api.app`` re-exports it so existing imports keep working.
SUPPORTED_SECTIONS: list[str] = [
    "business",
    "risk_factors",
    "mdna",
    "financial_statements",
    "financial_table",
]

FACET_COMPANY = "company"
FACET_YEAR = "year"
FACET_SECTION = "section"
FACET_DIMENSIONS: tuple[str, ...] = (FACET_COMPANY, FACET_YEAR, FACET_SECTION)

# Counts describe the applied filters minus the facet's own dimension, which is
# the standard faceted-navigation contract: a facet tells a user what selecting
# one of its values would leave.
FACET_COUNT_BASIS = "all_filters_except_own_dimension"

SORT_FIELDS: tuple[str, ...] = ("ticker", "filing_date", "chunk_count", "document_id")
DEFAULT_SORT = "ticker"

# Documents are ingested as 10-K filings only, but the stored per-filing
# artifacts record no form type, so the catalog reports the dimension as
# unknown instead of inventing a constant.
FILING_TYPE_UNAVAILABLE_REASON = (
    "Stored filing artifacts record no per-filing form type."
)
REPORT_DATE_UNAVAILABLE_REASON = (
    "No loaded document records a report date."
)
SECTION_METADATA_UNAVAILABLE_REASON = (
    "No loaded document records a section."
)
FILING_DATE_UNAVAILABLE_REASON = (
    "No loaded document records a filing date."
)
EMPTY_CATALOG_REASON = "The catalog contains no documents."


def dimension_availability(
    present: int,
    documents: int,
    missing_reason: str,
) -> tuple[str, str | None]:
    """Return the availability state and reason for one catalog dimension.

    An empty catalog is not evidence that a dimension is recorded: it reports
    ``unknown`` so a consumer cannot read an empty list as a real zero.
    """
    if documents == 0:
        return "unknown", EMPTY_CATALOG_REASON
    if present == 0:
        return "unknown", missing_reason
    return "recorded", None


def catalog_timestamp() -> str:
    """Return the response timestamp in the project's UTC ISO-8601 form."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def filing_year(row: dict[str, Any]) -> int | None:
    """Return the filing year recorded by a document row, or None when absent."""
    value = row.get("filing_date")
    if not isinstance(value, str) or len(value) < 4 or not value[:4].isdigit():
        return None
    return int(value[:4])


def document_matches(
    row: dict[str, Any],
    *,
    ticker: str | None = None,
    section: str | None = None,
    year: int | None = None,
    filing_date: str | None = None,
    search: str | None = None,
) -> bool:
    """Return whether one catalog row satisfies every supplied filter."""
    if ticker is not None and row.get("ticker") != ticker:
        return False
    if section is not None and section not in (row.get("sections") or ()):
        return False
    if year is not None and filing_year(row) != year:
        return False
    if filing_date is not None and row.get("filing_date") != filing_date:
        return False
    if search:
        haystack = " ".join(
            str(row.get(field) or "")
            for field in ("document_id", "ticker", "filing_date", "accession_number")
        ).casefold()
        if search.casefold().strip() not in haystack:
            return False
    return True


def filter_documents(
    rows: Iterable[dict[str, Any]],
    *,
    ticker: str | None = None,
    section: str | None = None,
    year: int | None = None,
    filing_date: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Return the catalog rows matching every supplied filter, in catalog order."""
    return [
        row
        for row in rows
        if document_matches(
            row,
            ticker=ticker,
            section=section,
            year=year,
            filing_date=filing_date,
            search=search,
        )
    ]


def sort_documents(
    rows: Iterable[dict[str, Any]],
    sort: str = DEFAULT_SORT,
    direction: str = "asc",
) -> list[dict[str, Any]]:
    """Return rows in a deterministic order for a supported sort field.

    ``document_id`` is always the final tiebreaker so equal keys keep one
    stable order rather than depending on the input order.
    """
    if sort not in SORT_FIELDS:
        raise ValueError("unsupported document sort field")
    if direction not in {"asc", "desc"}:
        raise ValueError("unsupported document sort direction")
    reverse = direction == "desc"

    def primary(row: dict[str, Any]) -> Any:
        value = row.get(sort)
        return int(value or 0) if sort == "chunk_count" else str(value or "")

    # The identifier tiebreaker is applied outside the reversed comparison so a
    # descending primary sort still leaves ties in a stable ascending order.
    ordered = sorted(rows, key=lambda row: str(row.get("document_id") or ""))
    ordered.sort(key=primary, reverse=reverse)
    return ordered


def _counts_by(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _company_facet(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = _counts_by(str(row.get("ticker") or "") for row in rows if row.get("ticker"))
    return [
        {"value": ticker, "count": counts[ticker]}
        for ticker in sorted(counts)
    ]


def _year_facet(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    counts: dict[int, int] = {}
    missing = 0
    for row in rows:
        year = filing_year(row)
        if year is None:
            missing += 1
            continue
        counts[year] = counts.get(year, 0) + 1
    values = [{"value": year, "count": counts[year]} for year in sorted(counts, reverse=True)]
    return values, missing


def _section_facet(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    counts: dict[str, int] = {}
    without_sections = 0
    for row in rows:
        sections = row.get("sections") or ()
        if not sections:
            without_sections += 1
            continue
        for section in sections:
            counts[str(section)] = counts.get(str(section), 0) + 1
    known = [section for section in SUPPORTED_SECTIONS if section in counts]
    extra = sorted(section for section in counts if section not in SUPPORTED_SECTIONS)
    values = [{"value": section, "count": counts[section]} for section in (*known, *extra)]
    return values, without_sections


def build_facets(
    rows: list[dict[str, Any]],
    *,
    ticker: str | None = None,
    section: str | None = None,
    year: int | None = None,
    filing_date: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """Return deterministic facet values and counts for the applied scope.

    Each facet excludes its own dimension from the filters it counts over, so a
    company facet reports what selecting a company would leave while the other
    filters stay applied. Empty dimensions still return an explicit availability
    reason instead of a fabricated or silently zero value.
    """
    common = {"filing_date": filing_date, "search": search}
    company_rows = filter_documents(rows, section=section, year=year, **common)
    year_rows = filter_documents(rows, ticker=ticker, section=section, **common)
    section_rows = filter_documents(rows, ticker=ticker, year=year, **common)

    year_values, documents_without_filing_date = _year_facet(year_rows)
    section_values, documents_without_sections = _section_facet(section_rows)
    company_values = _company_facet(company_rows)

    company_availability, company_reason = dimension_availability(
        len(company_rows) - sum(1 for row in company_rows if not row.get("ticker")),
        len(company_rows),
        "No loaded document records a ticker.",
    )
    year_availability, year_reason = dimension_availability(
        sum(value["count"] for value in year_values),
        len(year_rows),
        FILING_DATE_UNAVAILABLE_REASON,
    )
    section_availability, section_reason = dimension_availability(
        sum(1 for row in section_rows if row.get("sections")),
        len(section_rows),
        SECTION_METADATA_UNAVAILABLE_REASON,
    )

    return {
        "generated_at": catalog_timestamp(),
        "count_basis": FACET_COUNT_BASIS,
        "scope": {
            "ticker": ticker,
            "section": section,
            "year": year,
            "filing_date": filing_date,
            "search": search,
            "documents": len(
                filter_documents(
                    rows,
                    ticker=ticker,
                    section=section,
                    year=year,
                    filing_date=filing_date,
                    search=search,
                )
            ),
        },
        "facets": [
            {
                "dimension": FACET_COMPANY,
                "availability": company_availability,
                "reason": company_reason,
                "values": company_values,
            },
            {
                "dimension": FACET_YEAR,
                "availability": year_availability,
                "reason": year_reason,
                "documents_without_value": documents_without_filing_date,
                "values": year_values,
            },
            {
                "dimension": FACET_SECTION,
                "availability": section_availability,
                "reason": section_reason,
                "documents_without_value": documents_without_sections,
                "values": section_values,
            },
        ],
    }


def build_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return truthful corpus counts and per-dimension availability.

    ``availability`` distinguishes a recorded dimension from one the stored
    metadata never carries: an unknown dimension still reports its count but
    also a reason, so a consumer cannot read "0" as "the corpus contains none".
    """
    tickers = {str(row.get("ticker")) for row in rows if row.get("ticker")}
    chunks = sum(int(row.get("chunk_count") or 0) for row in rows)
    year_values, documents_without_filing_date = _year_facet(rows)
    section_values, documents_without_sections = _section_facet(rows)
    documents_with_report_date = sum(1 for row in rows if row.get("report_date"))
    configured = [ticker for ticker in TICKERS if ticker in tickers]
    configured_missing = [ticker for ticker in TICKERS if ticker not in tickers]

    filing_date_availability, filing_date_reason = dimension_availability(
        sum(value["count"] for value in year_values),
        len(rows),
        FILING_DATE_UNAVAILABLE_REASON,
    )
    report_date_availability, report_date_reason = dimension_availability(
        documents_with_report_date,
        len(rows),
        REPORT_DATE_UNAVAILABLE_REASON,
    )
    section_availability, section_reason = dimension_availability(
        sum(1 for row in rows if row.get("sections")),
        len(rows),
        SECTION_METADATA_UNAVAILABLE_REASON,
    )

    return {
        "generated_at": catalog_timestamp(),
        "documents": len(rows),
        "companies": len(tickers),
        "chunks": chunks,
        "configured_companies": len(TICKERS),
        "configured_companies_without_documents": configured_missing,
        "filing_dates": {
            "availability": filing_date_availability,
            "reason": filing_date_reason,
            "earliest": min((value["value"] for value in year_values), default=None),
            "latest": max((value["value"] for value in year_values), default=None),
            "documents_without_value": documents_without_filing_date,
        },
        "report_dates": {
            "availability": report_date_availability,
            "reason": report_date_reason,
            "documents_with_value": documents_with_report_date,
        },
        "sections": {
            "availability": section_availability,
            "reason": section_reason,
            "documents_without_value": documents_without_sections,
            "values": section_values,
        },
        "filing_type": {
            "availability": "unknown",
            "reason": FILING_TYPE_UNAVAILABLE_REASON,
            "value": None,
        },
        "configured_companies_with_documents": configured,
    }
