from tests.fixtures.workspace_matrix import WORKSPACE_QUERY_MATRIX


def test_registered_workspace_matrix_has_120_independent_language_variants() -> None:
    assert len(WORKSPACE_QUERY_MATRIX) == 120
    assert len({item["id"] for item in WORKSPACE_QUERY_MATRIX}) == 120
    assert {item["variant"] for item in WORKSPACE_QUERY_MATRIX} == {"en", "vi", "vi-unaccented"}
    assert all(item["expected_signals"] for item in WORKSPACE_QUERY_MATRIX)
    assert sum(item["language"] == "vi" for item in WORKSPACE_QUERY_MATRIX) == 80
