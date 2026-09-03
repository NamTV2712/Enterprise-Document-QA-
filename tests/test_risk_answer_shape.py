from src.generation.risk_answer_shape import (
    assess_risk_answer_shape,
    render_deterministic_risk_answer,
)
from src.generation.answer_completion import correct_answer_once
from src.generation.period_value_completeness import validate_grounded_answer


QUESTION = "What are all the major risk factors Microsoft discloses?"
BROAD_QUESTION = "What are all the risks Microsoft discloses?"
CONTEXT = """[Source 1] MSFT 10-K, Risk Factors
STRATEGIC AND COMPETITIVE RISKS
Competition can adversely affect our products and results.
OPERATIONAL RISKS
Our infrastructure may experience outages and disruptions.
Threats to security can take a variety of forms.
"""


def test_renderer_is_byte_stable_and_keeps_major_risk_scope() -> None:
    first = render_deterministic_risk_answer(QUESTION, CONTEXT)
    second = render_deterministic_risk_answer(QUESTION, CONTEXT)

    assert first == second
    assert first is not None
    assert first.splitlines() == [
        "- Strategic And Competitive Risks — Competition can adversely affect our products and results [Source 1]",
        "- Operational Risks — Our infrastructure may experience outages and disruptions [Source 1]",
    ]
    audit = assess_risk_answer_shape(QUESTION, CONTEXT, first)
    assert audit.passed is True
    assert audit.canonical_count == 2
    assert audit.supporting_count == 0


def test_broad_risk_scope_preserves_supporting_section() -> None:
    answer = render_deterministic_risk_answer(BROAD_QUESTION, CONTEXT)

    assert answer is not None
    assert "Additional cross-cutting risks:" in answer
    audit = assess_risk_answer_shape(BROAD_QUESTION, CONTEXT, answer)
    assert audit.passed is True
    assert audit.canonical_count == 2
    assert audit.supporting_count == 1


def test_shape_oracle_rejects_supporting_risk_as_a_peer() -> None:
    answer = (
        "- Strategic And Competitive Risks — Competition affects results [Source 1]\n"
        "- Operational Risks — Infrastructure may fail [Source 1]\n"
        "- Threats to security — Security threats [Source 1]"
    )

    audit = assess_risk_answer_shape(QUESTION, CONTEXT, answer)

    assert audit.passed is False
    assert "unsupported_peer" in audit.reason_codes


def test_shape_oracle_rejects_duplicate_and_unsupported_peer() -> None:
    answer = (
        "- Strategic And Competitive Risks — Competition affects results [Source 1]\n"
        "- Strategic And Competitive Risks — Competition affects results [Source 1]\n"
        "- Operational Risks — Infrastructure may fail [Source 1]\n"
        "- Unrelated risk [Source 1]"
    )

    audit = assess_risk_answer_shape(QUESTION, CONTEXT, answer)

    assert audit.passed is False
    assert "duplicate_item" in audit.reason_codes
    assert "unsupported_peer" in audit.reason_codes


def test_candidate_renderer_does_not_spend_a_correction_call() -> None:
    result = correct_answer_once(
        QUESTION,
        CONTEXT,
        "- Strategic And Competitive Risks [Source 1]",
        lambda _prompt: (_ for _ in ()).throw(
            AssertionError("deterministic renderer should run first")
        ),
        validate_answer=lambda answer: validate_grounded_answer(answer, CONTEXT),
        deterministic_risk_renderer=True,
    )

    assert result.answer_rendered_deterministically is True
    assert result.correction_accepted is True
    assert result.final.enumeration.passed is True
