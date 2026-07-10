from dataclasses import dataclass, field
from typing import Literal

Category = Literal[
    "fact_lookup",
    "summary",
    "enumeration",
    "comparative",
    "multi_hop",
    "out_of_corpus",
]


@dataclass
class TestCase:
    question: str
    category: Category
    ticker: str | None
    section: str | None
    ground_truth: str
    required_keywords: list[str] = field(default_factory=list)
    expects_fallback: bool = False
    expects_decomposition: bool = False
    priority: int = 1


TEST_SET: list[TestCase] = [
    # Fact lookup: one company, one section, specific evidence.
    TestCase(
        question="What was Apple's total net sales in fiscal year 2024?",
        category="fact_lookup",
        ticker="AAPL",
        section=None,
        ground_truth="Apple's total net sales in fiscal year 2024 were $391,035 million.",
        required_keywords=["391,035"],
    ),
    TestCase(
        question="What was Apple's total net sales in fiscal year 2025?",
        category="fact_lookup",
        ticker="AAPL",
        section=None,
        ground_truth="Apple's total net sales in fiscal year 2025 were $416,161 million.",
        required_keywords=["416,161"],
        priority=2,
    ),
    TestCase(
        question="What was Microsoft's total assets as of fiscal year 2025?",
        category="fact_lookup",
        ticker="MSFT",
        section=None,
        ground_truth="Microsoft's total assets were $619,003 million as of fiscal year 2025.",
        required_keywords=["619,003"],
    ),
    TestCase(
        question="What was Amazon's AWS net sales in 2025?",
        category="fact_lookup",
        ticker="AMZN",
        section="mdna",
        ground_truth="Amazon's AWS net sales were $128,725 million in 2025.",
        required_keywords=["128,725"],
    ),
    TestCase(
        question="What was Amazon's consolidated net sales in 2024?",
        category="fact_lookup",
        ticker="AMZN",
        section="mdna",
        ground_truth="Amazon's consolidated net sales were $637,959 million in 2024.",
        required_keywords=["637,959"],
        priority=2,
    ),
    TestCase(
        question="What was Amazon's North America operating income in 2025?",
        category="fact_lookup",
        ticker="AMZN",
        section="mdna",
        ground_truth="Amazon's North America operating income was $29,619 million in 2025.",
        required_keywords=["29,619"],
        priority=2,
    ),
    TestCase(
        question="Who audited Apple's financial statements and when was the report signed?",
        category="fact_lookup",
        ticker="AAPL",
        section=None,
        ground_truth="Ernst & Young LLP audited Apple's financial statements, signed October 31, 2025.",
        required_keywords=["Ernst", "Young"],
    ),
    TestCase(
        question="Who audited Microsoft's financial statements?",
        category="fact_lookup",
        ticker="MSFT",
        section=None,
        ground_truth="Deloitte & Touche LLP audited Microsoft's financial statements.",
        required_keywords=["Deloitte"],
        priority=2,
    ),

    # Summary: one company, one topic, synthesis over a focused section.
    TestCase(
        question="Summarize the key risk factors related to competition for Apple.",
        category="summary",
        ticker="AAPL",
        section="risk_factors",
        ground_truth="Apple faces intense competition in all markets including smartphones, PCs, tablets, wearables and services.",
        required_keywords=["compet"],
    ),
    TestCase(
        question="What does Microsoft say about cybersecurity risks?",
        category="summary",
        ticker="MSFT",
        section="risk_factors",
        ground_truth="Microsoft faces cybersecurity risks including data breaches and unauthorized access from nation-state actors and cybercriminals.",
        required_keywords=["cyber", "security"],
    ),
    TestCase(
        question="What risks does Amazon face related to its international operations?",
        category="summary",
        ticker="AMZN",
        section="risk_factors",
        ground_truth="Amazon faces risks from international operations including regulatory, currency, and geopolitical factors.",
        required_keywords=["international"],
        priority=2,
    ),
    TestCase(
        question="What quality and manufacturing risks does Apple mention?",
        category="summary",
        ticker="AAPL",
        section="risk_factors",
        ground_truth="Apple faces risks from design and manufacturing defects and third-party component quality issues.",
        required_keywords=["defect"],
        priority=2,
    ),
    TestCase(
        question="How does Microsoft describe its Azure and cloud services growth?",
        category="summary",
        ticker="MSFT",
        section="mdna",
        ground_truth="Microsoft's Intelligent Cloud revenue increased significantly, driven by Azure and other cloud services growth of over 20%.",
        required_keywords=["Azure", "cloud"],
    ),
    TestCase(
        question="What does Amazon say about risks from government contracts?",
        category="summary",
        ticker="AMZN",
        section="risk_factors",
        ground_truth="Amazon faces risks of debarment or termination from government business due to contract compliance issues.",
        required_keywords=["government"],
        priority=2,
    ),

    # Enumeration: exhaustive listing across multiple items in one company.
    TestCase(
        question="What are the main sources of revenue for Microsoft?",
        category="enumeration",
        ticker="MSFT",
        section="business",
        ground_truth="Microsoft's revenue sources include Microsoft 365, Azure/cloud services, LinkedIn, Dynamics, Xbox/gaming, Windows OEM, and Devices.",
        required_keywords=["Azure", "LinkedIn"],
        expects_decomposition=True,
    ),
    TestCase(
        question="What are all the product categories Apple sells?",
        category="enumeration",
        ticker="AAPL",
        section="business",
        ground_truth="Apple sells iPhone, Mac, iPad, wearables/accessories, and services.",
        required_keywords=["iPhone", "Mac", "iPad"],
        expects_decomposition=True,
    ),
    TestCase(
        question="What are the different business segments Amazon operates?",
        category="enumeration",
        ticker="AMZN",
        section="mdna",
        ground_truth="Amazon operates North America, International, and AWS segments.",
        required_keywords=["North America", "AWS"],
        expects_decomposition=True,
    ),
    TestCase(
        question="What are all the major risk factors Microsoft discloses?",
        category="enumeration",
        ticker="MSFT",
        section="risk_factors",
        ground_truth="Microsoft discloses risks including competition, cybersecurity, AI, data privacy, and global economic conditions.",
        required_keywords=["cyber", "compet"],
        expects_decomposition=True,
    ),

    # Comparative: two or more companies.
    TestCase(
        question="Compare Apple and Microsoft's approach to cloud/services revenue.",
        category="comparative",
        ticker=None,
        section=None,
        ground_truth="Apple generates services revenue including cloud storage; Microsoft generates cloud revenue primarily through Azure.",
        required_keywords=["Azure"],
        expects_decomposition=True,
    ),
    TestCase(
        question="Which company, Apple or Amazon, has higher total revenue?",
        category="comparative",
        ticker=None,
        section=None,
        ground_truth="Amazon's consolidated net sales are significantly higher than Apple's total net sales.",
        required_keywords=["Amazon"],
        expects_decomposition=True,
    ),
    TestCase(
        question="Compare the cybersecurity risk disclosures of Apple, Microsoft, and Amazon.",
        category="comparative",
        ticker=None,
        section=None,
        ground_truth="All three companies disclose cybersecurity risks; Microsoft provides detailed disclosure given its cloud infrastructure focus.",
        expects_decomposition=True,
    ),
    TestCase(
        question="How does Amazon's AWS segment compare to Microsoft's cloud business in terms of growth?",
        category="comparative",
        ticker=None,
        section=None,
        ground_truth="Both AWS and Microsoft's Azure/cloud services showed strong growth, though exact comparison requires both companies' specific figures.",
        expects_decomposition=True,
        priority=2,
    ),
    TestCase(
        question="Which company depends more on cloud/subscription revenue, Microsoft or Apple?",
        category="comparative",
        ticker=None,
        section=None,
        ground_truth="Microsoft depends more heavily on cloud revenue as a core growth driver compared to Apple's services segment.",
        expects_decomposition=True,
        priority=2,
    ),
    TestCase(
        question="Compare Apple's and Amazon's approach to international operations risk.",
        category="comparative",
        ticker=None,
        section=None,
        ground_truth="Both companies disclose international operations risks including currency, regulatory, and geopolitical factors.",
        required_keywords=["international"],
        expects_decomposition=True,
        priority=2,
    ),

    # Multi-hop: multiple evidence points across time or rows.
    TestCase(
        question="How did Apple's total net sales trend from 2023 to 2025?",
        category="multi_hop",
        ticker="AAPL",
        section=None,
        ground_truth="Apple's net sales grew from $383,285M in 2023 to $391,035M in 2024 to $416,161M in 2025.",
        required_keywords=["383,285", "416,161"],
    ),
    TestCase(
        question="How did Amazon's AWS net sales change from 2024 to 2025?",
        category="multi_hop",
        ticker="AMZN",
        section=None,
        ground_truth="Amazon's AWS net sales grew from $107,556M in 2024 to $128,725M in 2025.",
        required_keywords=["107,556", "128,725"],
    ),
    TestCase(
        question="How did Microsoft's total assets change year over year?",
        category="multi_hop",
        ticker="MSFT",
        section=None,
        ground_truth="Microsoft's total assets grew from $512,163M to $619,003M.",
        required_keywords=["512,163", "619,003"],
    ),

    # Out of corpus: fallback behavior is required.
    TestCase(
        question="What is Tesla's revenue in 2024?",
        category="out_of_corpus",
        ticker=None,
        section=None,
        ground_truth="Tesla is not in the document corpus.",
        expects_fallback=True,
    ),
    TestCase(
        question="What are Nvidia's main risk factors?",
        category="out_of_corpus",
        ticker=None,
        section=None,
        ground_truth="Nvidia is not in the document corpus.",
        expects_fallback=True,
        priority=2,
    ),
    TestCase(
        question="What was Google's total revenue in 2024?",
        category="out_of_corpus",
        ticker=None,
        section=None,
        ground_truth="Google/Alphabet is not in the document corpus.",
        expects_fallback=True,
        priority=2,
    ),
]
