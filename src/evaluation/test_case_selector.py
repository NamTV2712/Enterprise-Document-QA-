"""Shared deterministic selection rules for evaluation phases.

The default selector is the historical cumulative priority contract.  Exact
priority selection is an opt-in scope used by shadow campaigns so a priority-3
run cannot accidentally include the protected priority-1/2 benchmark cases.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from src.evaluation.test_set import TestCase


@dataclass(frozen=True)
class TestCaseSelection:
    """Selected cases plus the auditable predicate that produced them."""

    cases: tuple[TestCase, ...]
    priority: int
    exact_priority: bool
    categories: tuple[str, ...]

    @property
    def questions(self) -> tuple[str, ...]:
        return tuple(case.question for case in self.cases)

    @property
    def scope(self) -> str:
        operator = "==" if self.exact_priority else "<="
        return f"priority {operator} {self.priority}"

    def provenance(self) -> dict[str, Any]:
        """Return stable selection metadata suitable for an artifact."""
        question_hash = hashlib.sha256(
            json.dumps(
                list(self.questions),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return {
            "selector": "shared_test_case_selector_v1",
            "selection_scope": self.scope,
            "priority": self.priority,
            "exact_priority": self.exact_priority,
            "categories": list(self.categories),
            "selected_case_count": len(self.cases),
            "selected_questions_sha256": f"sha256:{question_hash}",
        }


def select_test_cases(
    test_set: Sequence[TestCase],
    *,
    priority: int,
    exact_priority: bool = False,
    categories: Iterable[str] = (),
) -> TestCaseSelection:
    """Select cases in test-set order using one explicit priority policy."""
    if priority < 1:
        raise ValueError("priority must be at least 1")
    selected_categories = tuple(sorted(set(categories)))
    category_set = set(selected_categories)
    if exact_priority:
        selected = [case for case in test_set if case.priority == priority]
    else:
        selected = [case for case in test_set if case.priority <= priority]
    if category_set:
        selected = [case for case in selected if case.category in category_set]
    return TestCaseSelection(
        cases=tuple(selected),
        priority=priority,
        exact_priority=exact_priority,
        categories=selected_categories,
    )
