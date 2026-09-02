import pytest

from src.generation.answer_completion import (
    ANSWER_COMPLETION_FINGERPRINT,
    AnswerCompletionError,
    completion_metadata,
    correct_answer_once,
)


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
