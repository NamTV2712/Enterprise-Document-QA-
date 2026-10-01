from src.api.content_presentation import build_chunk_presentation, parse_indexed_markdown_table


def test_parses_existing_lossless_table_shape() -> None:
    text = "### Revenue\nUnits: USD in millions\n| Metric | 2025 | 2024 |\n|---|---|---|\n| Total net sales | 416,161 | 391,035 |"
    result = parse_indexed_markdown_table(text)
    assert result == {
        "kind": "markdown_table",
        "caption": "Revenue",
        "units": "USD in millions",
        "columns": ["Metric", "2025", "2024"],
        "rows": [["Total net sales", "416,161", "391,035"]],
    }


def test_rejects_uneven_or_ambiguous_rows_without_repairing_values() -> None:
    text = "| Metric | 2025 | 2024 |\n|---|---|---|\n| Total net sales | 416,161 | 391,035 | extra |"
    assert parse_indexed_markdown_table(text) is None
    assert build_chunk_presentation(text, "financial_table")["kind"] == "plain_text"


def test_non_financial_chunk_is_not_reclassified_as_a_table() -> None:
    result = build_chunk_presentation("| Metric | 2025 | 2024 |", "risk_factors")
    assert result == {"kind": "plain_text", "reason": "not_financial_table"}
