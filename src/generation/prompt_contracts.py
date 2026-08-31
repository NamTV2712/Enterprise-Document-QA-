"""Shared generation instructions used by every answer-producing path."""

import re

ANSWER_FOCUS_CONTRACT = (
    "Answer the exact dimension asked in the question before adding supporting "
    "detail. For a comparison about each company's approach, first compare the "
    "evidence-supported products, services, revenue sources, or business drivers "
    "that answer that approach question. Use reported figures only as supporting "
    "evidence; do not replace the requested qualitative comparison with a table "
    "of figures or a comparison of reporting formats. Keep the answer concise and "
    "omit evidence that does not help answer the requested comparison dimension."
)

_APPROACH_QUESTION_RE = re.compile(r"\bapproach(?:es)?\b", re.IGNORECASE)


def answer_focus_contract_for_question(question: str) -> str:
    """Return the qualitative approach contract only for approach questions.

    The contract was introduced to correct an approach-comparison failure, so
    applying it to every question can distort unrelated fact and enumeration
    answers. Keep the scope deliberately narrow until a broader intent router
    has evidence for additional question families.
    """
    if _APPROACH_QUESTION_RE.search(question):
        return ANSWER_FOCUS_CONTRACT
    return ""

NUMERIC_PAIR_CONTRACT = (
    "For every question that explicitly asks for a numeric trend, numeric "
    "comparison, or growth, inspect all provided "
    "sources for explicit period-and-value pairs for each compared entity. "
    "When those pairs exist, the answer MUST first list every underlying "
    "value relevant to the comparison together with its period, exactly as "
    "printed, before any trend summary. A percentage-only, qualitative, "
    "rounded, abbreviated, approximate, or range-based answer is incomplete "
    "when exact underlying values are available. Never omit those values or "
    "replace them with a percentage. Never replace filing values with rounded, "
    "abbreviated, or recalculated values. Do not calculate a difference, ratio, "
    "percentage, average, approximation, range, or unit conversion, even when "
    "the underlying values are cited. Do not introduce numeric shorthand such "
    "as '$100 billion range'. Report only numeric values explicitly present in "
    "the cited evidence. Before finalizing, check that every numeric comparison "
    "claim is a verbatim evidence value and that every available period-value "
    "pair was listed. Never answer with only a percentage when those underlying "
    "values are present."
)

NUMERIC_PAIR_REMINDER = (
    "Numeric checklist: for a numeric trend, numeric comparison, or growth "
    "question, first quote every "
    "relevant underlying value with its period when the context provides "
    "multiple period-and-value pairs. Do not round, abbreviate, or omit them, "
    "replace them with only a percentage, or summarize them as a numeric range. "
    "Do not calculate a difference, ratio, percentage, average, approximation, "
    "range, or unit conversion. Report only values explicitly present in the "
    "cited evidence, and verify every numeric claim before finalizing."
)
