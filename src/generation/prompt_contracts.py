"""Shared generation instructions used by every answer-producing path."""

NUMERIC_PAIR_CONTRACT = (
    "For every trend, comparison, or growth question, inspect all provided "
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
    "Numeric checklist: for a trend, growth, or comparison, first quote every "
    "relevant underlying value with its period when the context provides "
    "multiple period-and-value pairs. Do not round, abbreviate, or omit them, "
    "replace them with only a percentage, or summarize them as a numeric range. "
    "Do not calculate a difference, ratio, percentage, average, approximation, "
    "range, or unit conversion. Report only values explicitly present in the "
    "cited evidence, and verify every numeric claim before finalizing."
)
