from src.retrieval.structured_lookup import (
    detect_structured_query,
    structured_lookup,
)


def test_detect_structured_total_assets_query():
    assert detect_structured_query("What was Microsoft's total assets?") == "total assets"
    assert detect_structured_query("Tell me about assets") is None


def test_structured_lookup_matches_exact_total_assets_row():
    chunks = [
        {
            "chunk_id": "wrong",
            "ticker": "MSFT",
            "section": "financial_table",
            "text": "| Metric | 2025 | 2024 |\n|---|---|---|\n| Assets - Total current assets | 191,412 | 159,734 |",
        },
        {
            "chunk_id": "right",
            "ticker": "MSFT",
            "section": "financial_table",
            "text": "| Metric | 2025 | 2024 |\n|---|---|---|\n| Assets - Total assets | 619,003 | 512,163 |",
        },
    ]

    match = structured_lookup("What was Microsoft's total assets?", "MSFT", chunks)

    assert match is not None
    assert match.chunk["chunk_id"] == "right"
    assert match.label == "Assets - Total assets"


def test_structured_lookup_matches_prefixed_total_assets_row():
    chunks = [
        {
            "chunk_id": "subtotal",
            "ticker": "JNJ",
            "section": "financial_table",
            "text": "| Metric | 2025 | 2024 |\n| Current assets - Total current assets | 55,624 | 55,893 |",
        },
        {
            "chunk_id": "total",
            "ticker": "JNJ",
            "section": "financial_table",
            "text": "| Metric | 2025 | 2024 |\n| Current assets - Total assets | 180,104 | - |",
        },
    ]

    match = structured_lookup("What was JNJ's total assets?", "JNJ", chunks)

    assert match is not None
    assert match.chunk["chunk_id"] == "total"
    assert match.label == "Current assets - Total assets"


def test_structured_lookup_requires_ticker():
    chunks = [
        {
            "chunk_id": "right",
            "ticker": "MSFT",
            "section": "financial_table",
            "text": "| Metric | 2025 | 2024 |\n| Assets - Total assets | 619,003 | 512,163 |",
        }
    ]

    assert structured_lookup("What was total assets?", None, chunks) is None


def test_structured_lookup_ignores_non_total_queries():
    chunks = [
        {
            "chunk_id": "right",
            "ticker": "AAPL",
            "section": "financial_table",
            "text": "| Metric | 2025 | 2024 |\n| Assets - Total assets | 359,241 | 364,980 |",
        }
    ]

    assert structured_lookup("What are Apple's main risk factors?", "AAPL", chunks) is None
