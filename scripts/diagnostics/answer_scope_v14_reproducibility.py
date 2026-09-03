"""Audit two V14 sentinel reports without provider calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.diagnostics import answer_scope_reproducibility as base
from src.generation.risk_answer_shape import RISK_ANSWER_SHAPE_FINGERPRINT
from src.generation.enumeration_answer_renderer import (
    ENUMERATION_ANSWER_RENDERER_FINGERPRINT,
)


DEFAULT_R1 = Path("data/eval_artifacts/answer_scope_v14_sentinel_summary_r1.json")
DEFAULT_R2 = Path("data/eval_artifacts/answer_scope_v14_sentinel_summary_r2.json")
DEFAULT_OUTPUT = Path("data/diagnostics/answer_scope_v14_reproducibility.json")
RISK_QUESTION = "What are all the major risk factors Microsoft discloses?"
REVENUE_QUESTION = "What are the main sources of revenue for Microsoft?"


def _risk_answer(report: dict[str, Any]) -> str:
    for case in report.get("cases", []):
        if case.get("question") == RISK_QUESTION:
            return str(case.get("answer") or "")
    return ""


def _revenue_answer(report: dict[str, Any]) -> str:
    for case in report.get("cases", []):
        if case.get("question") == REVENUE_QUESTION:
            return str(case.get("answer") or "")
    return ""


def build_report(
    first: dict[str, Any],
    second: dict[str, Any],
    first_path: Path | None = None,
    second_path: Path | None = None,
    audit_version: str = "v14",
) -> dict[str, Any]:
    report = base.build_report(first, second, first_path, second_path)
    gates = dict(report.get("gates") or {})
    gates.update(
        {
            "both_use_deterministic_risk_renderer": (
                first.get("deterministic_risk_renderer") is True
                and second.get("deterministic_risk_renderer") is True
            ),
            "same_risk_answer_shape_fingerprint": (
                first.get("risk_answer_shape_fingerprint")
                == RISK_ANSWER_SHAPE_FINGERPRINT
                and second.get("risk_answer_shape_fingerprint")
                == RISK_ANSWER_SHAPE_FINGERPRINT
            ),
            "same_microsoft_risk_answer": (
                _risk_answer(first) == _risk_answer(second)
                and bool(_risk_answer(first))
            ),
            "both_use_deterministic_revenue_renderer": (
                first.get("deterministic_revenue_renderer") is True
                and second.get("deterministic_revenue_renderer") is True
            ),
            "same_revenue_renderer_fingerprint": (
                first.get("enumeration_answer_renderer_fingerprint")
                == ENUMERATION_ANSWER_RENDERER_FINGERPRINT
                and second.get("enumeration_answer_renderer_fingerprint")
                == ENUMERATION_ANSWER_RENDERER_FINGERPRINT
            ),
            "same_revenue_answer": (
                _revenue_answer(first) == _revenue_answer(second)
                and bool(_revenue_answer(first))
            ),
        }
    )
    report.update(
        {
            "audit": f"answer_scope_reproducibility_{audit_version}",
            "candidate_strategy": base.CANDIDATE_STRATEGY,
            "risk_answer_shape_fingerprint": RISK_ANSWER_SHAPE_FINGERPRINT,
            "gates": gates,
            "passed": all(gates.values()),
        }
    )
    return report


def run(
    first_path: Path = DEFAULT_R1,
    second_path: Path = DEFAULT_R2,
    output: Path | None = DEFAULT_OUTPUT,
    audit_version: str = "v14",
) -> dict[str, Any]:
    first = json.loads(first_path.read_text(encoding="utf-8"))
    second = json.loads(second_path.read_text(encoding="utf-8"))
    report = build_report(
        first, second, first_path, second_path, audit_version=audit_version
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--r1", type=Path, default=DEFAULT_R1)
    parser.add_argument("--r2", type=Path, default=DEFAULT_R2)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-version", default="v14")
    args = parser.parse_args(argv)
    report = run(args.r1, args.r2, args.output, args.audit_version)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
