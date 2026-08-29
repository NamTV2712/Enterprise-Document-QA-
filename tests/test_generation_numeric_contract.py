from src.evaluation.generation_checkpoint import (
    DEFAULT_GENERATION_PROMPT_TEMPLATE,
)
from src.generation.generator import SYSTEM_PROMPT, _build_user_message


def test_system_prompt_requires_all_exact_period_value_pairs() -> None:
    normalized = " ".join(SYSTEM_PROMPT.split()).casefold()

    assert "inspect all provided sources" in normalized
    assert "every underlying value relevant to the comparison" in normalized
    assert "together with its period" in normalized
    assert "rounded, abbreviated, or recalculated" in normalized
    assert "percentage-only" in normalized


def test_production_user_message_repeats_numeric_pair_contract_near_question() -> None:
    message = _build_user_message("How did it grow?", [])
    normalized = " ".join(message.split()).casefold()

    assert "every relevant underlying value" in normalized
    assert "multiple period-and-value pairs" in normalized
    assert "do not round, abbreviate" in normalized
    assert "only a percentage" in normalized


def test_phase2_template_has_the_same_numeric_pair_contract() -> None:
    normalized = " ".join(DEFAULT_GENERATION_PROMPT_TEMPLATE.split()).casefold()

    assert "inspect all excerpts" in normalized
    assert "every relevant underlying period-and-value pair" in normalized
    assert "do not round, abbreviate, recalculate" in normalized
    assert "only a percentage" in normalized
