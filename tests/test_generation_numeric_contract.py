from src.evaluation.generation_checkpoint import (
    DEFAULT_GENERATION_PROMPT_TEMPLATE,
)
from src.generation.generator import SYSTEM_PROMPT, _build_user_message
from src.generation.prompt_contracts import ANSWER_FOCUS_CONTRACT
from src.generation.query_decomposer import SYNTHESIS_SYSTEM_PROMPT


def _assert_answer_focus_contract(text: str) -> None:
    normalized = " ".join(text.split()).casefold()

    assert "exact dimension asked" in normalized
    assert "products, services, revenue sources, or business drivers" in normalized
    assert "supporting evidence" in normalized
    assert "comparison of reporting formats" in normalized


def test_answer_focus_contract_is_shared_by_all_generation_paths() -> None:
    assert "{answer_focus_contract}" not in SYSTEM_PROMPT
    _assert_answer_focus_contract(_build_user_message("Compare their approach", []))
    assert "{answer_focus_contract}" in DEFAULT_GENERATION_PROMPT_TEMPLATE
    assert ANSWER_FOCUS_CONTRACT not in SYNTHESIS_SYSTEM_PROMPT


def test_answer_focus_contract_is_scoped_to_approach_questions() -> None:
    ordinary_message = _build_user_message(
        "What are all the product categories Apple sells?", []
    )
    assert ANSWER_FOCUS_CONTRACT not in ordinary_message

    ordinary_prompt = DEFAULT_GENERATION_PROMPT_TEMPLATE.format(
        context_blocks="", question="What are all the product categories Apple sells?",
        answer_focus_contract="",
    )
    assert ANSWER_FOCUS_CONTRACT not in ordinary_prompt

    approach_prompt = DEFAULT_GENERATION_PROMPT_TEMPLATE.format(
        context_blocks="", question="How do their approaches differ?",
        answer_focus_contract=ANSWER_FOCUS_CONTRACT,
    )
    _assert_answer_focus_contract(approach_prompt)


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
    assert "explicitly asks for a numeric trend, numeric comparison, or growth" in normalized


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
