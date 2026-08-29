"""Shared generation instructions used by every answer-producing path."""

NUMERIC_PAIR_CONTRACT = (
    "For every trend, comparison, or growth question, inspect all provided "
    "sources for explicit period-and-value pairs for each compared entity. "
    "When those pairs exist, quote every underlying value relevant to the "
    "comparison together with its period before summarizing the trend. Never "
    "replace filing values with rounded, abbreviated, or recalculated values. "
    "A percentage-only or qualitative answer is incomplete when exact "
    "underlying values are available in the context. Never answer with only "
    "a percentage when those underlying values are present."
)

NUMERIC_PAIR_REMINDER = (
    "For a trend, growth, or comparison, quote every relevant underlying "
    "value with its period when the context provides multiple period-and-value "
    "pairs. Do not round, abbreviate, or replace those filing values with "
    "only a percentage."
)
