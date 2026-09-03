from src.generation.evidence_fact_renderer import (
    render_auditor_fact,
    render_single_period_net_sales_fact,
)


def test_auditor_renderer_repairs_signature_line_wrap_without_ground_truth() -> None:
    context = """[Source 1] MSFT 10-K, Financial Statements
/s/
D
ELOITTE
 & T
OUCHE
 LLP

Seattle, Washington
July 30, 2025
"""

    answer = render_auditor_fact(
        "Who audited Microsoft's financial statements?", context
    )

    assert answer == (
        "Microsoft's financial statements were audited by Deloitte & Touche LLP "
        "[Source 1]."
    )


def test_auditor_renderer_is_scoped_to_the_question_intent() -> None:
    context = """[Source 1] Filing
/s/
Example Audit LLP

Seattle, Washington
"""

    assert render_auditor_fact("What is Microsoft's total revenue?", context) is None


def test_net_sales_renderer_maps_the_requested_year_and_preserves_units() -> None:
    context = """[Source 1] Apple 10-K, Financial Table
| Metric | 2025 | 2024 | 2023 |
|---|---|---|---|
| Total net sales | 416,161 | 391,035 | 383,285 |
The table reports dollars in millions.
"""

    answer = render_single_period_net_sales_fact(
        "What was Apple's total net sales in fiscal year 2025?", context
    )

    assert answer == (
        "Apple's total net sales in fiscal year 2025 were $416,161 million "
        "[Source 1]."
    )


def test_net_sales_renderer_handles_consolidated_segment_rows() -> None:
    context = """[Source 1] Amazon 10-K, MD&A
Year Ended December 31,
2024
2025
Net Sales:
North America
$
387,497
$
426,305
Consolidated
$
637,959
$
716,924
Operating Expenses (in millions)
"""

    answer = render_single_period_net_sales_fact(
        "What was Amazon's consolidated net sales in 2024?", context
    )

    assert answer == (
        "Amazon's consolidated net sales in fiscal year 2024 were $637,959 "
        "million [Source 1]."
    )
