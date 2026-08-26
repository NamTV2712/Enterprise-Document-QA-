"""Single-call diagnostic: what does the gpt-oss planner produce?

Exactly one LLM call to the production QueryDecomposer planner for the
AAPL-vs-AMZN FY2024 revenue comparison. Compares the planned subquery
wording against the counterfactual winner ("Amazon consolidated net
sales").

This is a DIAGNOSTIC; it freezes nothing.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

from configs.settings import settings
from src.generation.generator import Generator
from src.generation.query_decomposer import QueryDecomposer

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TARGET_QUESTION = (
    "Which company, Apple or Amazon, had higher total revenue in fiscal year 2024?"
)
COUNTERFACTUAL_WINNER = "Amazon consolidated net sales"
PLANNER_MODEL = "openai/gpt-oss-120b"
OUTPUT_PATH = Path("data/diagnostics/planner_wording_check.json")


def main() -> int:
    generation_keys = [
        settings.groq_api_key_fall_back,
        settings.groq_api_key_fall_back2,
    ]
    if not any(generation_keys):
        generation_keys = [settings.groq_api_key, settings.groq_api_key2]

    generator = Generator(model=PLANNER_MODEL, api_keys=generation_keys)
    # _plan only touches pipeline.generator; retrieval never runs here.
    decomposer = QueryDecomposer(
        pipeline=SimpleNamespace(generator=generator, retriever=None)
    )

    plan = decomposer._plan(TARGET_QUESTION)
    sub_queries = plan.get("sub_queries", [])
    print("\n=== Planner output ===")
    print(json.dumps(plan, indent=2, ensure_ascii=False))

    amzn_queries = [
        sq.get("query", "")
        for sq in sub_queries
        if sq.get("ticker") == "AMZN"
    ]
    matches_counterfactual = any(
        "consolidated" in q.lower() and "net sales" in q.lower()
        or "net sales" in q.lower()
        for q in amzn_queries
    )
    bare_total_revenue = any(
        q.strip().lower() == "amazon total revenue" for q in amzn_queries
    )

    verdict = "matches_counterfactual" if matches_counterfactual else (
        "planner_gap_bare_total_revenue" if bare_total_revenue
        else "planner_other_wording"
    )
    print(f"\nAMZN subqueries : {amzn_queries}")
    print(f"Verdict         : {verdict}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "diagnostic": True,
                "official": False,
                "question": TARGET_QUESTION,
                "model": PLANNER_MODEL,
                "plan": plan,
                "amzn_subqueries": amzn_queries,
                "counterfactual_winner": COUNTERFACTUAL_WINNER,
                "verdict": verdict,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    logger.info("Diagnostic written: %s", OUTPUT_PATH)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
