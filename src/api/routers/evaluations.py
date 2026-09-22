"""Validated public evaluation report routes."""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from configs.settings import settings
from src.evaluation.public_report import get_public_report, list_public_reports


def create_evaluation_router() -> APIRouter:
    router = APIRouter()

    @router.get("/evaluation/runs")
    async def evaluation_runs(
        status: Literal["official", "candidate", "historical", "incomplete"] | None = None,
        language: Literal["en", "vi"] | None = None,
        intent: str | None = Query(default=None, max_length=80),
        ticker: str | None = Query(default=None, pattern=r"^[A-Z]{1,5}(-[A-Z])?$"),
        gate: str | None = Query(default=None, max_length=80),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ) -> dict:
        """List validated, explicitly published evaluation summaries only."""
        reports = list_public_reports(root=settings.data_public_evaluations_dir)
        filtered: list[dict[str, Any]] = []
        for summary in reports:
            if status is not None and summary["status"] != status:
                continue
            if language is None and intent is None and ticker is None and gate is None:
                filtered.append(summary)
                continue
            detail = get_public_report(
                summary["run_id"], root=settings.data_public_evaluations_dir
            )
            if detail is None:
                continue
            cases = detail["cases"]
            if language is not None and not any(
                case["language"] == language for case in cases
            ):
                continue
            if intent is not None and not any(
                case.get("intent") == intent for case in cases
            ):
                continue
            if ticker is not None and not any(
                case.get("ticker") == ticker for case in cases
            ):
                continue
            if gate is not None and not any(
                case.get("gates", {}).get(gate) is True for case in cases
            ):
                continue
            filtered.append(summary)
        start = (page - 1) * page_size
        return {
            "items": filtered[start : start + page_size],
            "total": len(filtered),
            "page": page,
            "page_size": page_size,
        }

    @router.get("/evaluation/runs/{run_id}")
    async def evaluation_run(run_id: str) -> dict:
        """Return one validated public report; arbitrary filesystem paths are impossible."""
        report = get_public_report(run_id, root=settings.data_public_evaluations_dir)
        if report is None:
            raise HTTPException(status_code=404, detail="Evaluation run not found")
        return report

    return router
