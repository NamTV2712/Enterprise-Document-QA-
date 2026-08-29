from src.evaluation.generation_checkpoint import (
    DEFAULT_GENERATION_PROMPT_TEMPLATE,
)
from src.generation.generator import SYSTEM_PROMPT, _build_user_message
from src.generation.query_decomposer import SYNTHESIS_SYSTEM_PROMPT


def test_system_prompt_requires_all_exact_period_value_pairs() -> None:
    normalized = " ".join(SYSTEM_PROMPT.split()).casefold()

    assert "inspect all provided sources" in normalized
    assert "every underlying value relevant to the comparison" in normalized
    assert "together with its period" in normalized
    assert "rounded, abbreviated, or recalculated" in normalized
    assert "do not calculate a difference" in normalized
    assert "only numeric values explicitly present" in normalized
    assert "percentage-only" in normalized
    assert "must first list every underlying" in normalized
    assert "numeric shorthand" in normalized


def test_production_user_message_repeats_numeric_pair_contract_near_question() -> None:
    message = _build_user_message("How did it grow?", [])
    normalized = " ".join(message.split()).casefold()

    assert "every relevant underlying value" in normalized
    assert "multiple period-and-value pairs" in normalized
    assert "do not round, abbreviate" in normalized
    assert "calculate" in normalized
    assert "unit conversion" in normalized
    assert "only a percentage" in normalized
    assert "numeric range" in normalized


def test_phase2_template_has_the_same_numeric_pair_contract() -> None:
    normalized = " ".join(DEFAULT_GENERATION_PROMPT_TEMPLATE.split()).casefold()

    assert "inspect all provided sources" in normalized
    assert "every underlying value relevant to the comparison" in normalized
    assert "rounded, abbreviated, or recalculated" in normalized
    assert "do not calculate a difference" in normalized
    assert "only numeric values explicitly present" in normalized
    assert "only a percentage" in normalized
    assert "must first list every underlying" in normalized


def test_comparative_synthesis_has_the_same_numeric_pair_contract() -> None:
    normalized = " ".join(SYNTHESIS_SYSTEM_PROMPT.split()).casefold()

    assert "inspect all provided sources" in normalized
    assert "every underlying value relevant to the comparison" in normalized
    assert "rounded, abbreviated, or recalculated" in normalized
    assert "do not calculate a difference" in normalized
    assert "only numeric values explicitly present" in normalized
    assert "percentage-only" in normalized
    assert "must first list every underlying" in normalized
