from src.retrieval.structured_lookup import (
    CANONICAL_LABELS,
    detect_structured_query,
    _label_matches_canonical,
    structured_lookup,
)


def matches_canonical(label: str, canonical_key: str) -> bool:
    return _label_matches_canonical(label, CANONICAL_LABELS[canonical_key])


def test_detect_structured_total_assets_query():
    assert detect_structured_query("What was Microsoft's total assets?") == "total assets"
    assert detect_structured_query("Tell me about assets") is None


def test_detect_structured_auditor_query():
    assert detect_structured_query("Who audited Microsoft's financial statements?") == "auditor signature"
    assert detect_structured_query("When was Apple's audit report signed?") == "auditor signature"
    assert detect_structured_query("Summarize Microsoft's audit risks") is None


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


def test_structured_lookup_prefers_consolidated_table_for_duplicate_total_rows():
    chunks = [
        {
            "chunk_id": "investee_table",
            "ticker": "KO",
            "section": "financial_table",
            "text": "### Company equity income (loss) - net\n"
            "| Metric | 2025 | 2024 |\n"
            "|---|---|---|\n"
            "| Assets - Total assets | 115,098 | 105,759 |",
        },
        {
            "chunk_id": "consolidated_table",
            "ticker": "KO",
            "section": "financial_table",
            "text": "### Consolidated Balance Sheets\n"
            "| Metric | 2025 | 2024 |\n"
            "|---|---|---|\n"
            "| Assets - Total assets | 100 | 90 |",
        },
    ]

    match = structured_lookup("What was Coca-Cola's total assets?", "KO", chunks)

    assert match is not None
    assert match.chunk["chunk_id"] == "consolidated_table"


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


def test_equity_subcomponents_do_not_match_total_equity():
    """Equity section subcomponents must not match the total equity row."""
    subcomponent_labels = [
        "Shareholders' equity - Retained earnings",
        "Stockholders' equity - Retained earnings",
        "Stockholders' equity - Additional paid-in capital",
        "Shareholders' equity - Common stock",
    ]

    for label in subcomponent_labels:
        assert not matches_canonical(label, "total equity")


def test_equity_with_commitments_prefix_matches():
    """Real commitment-note prefixes should still match total equity rows."""
    variants_with_notes = [
        "Commitments and contingencies (see Note 12) - Total stockholders' equity",
        "Commitments and contingencies (Note 7) - Total stockholders' equity",
        "Commitments and Contingencies (Note 10) - Total stockholders' equity",
        "Commitments and contingencies (see Note 12) - Total shareholders' equity",
    ]

    for label in variants_with_notes:
        assert matches_canonical(label, "total equity")


def test_quote_normalization_handles_unicode_and_ascii_quotes():
    """Unicode and ASCII apostrophes should behave the same in label matching."""
    unicode_version = "Total stockholders\u2019 equity"
    ascii_version = "Total stockholders' equity"

    assert matches_canonical(unicode_version, "total equity")
    assert matches_canonical(ascii_version, "total equity")


def test_structured_lookup_matches_auditor_signature_chunk():
    chunks = [
        {
            "chunk_id": "report_header",
            "ticker": "MSFT",
            "section": "financial_statements",
            "text": "REPORT OF INDEPENDENT REGISTERED PUBLIC ACCOUNTING FIRM To the Stockholders",
        },
        {
            "chunk_id": "signature",
            "ticker": "MSFT",
            "section": "financial_statements",
            "text": "/s/\nD\nELOITTE\n & T\nOUCHE\n LLP\nSeattle, Washington\nJuly 30, 2025\nWe have served as the Company's auditor since 1983.",
        },
    ]

    match = structured_lookup("Who audited Microsoft's financial statements?", "MSFT", chunks)

    assert match is not None
    assert match.chunk["chunk_id"] == "signature"
    assert match.canonical_key == "auditor signature"


def test_auditor_lookup_requires_signature_marker():
    chunks = [
        {
            "chunk_id": "audit_matter",
            "ticker": "MSFT",
            "section": "financial_statements",
            "text": "Evaluating estimates required auditor judgment and tax specialists.",
        }
    ]

    assert structured_lookup("Who audited Microsoft's financial statements?", "MSFT", chunks) is None
