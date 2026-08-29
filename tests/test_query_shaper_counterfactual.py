from scripts.diagnostics.query_shaper_counterfactual import DEFAULT_QUERY


def test_counterfactual_defaults_to_aws_growth_case() -> None:
    assert DEFAULT_QUERY == "Amazon AWS growth"
