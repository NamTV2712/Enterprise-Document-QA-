import re

from src.retrieval.query_normalizer import normalize_retrieval_question
from tests.fixtures.workspace_matrix import WORKSPACE_QUERY_MATRIX


def test_registered_workspace_matrix_has_120_independent_language_variants() -> None:
    assert len(WORKSPACE_QUERY_MATRIX) == 120
    assert len({item["id"] for item in WORKSPACE_QUERY_MATRIX}) == 120
    assert {item["variant"] for item in WORKSPACE_QUERY_MATRIX} == {"en", "vi", "vi-unaccented"}
    assert all(item["expected_signals"] for item in WORKSPACE_QUERY_MATRIX)
    assert sum(item["language"] == "vi" for item in WORKSPACE_QUERY_MATRIX) == 80


def test_all_120_variants_execute_the_same_provider_free_interpretation_contract() -> None:
    """Freeze the language matrix at the normalizer boundary, not just as data."""
    for item in WORKSPACE_QUERY_MATRIX:
        normalized = normalize_retrieval_question(item["query"])
        years = tuple(dict.fromkeys(re.findall(r"\b(?:19|20)\d{2}\b", item["query"])))

        assert normalized.question.strip(), item["id"]
        assert normalized.requested_periods == years, item["id"]
        if item["variant"] == "en":
            assert normalized.translated_from_vietnamese is False, item["id"]
        else:
            # Accent loss must not make a Vietnamese fixture disappear or
            # invent a period; high-confidence metric phrases may translate,
            # while ambiguous/non-metric text is intentionally preserved.
            assert normalized.question.strip() == normalized.question, item["id"]

    gross_profit = next(item for item in WORKSPACE_QUERY_MATRIX if item["id"] == "gross-profit-vi")
    normalized_gross_profit = normalize_retrieval_question(gross_profit["query"])
    assert "gross profit" in normalized_gross_profit.question.lower()

    comparison = next(item for item in WORKSPACE_QUERY_MATRIX if item["id"] == "operating-income-vi-unaccented")
    normalized_comparison = normalize_retrieval_question(comparison["query"])
    assert normalized_comparison.is_comparative is True
    assert normalized_comparison.requested_periods == ("2023", "2024")
