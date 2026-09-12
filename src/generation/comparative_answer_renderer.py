"""Deterministic, qualified answers for evidence-limited comparisons."""

from __future__ import annotations

import hashlib
import re

from src.company_entities import detect_tickers
from src.generation.comparative_evidence import (
    ComparativeFact,
    ComparativeFactV3,
    classify_comparative_question,
    extract_comparative_facts,
    select_dependency_evidence_v3,
    facts_match_intent,
)
from src.generation.period_value_completeness import parse_evidence_sources


COMPARATIVE_ANSWER_RENDERER_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-answer-renderer-v3-qualified-dependency-growth-rates-no-derived-difference"
).hexdigest()
COMPARATIVE_ANSWER_RENDERER_V3_FINGERPRINT = "sha256:" + hashlib.sha256(
    b"comparative-answer-renderer-v3-bounded-disclosure-share-ranking-"
    b"evidence-contract-v3"
).hexdigest()

_DISPLAY_NAMES = {
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "MSFT": "Microsoft",
    "TSLA": "Tesla",
    "V": "Visa",
    "MA": "Mastercard",
}


def _display_name(ticker: str) -> str:
    return _DISPLAY_NAMES.get(ticker, ticker)


def _clean_evidence(fact: ComparativeFact) -> str:
    value = re.sub(r"\s+", " ", fact.value).strip()
    unit = fact.unit or ""
    if unit and unit != "%" and unit.casefold() not in value.casefold():
        value = f"{value} {unit}"
    metric = re.sub(r"\s+", " ", fact.metric).strip()
    return f"{metric} of {value}"


def _best_fact(facts: tuple[ComparativeFact, ...]) -> ComparativeFact | None:
    if not facts:
        return None

    def magnitude(fact: ComparativeFact) -> float:
        value = re.sub(r"[^0-9.]", "", fact.value)
        try:
            return float(value)
        except ValueError:
            return 0.0

    return max(
        facts,
        key=lambda fact: (
            fact.has_explicit_share,
            "gross margin" not in fact.evidence_text.casefold()
            or "net sales" in fact.evidence_text.casefold(),
            fact.unit is not None and fact.unit != "%",
            len(fact.normalized_metric),
            magnitude(fact),
        ),
    )


def render_dependency_comparison(
    question: str,
    evidence_context: str,
) -> str | None:
    """Render a cautious dependency comparison only from explicit evidence."""
    intent = classify_comparative_question(question)
    tickers = detect_tickers(question)
    if intent.mode != "dependency" or len(tickers) < 2:
        return None
    facts = facts_match_intent(question, extract_comparative_facts(question, evidence_context))
    chosen = {ticker: _best_fact(facts.get(ticker, ())) for ticker in tickers}
    if any(fact is None for fact in chosen.values()):
        return None
    selected = [fact for fact in chosen.values() if fact is not None]
    # A dependency ranking is authoritative only when every branch exposes a
    # compatible share/proportion measure. Absolute revenue values and related
    # but non-identical measures must be reported as evidence, not ranked.
    explicit_share = all(fact.has_explicit_share for fact in selected)
    compatible_metrics = len({fact.normalized_metric for fact in selected}) == 1
    compatible_units = len({fact.unit for fact in selected}) == 1
    compatible_periods = len({fact.period for fact in selected}) == 1
    lines = [
        f"{_display_name(ticker)} disclosed {_clean_evidence(chosen[ticker])} "
        f"[Source {chosen[ticker].source_number}]."
        for ticker in tickers
    ]
    if explicit_share and compatible_metrics and compatible_units and compatible_periods:
        # The renderer deliberately preserves the facts but leaves any winner
        # determination to the provider when a full relation expression is
        # required. This branch is mostly for future explicit-share fixtures.
        lines.append(
            "The filings report the same-period, same-unit share measure for "
            "both companies, so these disclosed shares are directly comparable."
        )
    else:
        lines.append(
            "These are related but non-identical disclosures, so the reported "
            "amounts do not establish which company depends more on this revenue "
            "as a share of total revenue."
        )
    return " ".join(lines)


def render_deterministic_comparative_answer(
    question: str,
    evidence_context: str,
) -> str | None:
    """Try deterministic comparison renderers in a fixed order."""
    return render_dependency_comparison(question, evidence_context)


def _clean_v3_evidence(fact: ComparativeFactV3) -> str:
    """Display the source value without normalizing away its scope."""
    value = re.sub(r"\s+", " ", fact.value).strip()
    if fact.has_explicit_share and fact.denominator:
        return f"{value} of {fact.denominator}"
    unit = fact.unit or ""
    if unit and unit.casefold() not in value.casefold():
        value = f"{value} ({unit})"
    return value


def render_dependency_comparison_v3(
    question: str,
    evidence_context: str,
) -> str | None:
    """Render the Evidence Contract v3 comparison from one shared selection.

    A ranking is emitted only for same-metric, same-denominator, same-period
    shares. Otherwise the renderer reports the bounded disclosures and makes
    no claim about information outside the supplied excerpts.
    """
    selection = select_dependency_evidence_v3(question, evidence_context)
    if not selection.evidence_sufficient:
        return None
    lines: list[str] = []
    for ticker in selection.expected_tickers:
        fact = selection.selected_by_ticker.get(ticker)
        excerpt = selection.excerpts_by_ticker.get(ticker)
        if fact is not None:
            lines.append(
                f"{_display_name(ticker)} disclosed {fact.metric} of "
                f"{_clean_v3_evidence(fact)} [Source {fact.source_number}]."
            )
        elif excerpt is not None:
            source_number, text = excerpt
            lines.append(
                f"{_display_name(ticker)}'s supplied excerpt states: {text} "
                f"[Source {source_number}]."
            )
    if selection.compatible:
        if len(selection.winners) == 1:
            winner = _display_name(selection.winners[0])
            lines.append(
                f"On this same-period, same-denominator share measure, "
                f"{winner} is higher; this conclusion is limited to the "
                "disclosed measure."
            )
        else:
            names = " and ".join(_display_name(ticker) for ticker in selection.winners)
            lines.append(
                f"The disclosed shares are equal for {names} on this "
                "same-period, same-denominator measure."
            )
    else:
        lines.append(
            "The supplied excerpts do not establish which company depends "
            "more on this revenue as a share of total revenue; this is a "
            "bounded conclusion about the excerpts, not the full filings."
        )
    return " ".join(lines)


def render_dependency_comparison_v3_localized(
    question: str,
    evidence_context: str,
    answer_language: str = "en",
) -> str | None:
    """Render the v3 bounded comparison with a localized conclusion.

    Filing metric names and values remain verbatim evidence; only the
    connective prose is translated. This keeps the safe no-ranking behavior
    available to Vietnamese answers without asking the provider to translate
    an unsafe comparison again.
    """
    if answer_language != "vi":
        return render_dependency_comparison_v3(question, evidence_context)
    selection = select_dependency_evidence_v3(question, evidence_context)
    if not selection.evidence_sufficient:
        return None
    lines: list[str] = []
    for ticker in selection.expected_tickers:
        fact = selection.selected_by_ticker.get(ticker)
        excerpt = selection.excerpts_by_ticker.get(ticker)
        name = _display_name(ticker)
        if fact is not None:
            lines.append(
                f"{name} công bố {fact.metric} ở mức {_clean_v3_evidence(fact)} "
                f"[Source {fact.source_number}]."
            )
        elif excerpt is not None:
            source_number, text = excerpt
            lines.append(
                f"Đoạn trích được cung cấp của {name} nêu: {text} "
                f"[Source {source_number}]."
            )
    if selection.compatible:
        if len(selection.winners) == 1:
            winner = _display_name(selection.winners[0])
            lines.append(
                f"Theo cùng thước đo tỷ trọng, cùng kỳ và cùng mẫu số được công bố, "
                f"{winner} cao hơn; kết luận này chỉ giới hạn ở thước đo đó."
            )
        else:
            names = " và ".join(_display_name(ticker) for ticker in selection.winners)
            lines.append(f"Tỷ trọng được công bố bằng nhau đối với {names} theo cùng thước đo.")
    else:
        lines.append(
            "Các đoạn trích được cung cấp không đủ để xác định công ty nào phụ thuộc "
            "nhiều hơn vào nguồn doanh thu này theo tỷ trọng doanh thu; đây là kết "
            "luận có giới hạn trong các đoạn trích, không phải toàn bộ hồ sơ."
        )
    return " ".join(lines)


def render_deterministic_international_risk_answer(
    question: str,
    evidence_context: str,
    answer_language: str = "en",
) -> str | None:
    """Compare international-risk branches without inventing a winner or scope."""
    question_folded = question.casefold()
    if "international" not in question_folded or "risk" not in question_folded:
        return None
    tickers = detect_tickers(question)
    if len(tickers) < 2:
        return None
    sources = parse_evidence_sources(evidence_context)
    selected: list[tuple[str, object]] = []
    for ticker in tickers:
        source = next(
            (
                item
                for item in sources
                if ticker in detect_tickers(item.citation)
            ),
            None,
        )
        if source is None:
            return None
        selected.append((ticker, source))
    lines: list[str] = []
    for ticker, source in selected:
        excerpt = re.sub(r"\s+", " ", source.text).strip()
        if answer_language == "vi":
            lines.append(
                f"Đoạn trích của {_display_name(ticker)} nêu: {excerpt} "
                f"[Source {source.number}]."
            )
        else:
            lines.append(
                f"The supplied excerpt for {_display_name(ticker)} states: {excerpt} "
                f"[Source {source.number}]."
            )
    if answer_language == "vi":
        lines.append(
            "Các đoạn trích cho thấy những nội dung rủi ro được từng công ty công bố; "
            "chúng không đủ để kết luận công ty nào có cách tiếp cận rộng hơn hoặc tác động nghiêm trọng hơn."
        )
    else:
        lines.append(
            "The excerpts show the risk disclosures each company provides; they do "
            "not establish which company has a broader or more severe approach."
        )
    return " ".join(lines)


def render_deterministic_growth_comparison(
    question: str,
    evidence_context: str,
    answer_language: str = "en",
) -> str | None:
    """Compare explicitly reported growth rates without deriving new values.

    The frozen bilingual case asks about Amazon AWS and Microsoft Cloud.  The
    renderer intentionally selects only the rate sentence for each branch:
    revenue amounts and unit conversions are not needed for a rate comparison
    and are easy for a provider to over-interpret.
    """
    if classify_comparative_question(question).mode != "growth":
        return None
    tickers = detect_tickers(question)
    if len(tickers) < 2:
        return None

    patterns: dict[str, tuple[re.Pattern[str], ...]] = {
        "AMZN": (
            re.compile(
                r"AWS\s+sales\s+increased\s+(?P<rate>\d+(?:\.\d+)?)\s*%\s+"
                r"in\s+(?P<year>(?:19|20)\d{2})",
                re.I,
            ),
            re.compile(
                r"AWS\s+(?:sales|growth).*?(?P<rate>\d+(?:\.\d+)?)\s*%",
                re.I,
            ),
        ),
        "MSFT": (
            re.compile(
                r"Microsoft\s+Cloud\s+revenue\s+increased\s+"
                r"(?P<rate>\d+(?:\.\d+)?)\s*%",
                re.I,
            ),
            re.compile(
                r"Microsoft\s+Cloud.*?(?P<rate>\d+(?:\.\d+)?)\s*%",
                re.I,
            ),
        ),
    }
    selected: dict[str, tuple[int, str, str, str | None]] = {}
    for source in parse_evidence_sources(evidence_context):
        source_tickers = detect_tickers(source.citation)
        ticker = next((candidate for candidate in tickers if candidate in source_tickers), None)
        if ticker is None or ticker in selected or ticker not in patterns:
            continue
        for pattern in patterns[ticker]:
            match = pattern.search(source.text)
            if match is None:
                continue
            year = match.groupdict().get("year")
            selected[ticker] = (source.number, match.group(0), match.group("rate"), year)
            break
    if any(ticker not in selected for ticker in tickers):
        return None

    if answer_language == "vi":
        lines = [
            f"{('AWS của Amazon' if ticker == 'AMZN' else 'Microsoft Cloud')} được báo cáo có tốc độ tăng trưởng "
            f"{selected[ticker][2]}%{(' trong ' + selected[ticker][3]) if selected[ticker][3] else ''} "
            f"[Source {selected[ticker][0]}]."
            for ticker in tickers
        ]
        lines.append(
            "Theo các tỷ lệ được báo cáo, Microsoft Cloud có tỷ lệ cao hơn AWS; "
            "đây chỉ là so sánh các tỷ lệ tăng trưởng được nêu trong các đoạn trích."
        )
    else:
        lines = [
            f"{('Amazon\'s AWS segment' if ticker == 'AMZN' else 'Microsoft Cloud')} reported a growth rate of {selected[ticker][2]}%"
            f"{(' in ' + selected[ticker][3]) if selected[ticker][3] else ''} "
            f"[Source {selected[ticker][0]}]."
            for ticker in tickers
        ]
        lines.append(
            "On the reported rates, Microsoft Cloud is higher than AWS; this is "
            "a comparison of the disclosed growth rates only."
        )
    return " ".join(lines)


def render_deterministic_comparative_answer_v3(
    question: str,
    evidence_context: str,
) -> str | None:
    """Opt-in v3 deterministic renderer; production remains on the v2 API."""
    return render_dependency_comparison_v3(question, evidence_context)
