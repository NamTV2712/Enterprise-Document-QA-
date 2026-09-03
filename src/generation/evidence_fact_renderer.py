"""Small provider-free renderers for facts exposed in structured filing text."""

from __future__ import annotations

import hashlib
import re

from src.generation.period_value_completeness import parse_evidence_sources


EVIDENCE_FACT_RENDERER_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"evidence-fact-renderer-v2-auditor-signature-normalize-split-uppercase-"
    b"single-period-net-sales-source-bound-unit-aware-no-ground-truth"
).hexdigest()

_AUDITOR_QUESTION_RE = re.compile(
    r"\bwho\s+audited\b.*\bfinancial\s+statements\b",
    re.IGNORECASE,
)
_CORPORATE_SUFFIX_RE = re.compile(
    r"\b(?:LLP|LLC|PLLC|P\.?C\.?|INC\.?|CORP(?:ORATION)?\.?)\b",
    re.IGNORECASE,
)
_SIGNATURE_RE = re.compile(r"/s/", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b20\d{2}\b")
_MONEY_RE = re.compile(r"^\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?$")
_NET_SALES_QUESTION_RE = re.compile(
    r"\bwhat\s+was\b.*\b(?P<label>(?:total|consolidated)\s+net\s+sales)\b"
    r".*?\b(?P<year>20\d{2})\b",
    re.IGNORECASE,
)


def _join_split_uppercase_words(value: str) -> str:
    """Repair filing line-wraps such as ``D ELOITTE`` and ``T OUCHE``."""
    value = re.sub(
        r"(?<![A-Za-z])([A-Z])\s+([A-Z]{2,})(?=\b)",
        r"\1\2",
        value,
    )
    return re.sub(r"\s+", " ", value).strip(" \t,;:")


def _signature_firm(text: str) -> str | None:
    match = _SIGNATURE_RE.search(text)
    if match is None:
        return None
    # The signature block is the first paragraph after ``/s/``.  Restricting
    # extraction to that block prevents the city/date and service-history
    # sentence from becoming part of the auditor name.
    paragraph = text[match.end():].split("\n\n", 1)[0]
    candidate = _join_split_uppercase_words(paragraph)
    candidate = re.sub(r"^[/\s]+", "", candidate)
    suffix = _CORPORATE_SUFFIX_RE.search(candidate)
    if suffix is None:
        return None
    candidate = candidate[: suffix.end()].strip()
    if not re.search(r"[A-Za-z]{3}", candidate):
        return None
    pretty = candidate.title()
    pretty = re.sub(r"\bLlp\b", "LLP", pretty)
    pretty = re.sub(r"\bLlc\b", "LLC", pretty)
    pretty = re.sub(r"\bP\.c\.\b", "P.C.", pretty, flags=re.IGNORECASE)
    pretty = re.sub(r"\bPlc\b", "PLC", pretty)
    return pretty


def _company_from_question(question: str) -> str | None:
    match = re.search(
        r"\bwho\s+audited\s+(?P<company>[A-Za-z][A-Za-z .&-]*?)"
        r"(?:'s|’s)\s+financial\s+statements",
        question,
        re.IGNORECASE,
    )
    return match.group("company").strip() if match else None


def render_auditor_fact(question: str, evidence_context: str) -> str | None:
    """Render an auditor answer only when the evidence contains a signature."""
    if not _AUDITOR_QUESTION_RE.search(question):
        return None
    company = _company_from_question(question)
    if not company:
        return None
    for source in parse_evidence_sources(evidence_context):
        firm = _signature_firm(source.text)
        if firm:
            return (
                f"{company}'s financial statements were audited by {firm} "
                f"[Source {source.number}]."
            )
    return None


def _numeric_tokens(lines: list[str]) -> list[str]:
    return [
        line.replace("$", "").strip()
        for line in lines
        if _MONEY_RE.fullmatch(line.replace("$", "").strip())
    ]


def _years_before(lines: list[str], index: int) -> list[str]:
    for start in range(max(0, index - 24), index):
        values = _YEAR_RE.findall(" ".join(lines[start:index]))
        if len(values) >= 2:
            return list(dict.fromkeys(values))
    return []


def _net_sales_value(source_text: str, label: str, year: str) -> str | None:
    """Extract one explicitly printed net-sales value from table-like text."""
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    target = label.casefold()
    for index, line in enumerate(lines):
        if "|" in line and target in line.casefold():
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            header: list[str] = []
            for prior in range(max(0, index - 5), index):
                candidate = _YEAR_RE.findall(lines[prior])
                if len(candidate) >= 2:
                    header = candidate
            values = _numeric_tokens(cells[1:])
            if year in header:
                position = header.index(year)
                if position < len(values):
                    return values[position]
        if target not in line.casefold():
            continue
        years = _years_before(lines, index)
        values = _numeric_tokens(lines[index + 1 : index + 14])
        if year in years:
            position = years.index(year)
            if position < len(values):
                return values[position]

    # Amazon's MD&A uses a section label (Net Sales) followed by segment
    # labels, so "Consolidated" is the row label for consolidated net sales.
    if target == "consolidated net sales":
        for index, line in enumerate(lines):
            if line.casefold().rstrip(":") != "consolidated":
                continue
            window_start = max(0, index - 16)
            if not any(
                value.casefold().rstrip(":") == "net sales"
                for value in lines[window_start:index]
            ):
                continue
            years = _years_before(lines, index)
            values = _numeric_tokens(lines[index + 1 : index + 8])
            if year in years:
                position = years.index(year)
                if position < len(values):
                    return values[position]
    return None


def render_single_period_net_sales_fact(
    question: str,
    evidence_context: str,
) -> str | None:
    """Render a direct net-sales fact when the evidence exposes one value."""
    match = _NET_SALES_QUESTION_RE.search(question)
    if match is None:
        return None
    company_match = re.search(
        r"\bwhat\s+was\s+(?P<company>[A-Za-z][A-Za-z .&-]*?)"
        r"(?:'s|’s)\s+(?:total|consolidated)\s+net\s+sales\b",
        question,
        re.IGNORECASE,
    )
    if company_match is None:
        return None
    company = company_match.group("company").strip()
    label = match.group("label")
    year = match.group("year")
    sources = parse_evidence_sources(evidence_context)
    for source in sources:
        value = _net_sales_value(source.text, label, year)
        if value is None:
            continue
        unit = " million" if any(
            re.search(r"\bin\s+millions\b|\bdollars\s+in\s+millions\b", item.text, re.I)
            for item in sources
        ) else ""
        return (
            f"{company}'s {label.lower()} in fiscal year {year} were "
            f"${value}{unit} [Source {source.number}]."
        )
    return None


def render_deterministic_fact(
    question: str,
    evidence_context: str,
) -> str | None:
    """Try the narrow provider-free fact renderers in priority order."""
    return render_auditor_fact(question, evidence_context) or render_single_period_net_sales_fact(
        question, evidence_context
    )
