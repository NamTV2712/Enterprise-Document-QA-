"""Provider-free fact extraction for multi-company comparisons.

The extractor is intentionally conservative. It records nearby evidence for
metric/value pairs, but it does not decide which company wins a comparison.
That decision belongs to a contract or renderer with an explicit compatibility
rule.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal

from src.company_entities import detect_tickers
from src.generation.period_value_completeness import EvidenceSource, parse_evidence_sources


COMPARATIVE_EVIDENCE_CONTRACT_VERSION = 2
COMPARATIVE_EVIDENCE_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-evidence-v2-metric-value-period-unit-source-compatibility"
).hexdigest()

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?:[$€£]\s*)?(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    r"(?:\s*(?:%|million|billion|thousand|bn|mm))?",
    re.IGNORECASE,
)
_METRIC_RE = re.compile(
    r"\b(?:microsoft\s+cloud\s+revenue|microsoft\s+cloud|cloud\s+revenue|"
    r"cloud\s+services|cloud|services\s+net\s+sales|services|net\s+sales|"
    r"total\s+revenue|revenue|sales|subscriptions?|depend(?:s|ence|ency)?)\b",
    re.IGNORECASE,
)
_SHARE_RE = re.compile(
    r"\b(?:share|proportion|percent(?:age)?\s+of|%\s+of|of\s+total)\b",
    re.IGNORECASE,
)
_DEPENDENCY_RE = re.compile(
    r"\b(?:depend(?:s|ed|ence|ency)|reli(?:es|ance|ant)|reliant)\b",
    re.IGNORECASE,
)
_VALUE_RE = re.compile(
    r"\b(?:higher|lower|more|less|largest|smallest|growth|grew|increase|"
    r"increased|decrease|decreased|value|amount|revenue|sales|depends?|"
    r"reliance|reliant)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ComparativeFact:
    """One metric/value candidate tied to one rendered source."""

    ticker: str
    source_number: int
    metric: str
    value: str
    period: str | None
    unit: str | None
    evidence_text: str
    has_explicit_share: bool

    @property
    def normalized_metric(self) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", self.metric.casefold()))


@dataclass(frozen=True)
class ComparativeQuestionIntent:
    """The comparison dimension requested by a question."""

    mode: str
    metric_terms: tuple[str, ...]
    requested_periods: tuple[str, ...]
    requires_numeric_evidence: bool
    requires_share_evidence: bool


def _compact(value: str) -> str:
    return " ".join(value.split())


def _source_ticker(source: EvidenceSource) -> str | None:
    tickers = detect_tickers(source.citation)
    return tickers[0] if len(tickers) == 1 else None


def _unit_for_value(value: str, window: str, source_text: str) -> str | None:
    lowered = value.casefold()
    if "%" in value or re.search(r"\bpercent(?:age)?\b", lowered):
        return "%"
    for unit in ("billion", "million", "thousand", "bn", "mm"):
        if re.search(rf"\b{re.escape(unit)}\b", lowered):
            return unit
    if (
        "$" in value
        or "dollars" in window.casefold()
        or "usd" in window.casefold()
        or re.search(r"\bdollars?\s+in\s+millions?\b", source_text, re.I)
    ):
        # A table-level unit applies to the row when the source explicitly
        # declares its scale. It is still attached to this source, never to a
        # fact from another company.
        if re.search(r"\b(?:in|dollars? in)\s+millions?\b", source_text, re.I):
            return "million USD"
        return "USD"
    return None


def _metric_for_window(window: str) -> str | None:
    matches = list(_METRIC_RE.finditer(window))
    if not matches:
        return None
    # Prefer the most specific phrase present near the value.
    return max(matches, key=lambda match: len(match.group(0))).group(0)


def _metric_for_position(text: str, start: int, end: int) -> str | None:
    """Find a metric label immediately before a value in prose or a table."""
    preceding_start = max(0, start - 90)
    preceding = text[preceding_start:start]
    matches = list(_METRIC_RE.finditer(preceding))
    if matches:
        match = matches[-1]
        between = text[preceding_start + match.end() : start]
        # A metric from the preceding sentence cannot authorize a number in a
        # filing footer, page marker, or unrelated following sentence.
        if "." in between or ";" in between:
            return None
        return match.group(0)
    return None


def _evidence_window(text: str, start: int, end: int) -> str:
    left = max(0, start - 100)
    right = min(len(text), end + 100)
    return _compact(text[left:right]).strip(" -:;,.\n")


def _segment_for_position(text: str, start: int, end: int) -> str:
    """Return one sentence/table row around a numeric token."""
    punctuation_positions = [
        position
        for position in range(max(0, start - 180), start)
        if text[position] in ".;"
        and not (
            text[position] == "."
            and position > 0
            and position + 1 < len(text)
            and text[position - 1].isdigit()
            and text[position + 1].isdigit()
        )
    ]
    left_boundaries = [text.rfind("\n", 0, start), *(punctuation_positions or [-1])]
    left = max(left_boundaries) + 1
    right_candidates = []
    for position in (text.find("\n", end), text.find(".", end), text.find(";", end)):
        if position < 0:
            continue
        if (
            text[position] == "."
            and position > 0
            and position + 1 < len(text)
            and text[position - 1].isdigit()
            and text[position + 1].isdigit()
        ):
            continue
        right_candidates.append(position)
    right = min(right_candidates) if right_candidates else len(text)
    segment = _compact(text[left:right]).strip(" -:,.\n")
    if len(segment) < 12:
        return _evidence_window(text, start, end)
    return segment


def extract_comparative_facts(
    question: str,
    evidence_context: str,
) -> dict[str, tuple[ComparativeFact, ...]]:
    """Extract metric/value candidates grouped by company ticker."""
    expected = detect_tickers(question)
    result: dict[str, list[ComparativeFact]] = {ticker: [] for ticker in expected}
    for source in parse_evidence_sources(evidence_context):
        ticker = _source_ticker(source)
        if ticker not in result:
            continue
        text = source.text
        for match in _NUMBER_RE.finditer(text):
            value = _compact(match.group(0))
            if _YEAR_RE.fullmatch(value.replace(",", "")):
                continue
            window = _segment_for_position(text, match.start(), match.end())
            metric = _metric_for_position(text, match.start(), match.end())
            if metric is None:
                continue
            periods = tuple(dict.fromkeys(_YEAR_RE.findall(window)))
            result[ticker].append(
                ComparativeFact(
                    ticker=ticker,
                    source_number=source.number,
                    metric=metric,
                    value=value,
                    period=periods[-1] if periods else None,
                    unit=_unit_for_value(value, window, text),
                    evidence_text=window,
                    has_explicit_share=bool(_SHARE_RE.search(window)),
                )
            )
    return {ticker: tuple(facts) for ticker, facts in result.items()}


def classify_comparative_question(question: str) -> ComparativeQuestionIntent:
    """Classify only the comparison dimension expressed in the question."""
    lowered = question.casefold()
    periods = tuple(dict.fromkeys(_YEAR_RE.findall(question)))
    if _DEPENDENCY_RE.search(question):
        mode = "dependency"
    elif re.search(r"\b(?:growth|grew|increase|decrease|trend)\b", lowered):
        mode = "growth"
    elif re.search(r"\b(?:higher|lower|largest|smallest|value|amount)\b", lowered):
        mode = "value"
    else:
        mode = "qualitative"
    terms: list[str] = []
    if re.search(r"\bcloud\b|\bazure\b|\baws\b", lowered):
        terms.append("cloud")
    if re.search(r"\bsubscription", lowered):
        terms.append("subscription")
    if re.search(r"\bservices?\b", lowered):
        terms.append("services")
    if re.search(r"\brevenue|sales\b", lowered):
        terms.append("revenue")
    return ComparativeQuestionIntent(
        mode=mode,
        metric_terms=tuple(dict.fromkeys(terms)),
        requested_periods=periods,
        requires_numeric_evidence=mode in {"dependency", "growth", "value"}
        or bool(_VALUE_RE.search(question)),
        requires_share_evidence=mode == "dependency",
    )


def facts_match_intent(
    question: str,
    facts_by_ticker: dict[str, tuple[ComparativeFact, ...]],
) -> dict[str, tuple[ComparativeFact, ...]]:
    """Keep facts with the requested metric and period when possible."""
    intent = classify_comparative_question(question)
    terms = intent.metric_terms
    if intent.mode == "dependency":
        specific_terms = tuple(term for term in terms if term != "revenue")
        if specific_terms:
            terms = specific_terms
    aliases = {
        "cloud": ("cloud", "azure", "aws"),
        "subscription": ("subscription", "services"),
        "services": ("services", "subscription"),
        "revenue": ("revenue", "sales", "net sales"),
    }
    selected: dict[str, tuple[ComparativeFact, ...]] = {}
    for ticker, facts in facts_by_ticker.items():
        matching = tuple(
            fact
            for fact in facts
            if (
                not terms
                or any(
                    alias in fact.normalized_metric
                    for term in terms
                    for alias in aliases.get(term, (term,))
                )
            )
            and (
                not intent.requested_periods
                or fact.period is None
                or fact.period in intent.requested_periods
            )
        )
        # For a dependency question, a generic revenue/sales fact is not a
        # valid substitute for a requested cloud/services branch. Falling back
        # to arbitrary facts would recreate the original false-positive guard.
        selected[ticker] = (
            matching
            if intent.mode == "dependency" and any(term != "revenue" for term in terms)
            else matching or facts
        )
    return selected


# V3 is an opt-in contract. The v2 extractor and fingerprints above are frozen.
COMPARATIVE_EVIDENCE_V3_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-evidence-v3.1-strict-row-column-local-units-period-kind-"
    b"denominator-latest-known-conflict-abstention-shared-selection"
).hexdigest()

_V3_METRIC_RE = re.compile(
    r"\b(?:Microsoft Cloud revenue|server products and cloud services revenue|"
    r"cloud(?:/subscription)? revenue|subscription revenue|services net sales|"
    r"services revenue|cloud services|subscriptions?|services|total net sales|"
    r"total revenue|net sales|revenue)\b", re.I,
)
_V3_VALUE_RE = re.compile(
    r"(?<![\w.])(?:USD|EUR|GBP|[$€£])?\s*"
    r"(?P<number>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:\s*(?P<scale>billion|million|thousand|bn|mm))?"
    r"(?:\s*(?P<percent>%|percent\b))?", re.I,
)
_V3_FOOTNOTE_RE = re.compile(r"\(\d{1,2}\)|\[\d{1,2}\]|[†‡*]")
_V3_DENOMINATOR_RE = re.compile(
    r"^\s*of\s+(?:(?:the company|its|company)['’]?s?\s+)?"
    r"(?P<denominator>(?:total|consolidated|segment|domestic|international)\s+"
    r"(?:net\s+)?(?:revenue|sales))\b", re.I,
)


@dataclass(frozen=True)
class ComparativeFactV3:
    """A value bound to a row/column or sentence, never a nearby metric."""

    ticker: str
    source_number: int
    metric: str
    value: str
    numeric_value: Decimal
    currency: str | None
    scale: str | None
    period: str | None
    location: str
    kind: str
    denominator: str | None
    evidence_text: str

    @property
    def normalized_metric(self) -> str:
        metric = self.metric.casefold()
        metric = re.sub(r"^microsoft\s+(?=cloud revenue)", "", metric)
        return " ".join(re.findall(r"[a-z0-9]+", metric))

    @property
    def has_explicit_share(self) -> bool:
        return self.kind == "share" and self.denominator is not None

    @property
    def unit(self) -> str | None:
        if self.kind in {"share", "growth", "percentage"}:
            return "%"
        return " ".join(part for part in (self.scale, self.currency) if part) or None


@dataclass(frozen=True)
class DependencySelectionV3:
    """The single evidence decision consumed by rendering and assessment."""

    applicable: bool
    expected_tickers: tuple[str, ...]
    facts_by_ticker: dict[str, tuple[ComparativeFactV3, ...]]
    selected_by_ticker: dict[str, ComparativeFactV3 | None]
    excerpts_by_ticker: dict[str, tuple[int, str] | None]
    compatible: bool
    winners: tuple[str, ...]
    reason_codes: tuple[str, ...]

    @property
    def evidence_sufficient(self) -> bool:
        return self.applicable and all(
            self.selected_by_ticker[ticker] or self.excerpts_by_ticker[ticker]
            for ticker in self.expected_tickers
        )


def _v3_period(text: str) -> str | None:
    """Only a single explicit observation period is unambiguous in prose."""
    years = set(_YEAR_RE.findall(text))
    if len(years) != 1 or re.search(r"\b(?:filed|form\s+10-k)\b", text, re.I):
        return None
    year = next(iter(years))
    quarter = re.search(r"\bQ([1-4])\b", text, re.I)
    if quarter:
        return f"Q{quarter[1]} {year}"
    if re.search(r"\b(?:quarter|months|weeks)\b", text, re.I):
        return None
    return year


def _v3_units(text: str) -> tuple[str | None, str | None]:
    currencies = {
        currency for currency, pattern in (
            ("USD", r"\bUSD\b|\$|\bdollars?\b"),
            ("EUR", r"\bEUR\b|€|\beuros?\b"),
            ("GBP", r"\bGBP\b|£|\bpounds?\b"),
        ) if re.search(pattern, text, re.I)
    }
    scales = {
        scale for scale, pattern in (
            ("billion", r"\bbillions?\b|\bbn\b"),
            ("million", r"\bmillions?\b|\bmm\b"),
            ("thousand", r"\bthousands?\b"),
        ) if re.search(pattern, text, re.I)
    }
    return (next(iter(currencies)) if len(currencies) == 1 else None,
            next(iter(scales)) if len(scales) == 1 else None)


def _v3_fact(source: EvidenceSource, ticker: str, metric: str, raw: str,
             period: str | None, location: str, evidence: str,
             units: str = "", kind: str = "amount",
             denominator: str | None = None) -> ComparativeFactV3 | None:
    match = _V3_VALUE_RE.fullmatch(raw.strip())
    if not match:
        return None
    number = Decimal(match["number"].replace(",", ""))
    if match["percent"]:
        if kind == "amount":
            kind = "percentage"
        if kind == "share" and not 0 <= number <= 100:
            return None
        currency, scale = None, None
    else:
        currency, scale = _v3_units(raw + " " + units)
    return ComparativeFactV3(
        ticker, source.number, metric, _compact(raw), number, currency, scale,
        period, location, kind, denominator, evidence,
    )


def _v3_source_facts(source: EvidenceSource, ticker: str) -> list[ComparativeFactV3]:
    facts: list[ComparativeFactV3] = []
    lines = source.text.splitlines()
    columns: list[str] = []
    units = ""
    section = ""
    scoped_period = None
    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                continue
            if any(_v3_period(cell) for cell in cells[1:]):
                # Preserve every column, including change columns, in its position.
                columns = cells[1:]
                continue
            label = _V3_FOOTNOTE_RE.sub("", cells[0]).strip()
            if not columns or len(cells) != len(columns) + 1 or not _V3_METRIC_RE.search(label):
                continue
            for index, (header, raw) in enumerate(zip(columns, cells[1:]), 1):
                period = _v3_period(header)
                if period is None or re.search(r"change|growth", header, re.I):
                    continue
                denominator_match = re.search(r"(?:%|percent|share)\s+of\s+(.+)", label, re.I)
                denominator = None
                metric = label
                if denominator_match:
                    bound = _V3_DENOMINATOR_RE.match("of " + denominator_match[1])
                    if bound:
                        denominator = _compact(bound["denominator"].casefold())
                        metric = label[:denominator_match.start()].strip(" ()")
                kind = "margin" if "margin" in (section + label).casefold() else "amount"
                if denominator and re.search(r"%|percent", raw, re.I):
                    kind = "share"
                fact = _v3_fact(source, ticker, metric, _V3_FOOTNOTE_RE.sub("", raw),
                                period, f"line:{line_number}:column:{index}", line,
                                units, kind, denominator)
                if fact:
                    facts.append(fact)
            continue
        columns = []
        if re.match(r"Units\s*:", stripped, re.I):
            units = stripped
            continue
        if stripped.startswith("#"):
            section = stripped
            units = ""
            scoped_period = None
            continue
        highlights = re.fullmatch(
            r"Highlights from fiscal year ((?:19|20)\d{2}) compared with fiscal year "
            r"(?:19|20)\d{2} included:", stripped, re.I,
        )
        if highlights:
            scoped_period = highlights[1]
            continue
        # A period heading may scope following prose, but never filing metadata.
        if re.fullmatch(r"(?:Fiscal year |FY\s*|Q[1-4]\s+)(?:19|20)\d{2}:?", stripped, re.I):
            scoped_period = _v3_period(stripped)
            continue
        if not _V3_METRIC_RE.search(stripped):
            if re.search(r"[A-Za-z]", stripped) and not stripped.endswith(":"):
                scoped_period = None
            continue
        # Flattened numeric-only lines are handled separately; prose needs a verb.
        for sentence in re.split(r"(?<=[.;])\s+(?=[A-Z])", stripped):
            metric_match = _V3_METRIC_RE.search(sentence)
            if metric_match is None:
                continue
            metric = metric_match[0]
            prefix = sentence[:metric_match.start()]
            # Do not shorten an unknown metric (e.g. deferred revenue or costs).
            prefix = re.sub(r"\b(?:in|for|fiscal|year|FY|Microsoft|Apple|Q[1-4]|\d{4})\b", "", prefix, flags=re.I)
            if re.search(r"[A-Za-z0-9]", prefix):
                continue
            tail = sentence[metric_match.end():]
            if not re.match(r"\s+(?:was|were|is|are|accounted for|represented|"
                            r"increased|decreased|grew|reached|totaled)\b", tail, re.I):
                continue
            period = _v3_period(sentence)
            if not _YEAR_RE.search(sentence):
                period = scoped_period
            for value_match in _V3_VALUE_RE.finditer(tail):
                raw = value_match[0].strip()
                if _YEAR_RE.fullmatch(raw):
                    continue
                before = tail[:value_match.start()]
                after = tail[value_match.end():]
                denom_match = _V3_DENOMINATOR_RE.match(after) if value_match["percent"] else None
                denominator = _compact(denom_match["denominator"].casefold()) if denom_match else None
                kind = "amount"
                if value_match["percent"]:
                    kind = "share" if denominator else "growth" if re.search(
                        r"increased|decreased|grew|growth", before, re.I) else "percentage"
                elif re.search(r"increased|decreased|grew", before, re.I) and not re.search(r"\bto\s*$", before, re.I):
                    kind = "delta"
                if kind == "amount" and not (_v3_units(raw) != (None, None) or re.search(r"\b(?:was|were|is|are|reached|totaled)\s*$", before, re.I)):
                    continue
                fact = _v3_fact(source, ticker, metric, raw, period,
                                f"line:{line_number}:offset:{metric_match.end() + value_match.start()}",
                                sentence, "", kind, denominator)
                if fact:
                    facts.append(fact)

    # Flattened tables: bind only a complete row to a preceding year header.
    # Without a header, preserve unknown periods; selection refuses ambiguity.
    nonempty = [(i + 1, line.strip()) for i, line in enumerate(lines) if line.strip()]
    years: list[str] = []
    flat_units = ""
    flat_kind = "amount"
    for index, (line_number, line) in enumerate(nonempty):
        if "|" in line:
            years, flat_units, flat_kind = [], "", "amount"
            continue
        if "gross margin" in line.casefold():
            flat_kind = "margin"
        if re.search(r"(?:dollars|USD)\s+in\s+millions", line, re.I):
            flat_units = line
        if _YEAR_RE.fullmatch(line):
            if index == 0 or not _YEAR_RE.fullmatch(nonempty[index - 1][1]):
                years = []
            years.append(line)
            continue
        label = _V3_FOOTNOTE_RE.sub("", line).strip()
        if not _V3_METRIC_RE.fullmatch(label):
            if len(line.split()) > 6:
                years = []
            continue
        row: list[str] = []
        cursor = index + 1
        while cursor < len(nonempty):
            token = nonempty[cursor][1]
            if _V3_FOOTNOTE_RE.fullmatch(token):
                cursor += 1
                continue
            currency = ""
            if token in {"$", "€", "£"} and cursor + 1 < len(nonempty):
                currency = token
                cursor += 1
                token = nonempty[cursor][1]
            if not _V3_VALUE_RE.fullmatch(token) or _YEAR_RE.fullmatch(token):
                break
            if cursor + 1 < len(nonempty) and nonempty[cursor + 1][1] == "%":
                cursor += 2  # Change percentages cannot become revenue amounts.
                continue
            row.append(currency + token)
            cursor += 1
        if years and len(row) != len(years):
            continue
        for column, raw in enumerate(row):
            fact = _v3_fact(source, ticker, label, raw,
                            years[column] if years else None,
                            f"line:{line_number}:flat-column:{column + 1}",
                            "\n".join(value for _, value in nonempty[index:cursor]),
                            flat_units, flat_kind)
            if fact:
                facts.append(fact)
    return facts


def extract_comparative_facts_v3(question: str, context: str) -> dict[str, tuple[ComparativeFactV3, ...]]:
    """Extract v3 facts without changing the production v2 path."""
    result: dict[str, list[ComparativeFactV3]] = {ticker: [] for ticker in detect_tickers(question)}
    for source in parse_evidence_sources(context):
        ticker = _source_ticker(source)
        if ticker in result:
            result[ticker].extend(_v3_source_facts(source, ticker))
    return {ticker: tuple(facts) for ticker, facts in result.items()}


def select_dependency_evidence_v3(question: str, context: str) -> DependencySelectionV3:
    """Choose latest known observations before checking share compatibility."""
    intent = classify_comparative_question(question)
    expected = detect_tickers(question)
    applicable = intent.mode == "dependency" and len(expected) >= 2
    terms = tuple(term for term in intent.metric_terms if term != "revenue") or ("revenue", "sales")
    aliases = {"subscription": ("subscription", "services"), "cloud": ("cloud", "azure", "aws")}

    def relevant(text: str) -> bool:
        return any(alias in text.casefold() for term in terms for alias in aliases.get(term, (term,)))

    facts = {
        ticker: tuple(fact for fact in branch if relevant(fact.metric)
                      and fact.kind in {"amount", "share"}
                      and (not intent.requested_periods or fact.period in intent.requested_periods))
        for ticker, branch in extract_comparative_facts_v3(question, context).items()
    }
    chosen: dict[str, ComparativeFactV3 | None] = {}
    reasons: list[str] = []
    def period_key(period: str | None) -> tuple[int, int, int]:
        if period is None:
            return (-1, -1, -1)
        year_match = re.search(r"(19|20)\d{2}$", period)
        year = int(year_match[0]) if year_match else -1
        quarter_match = re.match(r"Q([1-4])\b", period)
        # A fiscal year observation is preferred to no period; a quarter is
        # ordered within the year but never inferred from filing metadata.
        quarter = int(quarter_match[1]) if quarter_match else 0
        return (year, quarter, 1 if quarter_match else 0)

    for ticker, branch in facts.items():
        known = [fact for fact in branch if fact.period is not None]
        if known and not intent.requested_periods:
            latest = max(period_key(fact.period) for fact in known)
            branch = tuple(fact for fact in known if period_key(fact.period) == latest)
        shares = tuple(fact for fact in branch if fact.has_explicit_share)
        candidates = shares or branch
        identities = {(fact.normalized_metric, fact.numeric_value, fact.currency,
                       fact.scale, fact.period, fact.kind, fact.denominator)
                      for fact in candidates}
        chosen[ticker] = candidates[0] if len(identities) == 1 else None
        if len(identities) > 1:
            reasons.append("ambiguous_metric_value_evidence")
    excerpts: dict[str, tuple[int, str] | None] = {ticker: None for ticker in expected}
    for source in parse_evidence_sources(context):
        ticker = _source_ticker(source)
        if ticker not in excerpts or excerpts[ticker]:
            continue
        for line in source.text.splitlines():
            if (relevant(line) and re.search(r"\b(?:revenue|sales)\b", line, re.I)
                    and re.search(r"\b(?:include|includes|generate|generates)\b", line, re.I)
                    and not _NUMBER_RE.search(line) and "|" not in line):
                excerpts[ticker] = (source.number, _compact(line))
                break
    selected = [fact for fact in chosen.values() if fact]
    compatible = bool(applicable and len(selected) == len(expected)
                      and all(fact.has_explicit_share and fact.period for fact in selected)
                      and len({(fact.normalized_metric, fact.denominator, fact.period, fact.unit)
                               for fact in selected}) == 1)
    winners = tuple(fact.ticker for fact in selected
                    if compatible and fact.numeric_value == max(item.numeric_value for item in selected))
    reasons.append("compatible_share_measure" if compatible else "dependency_measure_mismatch")
    if any(fact and fact.period is None for fact in chosen.values()):
        reasons.append("unknown_period")
    return DependencySelectionV3(applicable, expected, facts, chosen, excerpts,
                                 compatible, winners, tuple(dict.fromkeys(reasons)))
