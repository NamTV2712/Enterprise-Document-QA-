from src.generation.visual_answer import build_visual_answer
from src.retrieval.retriever import RetrievedChunk


def _chunk(text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="AAPL_table_0",
        ticker="AAPL",
        section="financial_table",
        filing_date="2025-10-31",
        score=10.0,
        text=text,
        citation="Apple 10-K, Financial Table",
    )


def test_visual_answer_emits_one_source_bound_net_sales_metric() -> None:
    fact = build_visual_answer(
        "What was Apple's total net sales in fiscal year 2025?",
        [_chunk("""| Metric | 2025 | 2024 |
|---|---|---|
| Total net sales | 416,161 | 391,035 |
The table reports dollars in millions.""")],
    )

    assert fact == {
        "kind": "metric",
        "metric": "net_sales",
        "label": "Apple total net sales",
        "value": "416161",
        "display_value": "$416,161 million",
        "unit": "USD million",
        "period": "2025",
        "source_index": 0,
        "source_chunk_id": "AAPL_table_0",
        "citation": "Apple 10-K, Financial Table",
        "evidence_quote": "| Total net sales | 416,161 | 391,035 |",
    }


def test_visual_answer_refuses_a_value_without_a_local_unit_and_quote() -> None:
    assert build_visual_answer(
        "What was Apple's total net sales in fiscal year 2025?",
        [_chunk("Total net sales were 416,161 in 2025.")],
    ) is None
