from scripts.diagnostics.financial_table_unit_candidate import (
    ENRICHMENT_FINGERPRINT,
    enrich_artifact,
)


def test_candidate_enrichment_changes_only_financial_table_text() -> None:
    from bs4 import BeautifulSoup

    artifact = {
        "schema_version": 2,
        "plans": [],
        "cases": [
            {
                "question": "What was Apple's total net sales in fiscal year 2025?",
                "queries": [
                    {
                        "chunks": [
                            {
                                "chunk_id": "AAPL_000000000000000001_financial_table_0",
                                "section": "financial_table",
                                "text": "### Statement\n| Metric | 2025 | 2024 |\n|---|---|---|\n| Total net sales | 416,161 | 391,035 |",
                            },
                            {
                                "chunk_id": "AAPL_000000000000000001_business_0",
                                "section": "business",
                                "text": "Unchanged prose",
                            },
                        ]
                    }
                ],
            }
        ],
        "fingerprints": {"artifact": "sha256:" + "a" * 64},
    }

    # The candidate's raw-table lookup is intentionally isolated from this
    # unit test; patch it to prove artifact semantics without filesystem I/O.
    import scripts.diagnostics.financial_table_unit_candidate as module

    soup = BeautifulSoup(
        "<p>Consolidated statements of operations (in millions)</p>"
        "<table><tr><td>Metric</td><td>2025</td></tr></table>",
        "lxml",
    )
    original = module._load_raw_table
    module._load_raw_table = lambda *args: (soup.table, "test")
    try:
        candidate, report = enrich_artifact(artifact)
    finally:
        module._load_raw_table = original

    assert report["financial_table_chunk_occurrences_changed"] == 1
    assert report["financial_table_chunk_occurrences_unresolved"] == 0
    assert candidate["cases"][0]["queries"][0]["chunks"][0]["text"] == (
        "### Statement\nUnits: in millions\n"
        "| Metric | 2025 | 2024 |\n|---|---|---|\n"
        "| Total net sales | 416,161 | 391,035 |"
    )
    assert candidate["cases"][0]["queries"][0]["chunks"][1]["text"] == (
        "Unchanged prose"
    )
    assert candidate["fingerprints"]["financial_table_unit_enrichment"] == (
        ENRICHMENT_FINGERPRINT
    )


def test_candidate_enrichment_is_deterministic_for_noop_artifact() -> None:
    artifact = {
        "schema_version": 2,
        "plans": [],
        "cases": [],
        "fingerprints": {"artifact": "sha256:" + "b" * 64},
    }

    first, first_report = enrich_artifact(artifact)
    second, second_report = enrich_artifact(artifact)

    assert first == second
    assert first_report == second_report
