# src/evaluation/test_set.py
from dataclasses import dataclass, field

@dataclass
class TestCase:
    question: str
    ticker: str | None
    section: str | None
    ground_truth: str
    # Recall proxy terms that must appear in retrieved chunks for the test
    # to count as retrieving the necessary evidence.
    required_keywords: list[str] = field(default_factory=list)
    # True when the expected behavior is an insufficient-context answer.
    expects_fallback: bool = False

TEST_SET: list[TestCase] = [
    TestCase(
        question="What was Apple's total net sales in fiscal year 2024?",
        ticker="AAPL",
        section="financial_statements",
        ground_truth="Apple's total net sales in fiscal year 2024 were $391,035 million.",
        required_keywords=["391,035"],
    ),
    TestCase(
        question="What are the main sources of revenue for Microsoft?",
        ticker="MSFT",
        section="business",
        ground_truth="Microsoft generates revenue from cloud services (Azure), productivity software (Office 365), LinkedIn, gaming (Xbox), and Dynamics business applications.",
        required_keywords=["Azure", "LinkedIn"],
    ),
    TestCase(
        question="What are the key risk factors related to competition for Apple?",
        ticker="AAPL",
        section="risk_factors",
        ground_truth="Apple faces intense competition in all its markets including smartphones, PCs, tablets, wearables and services.",
        required_keywords=["compet"],
    ),
    TestCase(
        question="What is Amazon's AWS operating income for 2025?",
        ticker="AMZN",
        section="mdna",
        ground_truth="Amazon AWS had strong operating income growth, with AWS being the most profitable segment.",
        required_keywords=["AWS", "operating income"],
    ),
    TestCase(
        question="What does Microsoft say about cybersecurity risks?",
        ticker="MSFT",
        section="risk_factors",
        ground_truth="Microsoft faces significant cybersecurity risks including data breaches, unauthorized access, and security vulnerabilities that could harm its business.",
        required_keywords=["cyber", "security"],
    ),
    TestCase(
        question="What is Tesla's revenue in 2024?",
        ticker=None,
        section=None,
        ground_truth="Tesla is not in the document corpus, so the system should indicate insufficient information.",
        expects_fallback=True,
    ),
]
