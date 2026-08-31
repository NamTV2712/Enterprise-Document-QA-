from scripts.diagnostics.context_precision_attribution import _completion_row


AWS_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
)

AWS_CONTEXT = """[Source 1] AMZN 10-K
2024
2025
AWS
107,556
128,725
"""


def test_attribution_completion_probe_detects_derived_value() -> None:
    result = _completion_row(
        AWS_QUESTION,
        "AWS reported 107,556 in 2024 and 128,725 in 2025 [Source 1]. "
        "The increase was $21,169 [Source 1].",
        AWS_CONTEXT,
    )

    assert result["applicable"] is True
    assert result["period_value_passed"] is True
    assert result["grounding_passed"] is False
    assert result["correction_required"] is True
    assert result["unsupported_numeric_claims"] == ["$21,169"]
