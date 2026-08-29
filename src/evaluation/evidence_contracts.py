"""Fact-specific evidence requirements shared by offline quality gates."""

from __future__ import annotations


EXPECTED_FACT_OVERRIDES: dict[str, tuple[str, ...]] = {
    "Which company, Apple or Amazon, had higher total revenue in fiscal year 2024?": (
        "391,035",
        "637,959",
    ),
    "How does Amazon's AWS segment compare to Microsoft's cloud business in terms of growth?": (
        "107,556",
        "128,725",
    ),
}


def evidence_terms(
    question: str,
    required_keywords: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Return deduplicated keyword and fact requirements for one case."""
    return tuple(
        dict.fromkeys(
            [
                *(required_keywords or ()),
                *EXPECTED_FACT_OVERRIDES.get(question, ()),
            ]
        )
    )
