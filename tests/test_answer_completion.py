import pytest

from src.generation.answer_completion import (
    ANSWER_COMPLETION_FINGERPRINT,
    AnswerCompletionError,
    completion_metadata,
    correct_answer_once,
)
from src.generation.period_value_completeness import validate_grounded_answer


ENUMERATION_CONTEXT = """[Source 1] AAPL 10-K, Business
The Company markets smartphones, personal computers, tablets, wearables and accessories, and sells related services.
"""
ENUMERATION_QUESTION = "What are all the product categories Apple sells?"
REVENUE_CONTEXT = """[Source 1] Microsoft 10-K, Business
Server Products and Cloud Services
Server and cloud revenue is driven by licenses and Azure consumption.
LinkedIn
LinkedIn revenue is driven by monetized solutions.
Dynamics Products and Cloud Services
Dynamics revenue is driven by licensed users and applications.
Microsoft 365 Commercial Products and Cloud Services
Microsoft 365 Commercial revenue is driven by installed base growth.
Microsoft 365 Consumer Products and Cloud Services
Microsoft 365 Consumer revenue is driven by subscriptions.
Windows and Devices, including Windows OEM licensing and Devices.
Gaming, including Xbox hardware, content, subscriptions, and advertising.
Search and news advertising, including Bing and Copilot.
"""
REVENUE_QUESTION = "What are the main sources of revenue for Microsoft?"
COMPARISON_CONTEXT = """[Source 1] Microsoft 10-K, MD&A
Microsoft Cloud revenue was $168.9 billion in fiscal year 2025.
[Source 2] Apple 10-K, MD&A
Services net sales were $96,169 million in fiscal year 2025.
"""
COMPARISON_QUESTION = (
    "Which company depends more on cloud/subscription revenue, Microsoft or Apple?"
)
RISK_ENUMERATION_QUESTION = "What are all the major risk factors Microsoft discloses?"
RISK_ENUMERATION_CONTEXT = """[Source 1] Microsoft 10-K, Risk Factors
STRATEGIC AND COMPETITIVE RISKS
Trade:
Cybersecurity:
OPERATIONAL RISKS
We may experience supply or quality problems.
Threats to security can take a variety of forms.
The occurrence of regional epidemics or a global pandemic could adversely affect our business.
The long-term effects of climate change on the global economy are unclear.
Our global business exposes us to operational and economic risks.
"""


def test_enumeration_correction_is_one_bounded_provider_call() -> None:
    calls: list[str] = []

    result = correct_answer_once(
        ENUMERATION_QUESTION,
        ENUMERATION_CONTEXT,
        "Apple sells smartphones, personal computers, and tablets [Source 1].",
        lambda prompt: calls.append(prompt)
        or (
            "Apple sells smartphones, personal computers, tablets, wearables, "
            "accessories, and services [Source 1]."
        ),
    )

    assert len(calls) == 1
    assert "services" in calls[0].casefold()
    assert result.correction_attempted is True
    assert result.correction_accepted is True
    assert result.final.enumeration.passed is True
    assert result.answer.endswith("[Source 1].")


def test_complete_enumeration_is_a_noop() -> None:
    calls: list[str] = []
    answer = (
        "Apple sells smartphones, personal computers, tablets, wearables, "
        "accessories, and services [Source 1]."
    )

    result = correct_answer_once(
        ENUMERATION_QUESTION,
        ENUMERATION_CONTEXT,
        answer,
        lambda prompt: calls.append(prompt) or "unused",
    )

    assert result.answer == answer
    assert result.correction_attempted is False
    assert calls == []


def test_grounded_correction_gets_evidence_only_missing_label_repair() -> None:
    calls: list[str] = []

    result = correct_answer_once(
        ENUMERATION_QUESTION,
        ENUMERATION_CONTEXT,
        "- smartphones [Source 1]\n- personal computers [Source 1]\n"
        "- tablets [Source 1]\n- wearables [Source 1]\n"
        "- accessories [Source 1]\n- Cloud Services [Source 1]",
        lambda prompt: calls.append(prompt)
        or "- smartphones [Source 1]\n- personal computers [Source 1]\n"
        "- tablets [Source 1]\n- wearables [Source 1]\n"
        "- accessories [Source 1]\n- Cloud Services [Source 1]",
    )

    assert len(calls) == 1
    assert result.correction_accepted is True
    assert "- services [Source 1]" in result.answer
    assert result.final.enumeration.missing_items == ()


def test_enumeration_completion_compacts_unclassified_nested_bullets() -> None:
    answer = "\n".join(
        [
            "- smartphones [Source 1]",
            "- personal computers [Source 1]",
            "- tablets [Source 1]",
            "- Wearables [Source 1]",
            "- Accessories [Source 1]",
            "- Services [Source 1]",
            "- Advertising [Source 1]",
            "- Cloud Services [Source 1]",
            "- Payment Services [Source 1]",
        ]
    )
    result = correct_answer_once(
        ENUMERATION_QUESTION,
        ENUMERATION_CONTEXT,
        answer,
        lambda _prompt: "unused",
    )

    assert result.correction_attempted is False
    assert result.answer_compacted is True
    assert "- Services [Source 1]" in result.answer
    assert "- Cloud Services [Source 1]" not in result.answer
    assert result.final.enumeration.passed is True


def test_grouped_home_bullet_is_not_kept_as_a_separate_product_category() -> None:
    context = (
        "[Source 1] AAPL 10-K, Business\n"
        "The Company markets smartphones, personal computers, tablets, "
        "wearables and accessories, and sells related services.\n"
        "Wearables, Home and Accessories\n"
    )
    answer = "\n".join(
        [
            "- smartphones [Source 1]",
            "- personal computers [Source 1]",
            "- tablets [Source 1]",
            "- Wearables [Source 1]",
            "- Home [Source 1]",
            "- Accessories [Source 1]",
            "- Services [Source 1]",
        ]
    )
    result = correct_answer_once(
        ENUMERATION_QUESTION,
        context,
        answer,
        lambda _prompt: "unused",
    )

    assert result.correction_attempted is False
    assert result.answer_compacted is True
    assert "- Home [Source 1]" not in result.answer
    assert result.final.enumeration.passed is True


def test_revenue_subcategories_are_compacted_to_top_level_evidence_items() -> None:
    answer = "\n".join(
        [
            '- Azure cloud services – "Azure consumption" [Source 1]',
            '- Server products – "licenses" [Source 1]',
            '- LinkedIn [Source 1]',
            '- Dynamics products and cloud services [Source 1]',
            '- Microsoft 365 Commercial products [Source 1]',
            '- Microsoft 365 Consumer products [Source 1]',
            '- Gaming [Source 1]',
            '- Search and news advertising [Source 1]',
            '- Windows OEM licensing [Source 1]',
            '- Devices [Source 1]',
        ]
    )

    result = correct_answer_once(
        REVENUE_QUESTION,
        REVENUE_CONTEXT,
        answer,
        lambda _prompt: "unused",
    )

    assert result.correction_attempted is False
    assert result.answer_compacted is True
    assert result.final.enumeration.passed is True
    assert result.final.enumeration.overdetailed is False
    assert result.answer.count("\n") == 6
    assert "Azure cloud services" in result.answer
    assert "Server products" in result.answer
    assert "Microsoft 365 Consumer products" in result.answer
    assert "Devices" in result.answer


def test_deterministic_revenue_renderer_avoids_provider_rewrite() -> None:
    result = correct_answer_once(
        REVENUE_QUESTION,
        REVENUE_CONTEXT,
        "- Azure [Source 1]",
        lambda _prompt: (_ for _ in ()).throw(
            AssertionError("deterministic revenue renderer should run first")
        ),
        validate_answer=lambda answer: validate_grounded_answer(
            answer, REVENUE_CONTEXT
        ),
        deterministic_revenue_renderer=True,
    )

    assert result.answer_rendered_deterministically is True
    assert result.correction_accepted is True
    assert result.final.enumeration.passed is True
    assert result.answer.count("\n") == 5


def test_deterministic_comparative_renderer_qualifies_dependency_claim() -> None:
    result = correct_answer_once(
        COMPARISON_QUESTION,
        COMPARISON_CONTEXT,
        "Microsoft depends more on cloud/subscription revenue. [Source 1]",
        lambda _prompt: (_ for _ in ()).throw(
            AssertionError("comparative renderer should run before provider rewrite")
        ),
        validate_answer=lambda answer: validate_grounded_answer(
            answer, COMPARISON_CONTEXT
        ),
        deterministic_comparative_renderer=True,
    )

    assert result.answer_rendered_deterministically is True
    assert result.correction_accepted is True
    assert "do not establish which company depends more" in result.answer
    assert result.final.answerability.status == "qualified"


def test_risk_subcategories_are_compacted_without_provider_call() -> None:
    calls: list[str] = []
    answer = "\n".join(
        [
            "- Strategic and Competitive Risks [Source 1]",
            "- Competition in the technology sector [Source 1]",
            "- Trade [Source 1]",
            "- Cybersecurity [Source 1]",
            "- Operational Risks [Source 1]",
            "- Supply or quality problems [Source 1]",
            "- Threats to security [Source 1]",
            "- Occurrence of regional epidemics or a global pandemic [Source 1]",
            "- Long-term effects of climate change [Source 1]",
            "- Global business operational and economic risks [Source 1]",
        ]
    )

    result = correct_answer_once(
        RISK_ENUMERATION_QUESTION,
        RISK_ENUMERATION_CONTEXT,
        answer,
        lambda prompt: calls.append(prompt) or "unused",
    )

    assert calls == []
    assert result.correction_attempted is False
    assert result.answer_compacted is True
    assert result.final.enumeration.overdetailed is False
    assert result.final.enumeration.passed is True
    assert "Supply or quality problems" not in result.answer


def test_risk_prose_is_grouped_after_canonical_categories() -> None:
    calls: list[str] = []
    answer = "\n".join(
        [
            "- Strategic and Competitive Risks [Source 1]",
            "- Trade [Source 1]",
            "- Cybersecurity [Source 1]",
            "- Operational Risks [Source 1]",
            "- Threats to security [Source 1]",
            "- Occurrence of regional epidemics or a global pandemic [Source 1]",
            "- Long-term effects of climate change [Source 1]",
            "- Global business operational and economic risks [Source 1]",
        ]
    )

    result = correct_answer_once(
        RISK_ENUMERATION_QUESTION,
        RISK_ENUMERATION_CONTEXT,
        answer,
        lambda prompt: calls.append(prompt) or "unused",
    )

    assert calls == []
    assert result.answer_compacted is True
    assert result.answer.count("Additional cross-cutting risks") == 1
    assert result.answer.count("Threats to security") >= 1
    assert result.answer.count("global pandemic") >= 1
    assert result.final.enumeration.missing_items == ()


def test_risk_compaction_drops_unproven_provider_descriptors() -> None:
    answer = "\n".join(
        [
            "- Strategic and Competitive Risks – intense competition [Source 1]",
            "- Trade – trade restrictions [Source 1]",
            "- Cybersecurity – cyber threats [Source 1]",
            "- Operational Risks – outages and supply problems [Source 1]",
            "- Threats to security – attacks [Source 1]",
            "- Occurrence of regional epidemics or a global pandemic – outbreaks [Source 1]",
            "- Long-term effects of climate change – costs [Source 1]",
            "- Global business operational and economic risks – exposure [Source 1]",
        ]
    )

    result = correct_answer_once(
        RISK_ENUMERATION_QUESTION,
        RISK_ENUMERATION_CONTEXT,
        answer,
        lambda _prompt: "unused",
    )

    assert result.answer_compacted is True
    assert "intense competition" not in result.answer
    assert "Strategic And Competitive Risks" in result.answer
    assert "Additional cross-cutting risks" in result.answer
    assert result.final.enumeration.passed is True


def test_unsupported_numeric_claim_gets_one_grounded_correction_outside_period_questions() -> None:
    calls: list[str] = []
    draft = (
        "Microsoft reported $168.9 billion [Source 1], while Apple reported "
        "$96,169 million (about $96.2 billion) [Source 2]."
    )
    corrected = (
        "Microsoft reported $168.9 billion [Source 1], while Apple reported "
        "$96,169 million [Source 2]. Therefore Microsoft depends more."
    )

    result = correct_answer_once(
        COMPARISON_QUESTION,
        COMPARISON_CONTEXT,
        draft,
        lambda prompt: calls.append(prompt) or corrected,
    )

    assert len(calls) == 1
    assert "$96.2" in calls[0]
    assert result.correction_attempted is True
    assert result.correction_accepted is True
    assert result.final.grounding_passed is True
    assert "$96.2" not in result.answer


def test_prose_numeric_stability_gets_one_grounded_correction() -> None:
    context = """[Source 1] MSFT 10-K, MD&A
Server products and cloud services revenue increased 23% driven by Azure and other cloud services revenue growth of 34%.
Microsoft Cloud revenue increased 23% to $168.9 billion.
"""
    calls: list[str] = []
    corrected = (
        "Azure and other cloud services revenue growth was 34%, while "
        "server products and cloud services revenue increased 23%. Microsoft "
        "Cloud revenue increased 23% to $168.9 billion [Source 1]."
    )

    result = correct_answer_once(
        "How does Microsoft describe its Azure and cloud services growth?",
        context,
        "Azure and other cloud services revenue growth was 34% and server "
        "products and cloud services revenue increased 23% [Source 1].",
        lambda prompt: calls.append(prompt) or corrected,
    )

    assert len(calls) == 1
    assert "$168.9 billion" in calls[0]
    assert result.correction_accepted is True
    assert result.initial.stability.missing_facts
    assert result.final.stability.passed is True


def test_prose_numeric_stability_metadata_is_serialized() -> None:
    context = """[Source 1] MSFT 10-K, MD&A
Server products and cloud services revenue increased 23% driven by Azure and other cloud services revenue growth of 34%.
Microsoft Cloud revenue increased 23% to $168.9 billion.
"""
    result = correct_answer_once(
        "How does Microsoft describe its Azure and cloud services growth?",
        context,
        "Azure growth was 34% and server products and cloud services revenue "
        "increased 23%; Microsoft Cloud revenue increased 23% to $168.9 "
        "billion [Source 1].",
        lambda _prompt: "unused",
    )

    metadata = completion_metadata(result)
    assert metadata["stability_applicable"] is True
    assert metadata["initial_stability_passed"] is True
    assert metadata["final_stability_passed"] is True
    assert metadata["stability_missing_facts"] == []


def test_correction_provider_failure_is_not_hidden_or_retried() -> None:
    calls: list[str] = []

    def generate(_prompt: str) -> str:
        calls.append("call")
        raise RuntimeError("quota exhausted")

    with pytest.raises(AnswerCompletionError, match="quota exhausted"):
        correct_answer_once(
            ENUMERATION_QUESTION,
            ENUMERATION_CONTEXT,
            "Apple sells smartphones [Source 1].",
            generate,
        )

    assert calls == ["call"]


def test_completion_metadata_preserves_scoped_enum_fields() -> None:
    answer = (
        "Apple sells smartphones, personal computers, tablets, wearables, "
        "accessories, and services [Source 1]."
    )
    result = correct_answer_once(
        ENUMERATION_QUESTION,
        ENUMERATION_CONTEXT,
        answer,
        lambda _prompt: "unused",
    )

    metadata = completion_metadata(result)
    assert metadata["enumeration_applicable"] is True
    assert metadata["period_value_applicable"] is False
    assert metadata["final_passed"] is True
    assert metadata["missing_items"] == []


def test_fingerprint_is_stable_and_nonempty() -> None:
    assert ANSWER_COMPLETION_FINGERPRINT.startswith("sha256:")
    assert len(ANSWER_COMPLETION_FINGERPRINT) == 71
