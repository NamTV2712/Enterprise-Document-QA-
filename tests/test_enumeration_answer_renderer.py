from src.generation.enumeration_answer_renderer import (
    render_deterministic_revenue_answer,
)


QUESTION = "What are the main sources of revenue for Microsoft?"
CONTEXT = """[Source 1] Microsoft 10-K, Business
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


def test_revenue_renderer_keeps_only_main_revenue_scope() -> None:
    first = render_deterministic_revenue_answer(QUESTION, CONTEXT)
    second = render_deterministic_revenue_answer(QUESTION, CONTEXT)

    assert first == second
    assert first == (
        "- Server Products and Cloud Services (Azure; Server Products) [Source 1]\n"
        "- LinkedIn [Source 2]\n"
        "- Dynamics Products and Cloud Services [Source 2]\n"
        "- Microsoft 365 Commercial Products and Cloud Services [Source 2]\n"
        "- Gaming (Xbox) [Source 3]\n"
        "- Windows and Devices (Windows OEM; Devices) [Source 3]"
    )


def test_revenue_renderer_keeps_supporting_heading_for_exhaustive_question() -> None:
    answer = render_deterministic_revenue_answer(
        "What are all of Microsoft's revenue sources?", CONTEXT
    )

    assert answer is not None
    assert "Search and news advertising (Bing; Copilot) [Source 3]" in answer


def test_revenue_renderer_is_scoped_to_revenue_enumerations() -> None:
    assert render_deterministic_revenue_answer(
        "What was Microsoft's total revenue in 2025?", CONTEXT
    ) is None
