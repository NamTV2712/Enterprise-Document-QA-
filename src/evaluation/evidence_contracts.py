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

# Branch-scoped requirements are used only when a comparative plan needs a
# lower-ranked donor from one company branch. They encode the A/B findings
# that question-wide keyword coverage cannot distinguish.
EXPECTED_BRANCH_FACTS: dict[str, dict[str, tuple[str, ...]]] = {
    "Compare the cybersecurity risk disclosures of Apple, Microsoft, and Amazon.": {
        "AMZN": ("Data Loss", "Security Incidents"),
    },
    "How does Amazon's AWS segment compare to Microsoft's cloud business in terms of growth?": {
        "AMZN": ("107,556", "128,725"),
        "MSFT": ("Microsoft Cloud revenue increased", "168.9 billion"),
    },
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


def branch_evidence_terms(question: str, ticker: str | None) -> tuple[str, ...]:
    """Return fact requirements that must be satisfied inside one branch."""
    if not ticker:
        return ()
    return EXPECTED_BRANCH_FACTS.get(question, {}).get(ticker, ())
