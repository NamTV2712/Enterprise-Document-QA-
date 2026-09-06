from src.generation.enumeration_completeness import (
    ENUMERATION_COMPLETENESS_FINGERPRINT,
    assess_enumeration_completeness,
    enumeration_kind,
    extract_evidence_items,
)
from src.generation.period_value_completeness import parse_evidence_sources
from src.evaluation.revenue_intent_contract import audit_revenue_intent_scope

from tests.conftest import skip_without_data


APPLE_CONTEXT = """[Source 1] AAPL 10-K, Business
The Company designs and markets smartphones, personal computers, tablets, wearables and accessories, and sells a variety of related services.
Wearables, Home and Accessories
"""

AMAZON_CONTEXT = """[Source 1] AMZN 10-K, Business
We have organized our operations into three segments: North America, International, and Amazon Web Services (\"AWS\").
"""

MICROSOFT_REVENUE_CONTEXT = """[Source 1] Microsoft 10-K, Business
Server Products and Cloud Services
Azure and server revenue.
[Source 2] Microsoft 10-K, Business
LinkedIn
Dynamics Products and Cloud Services
Microsoft 365 Commercial Products and Cloud Services
[Source 3] Microsoft 10-K, Business
Gaming, including Xbox hardware,
Search and news advertising, including Bing and Copilot,
Windows and Devices, including Windows OEM licensing and Devices.
"""


def test_classifier_is_scoped_to_exhaustive_enumeration_intent() -> None:
    assert enumeration_kind("What are all the product categories Apple sells?") == "product"
    assert enumeration_kind("What is Apple's main product?") is None
    assert enumeration_kind("Summarize Apple's key products.") is None
    assert enumeration_kind("What are Amazon's business segments?") is None


def test_apple_product_coverage_uses_grouped_filing_category() -> None:
    result = assess_enumeration_completeness(
        "What are all the product categories Apple sells?",
        APPLE_CONTEXT,
        "Apple sells smartphones, personal computers, tablets, wearables/accessories, and services [Source 1].",
    )

    assert result.applicable is True
    assert result.passed is True
    assert {item.label for item in result.missing_items} == set()
    assert any(
        item.label == "wearables"
        and "Wearables, Home and Accessories" in item.aliases
        for item in result.evidence_items
    )
    assert all(
        alias.casefold() != "home"
        for item in result.evidence_items
        for alias in item.aliases
    )


def test_amazon_segment_alias_covers_abbreviation() -> None:
    result = assess_enumeration_completeness(
        "What are the different business segments Amazon operates?",
        AMAZON_CONTEXT,
        "Amazon operates North America, International, and AWS segments [Source 1].",
    )

    assert result.passed is True
    assert [item.label for item in result.evidence_items] == [
        "North America",
        "International",
        "Amazon Web Services",
    ]


def test_main_revenue_scope_excludes_supporting_heading_from_required_items() -> None:
    result = assess_enumeration_completeness(
        "What are the main sources of revenue for Microsoft?",
        MICROSOFT_REVENUE_CONTEXT,
        "- Server Products and Cloud Services [Source 1]\n"
        "- LinkedIn [Source 2]\n"
        "- Dynamics Products and Cloud Services [Source 2]\n"
        "- Microsoft 365 Commercial Products and Cloud Services [Source 2]\n"
        "- Gaming [Source 3]\n"
        "- Windows and Devices [Source 3]",
    )

    assert result.passed is True
    assert "search and news advertising" in {
        item.label.casefold() for item in result.evidence_items
    }
    assert "search and news advertising" not in {
        item.label.casefold() for item in result.required_items
    }
    assert next(
        item
        for item in result.evidence_items
        if item.label.casefold() == "search and news advertising"
    ).evidence_role == "supporting"


def test_revenue_intent_contract_is_evidence_bound_and_ground_truth_free() -> None:
    answer = (
        "- Server Products and Cloud Services [Source 1]\n"
        "- Microsoft 365 Commercial Products and Cloud Services [Source 2]\n"
        "- LinkedIn [Source 2]\n"
        "- Dynamics Products and Cloud Services [Source 2]\n"
        "- Gaming (Xbox) [Source 3]\n"
        "- Windows and Devices (Windows OEM; Devices) [Source 3]"
    )

    result = audit_revenue_intent_scope(
        "What are the main sources of revenue for Microsoft?",
        MICROSOFT_REVENUE_CONTEXT,
        answer,
    )

    assert result["passed"] is True
    assert result["allowed_supporting_items_are_optional"] is True
    assert result["generation_ground_truth_dependency"] is False
    assert result["supporting_evidence_items"] == [
        "Search and news advertising"
    ]


def test_missing_item_is_reported_without_using_ground_truth() -> None:
    result = assess_enumeration_completeness(
        "What are all the product categories Apple sells?",
        APPLE_CONTEXT,
        "Apple sells iPhone, Mac, and iPad [Source 1].",
    )

    assert result.passed is False
    assert "services" in {item.label.casefold() for item in result.missing_items}


def test_nested_service_name_does_not_cover_top_level_services() -> None:
    result = assess_enumeration_completeness(
        "What are all the product categories Apple sells?",
        APPLE_CONTEXT,
        "Apple sells smartphones, personal computers, tablets, wearables, "
        "accessories, and Cloud Services [Source 1].",
    )

    assert "services" in {item.label.casefold() for item in result.missing_items}


def test_nested_bulleted_services_do_not_cover_top_level_services() -> None:
    result = assess_enumeration_completeness(
        "What are all the product categories Apple sells?",
        APPLE_CONTEXT,
        "- Advertising [Source 1]\n- AppleCare [Source 1]\n"
        "- Cloud Services [Source 1]\n- Payment Services [Source 1]",
    )

    assert "services" in {item.label.casefold() for item in result.missing_items}


def test_overdetailed_list_is_flagged_without_losing_grounded_completeness() -> None:
    answer = "\n".join(
        [
            "- smartphones [Source 1]",
            "- personal computers [Source 1]",
            "- tablets [Source 1]",
            "- wearables [Source 1]",
            "- accessories [Source 1]",
            "- services [Source 1]",
            "- extra example [Source 1]",
            "- another extra example [Source 1]",
            "- third extra example [Source 1]",
        ]
    )
    result = assess_enumeration_completeness(
        "What are all the product categories Apple sells?",
        APPLE_CONTEXT,
        answer,
    )

    assert result.overdetailed is True
    assert result.passed is True


def test_risk_prose_categories_are_extracted_and_grouped() -> None:
    context = """[Source 1] MSFT 10-K, Risk Factors
STRATEGIC AND COMPETITIVE RISKS
OPERATIONAL RISKS
We may experience supply or quality problems.
Threats to security can take a variety of forms.
The occurrence of regional epidemics or a global pandemic could adversely affect our business.
The long-term effects of climate change on the global economy are unclear.
Our global business exposes us to operational and economic risks.
"""
    result = assess_enumeration_completeness(
        "What are all the major risk factors Microsoft discloses?",
        context,
        "\n".join(
            [
                "- Strategic and Competitive Risks [Source 1]",
                "- Threats to security [Source 1]",
                "- Occurrence of regional epidemics or a global pandemic [Source 1]",
                "- Long-term effects of climate change [Source 1]",
                "- Global business operational and economic risks [Source 1]",
                "- Operational Risks [Source 1]",
            ]
        ),
    )

    labels = {item.label for item in result.evidence_items}
    assert "Operational Risks" in labels
    assert "Threats to security" in labels
    assert "Occurrence of regional epidemics or a global pandemic" in labels
    assert "Long-term effects of climate change" in labels
    assert "Global business operational and economic risks" in labels


def test_risk_evidence_roles_keep_prose_complete_but_secondary() -> None:
    context = """[Source 1] MSFT 10-K, Risk Factors
STRATEGIC AND COMPETITIVE RISKS
Trade:
OPERATIONAL RISKS
Threats to security can take a variety of forms.
The occurrence of regional epidemics or a global pandemic could adversely affect our business.
"""

    items = extract_evidence_items("risk", parse_evidence_sources(context))
    roles = {item.label: item.evidence_role for item in items}

    assert roles["Strategic And Competitive Risks"] == "canonical"
    assert roles["Trade"] == "canonical"
    assert roles["Operational Risks"] == "canonical"
    assert roles["Threats to security"] == "supporting"
    assert (
        roles["Occurrence of regional epidemics or a global pandemic"]
        == "supporting"
    )


def test_risk_compaction_preserves_unknown_bullet_until_taxonomy_is_complete() -> None:
    context = """[Source 1] MSFT 10-K, Risk Factors
STRATEGIC AND COMPETITIVE RISKS
Trade:
Cybersecurity:
"""
    result = assess_enumeration_completeness(
        "What are all the major risk factors Microsoft discloses?",
        context,
        "- Strategic and Competitive Risks [Source 1]\n"
        "- Unknown filing risk [Source 1]\n"
        "- Trade [Source 1]\n",
    )

    assert result.overdetailed is True


@skip_without_data(
    "data/eval_artifacts/phase1_priority2.json",
)
def test_real_microsoft_risk_taxonomy_covers_all_rendered_top_level_items() -> None:
    import json
    from pathlib import Path

    from src.evaluation.context_packing import (
        CONTEXT_STRATEGY_SELECTIVE_V6,
        render_case_context,
    )
    from src.evaluation.test_set import TEST_SET

    question = "What are all the major risk factors Microsoft discloses?"
    test_case = next(case for case in TEST_SET if case.question == question)
    artifact = json.loads(
        Path("data/eval_artifacts/phase1_priority2.json").read_text(
            encoding="utf-8"
        )
    )
    artifact_case = next(
        case for case in artifact["cases"] if case["question"] == question
    )
    context = render_case_context(
        artifact_case,
        required_keywords=test_case.required_keywords,
        strategy=CONTEXT_STRATEGY_SELECTIVE_V6,
    )
    answer = "\n".join(
        f"- {label} [Source 1]"
        for label in (
            "Strategic and Competitive Risks",
            "Trade",
            "Cybersecurity",
            "Handling of personal data",
            "Issues in the development, deployment, and use of AI",
            "Operational Risks",
            "Legal, regulatory, and litigation risks",
            "Threats to security",
            "Occurrence of regional epidemics or a global pandemic",
            "Long-term effects of climate change",
            "Global business operational and economic risks",
        )
    )
    result = assess_enumeration_completeness(question, context, answer)

    assert len(result.evidence_items) == 11
    assert result.missing_items == ()


def test_non_exhaustive_question_is_a_noop() -> None:
    result = assess_enumeration_completeness(
        "Summarize Apple's key risk factors related to competition.",
        APPLE_CONTEXT,
        "Competition is discussed [Source 1].",
    )

    assert result.applicable is False
    assert result.passed is True
    assert result.evidence_items == ()


def test_fingerprint_is_stable_and_nonempty() -> None:
    assert ENUMERATION_COMPLETENESS_FINGERPRINT.startswith("sha256:")
    assert len(ENUMERATION_COMPLETENESS_FINGERPRINT) == 71
