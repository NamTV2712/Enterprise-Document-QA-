"""Validated public evaluation report routes."""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from configs.settings import settings
from src.api.evaluation_models import (
    EvaluationMetricsResponse,
    NativeCompareRequestModel,
    NativeCompareResponseModel,
    NativeFailuresResponseModel,
    NativePublishedDetailModel,
    NativePublishedSummaryModel,
    NativeResultsPageModel,
    NativeTrendsResponseModel,
)
from src.evaluation.native_analysis import (
    IncompatibleNativeReports,
    UnknownNativeMetric,
    compare_native_reports,
    native_failures,
    native_trends,
)
from src.evaluation.native_protocol import (
    METRIC_DEFINITIONS,
    NATIVE_CAPABILITIES,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
)
from src.evaluation.native_publication import (
    InvalidPublishedRunId,
    NativePublicationError,
    PublishedNativeReport,
    get_published_native_report,
    list_published_native_reports,
)
from src.evaluation.public_report import get_public_report, list_public_reports
from src.retrieval.canonical_json import canonical_json_bytes


def _json(value: Any) -> Any:
    return json.loads(canonical_json_bytes(asdict(value)))


def _native(run_id: str) -> PublishedNativeReport:
    try:
        published = get_published_native_report(run_id, root=settings.data_public_evaluations_dir)
    except InvalidPublishedRunId as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except NativePublicationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if published is not None:
        return published
    if get_public_report(run_id, root=settings.data_public_evaluations_dir) is not None:
        raise HTTPException(status_code=409, detail="Native evaluation report required")
    raise HTTPException(status_code=404, detail="Evaluation run not found")


def _native_history() -> tuple[PublishedNativeReport, ...]:
    try:
        return list_published_native_reports(root=settings.data_public_evaluations_dir)
    except NativePublicationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _page(items: list[Any], page: int, page_size: int) -> list[Any]:
    start = (page - 1) * page_size
    return items[start:start + page_size]


def _query_keys(request: Request, allowed: set[str]) -> None:
    if set(request.query_params) - allowed:
        raise HTTPException(status_code=422, detail="Unsupported evaluation query parameter")


def create_evaluation_router() -> APIRouter:
    router = APIRouter()

    @router.get("/evaluation/metrics", response_model=EvaluationMetricsResponse)
    async def evaluation_metrics() -> EvaluationMetricsResponse:
        """Expose native identities and meanings without executing a provider."""
        return EvaluationMetricsResponse(
            protocol=PROTOCOL_NAME,
            protocol_version=PROTOCOL_VERSION,
            capabilities=asdict(NATIVE_CAPABILITIES),
            items=[
                asdict(definition) | {"required_inputs": list(definition.required_inputs)}
                for definition in METRIC_DEFINITIONS
            ],
            total=len(METRIC_DEFINITIONS),
        )

    @router.get("/evaluation/metrics/trends", response_model=NativeTrendsResponseModel)
    async def evaluation_metric_trends(
        request: Request,
        metric_id: str = Query(max_length=80),
        binding_group: str | None = Query(default=None, pattern=r"^sha256:[0-9a-f]{64}$"),
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        sort: Literal["published_at_asc"] = "published_at_asc",
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=100),
    ) -> NativeTrendsResponseModel:
        _query_keys(request, {"metric_id", "binding_group", "start_at", "end_at", "sort", "page", "page_size"})
        if any(value is not None and (value.tzinfo is None or value.utcoffset() is None) for value in (start_at, end_at)):
            raise HTTPException(status_code=422, detail="Trend range needs timezone-aware timestamps")
        if start_at and end_at and start_at > end_at:
            raise HTTPException(status_code=422, detail="Trend range is reversed")
        history = tuple(item for item in _native_history() if
            (start_at is None or item.published_at >= start_at) and
            (end_at is None or item.published_at <= end_at))
        try:
            groups = native_trends(history, metric_id)
        except UnknownNativeMetric as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if binding_group is not None:
            groups = tuple(group for group in groups if group.binding_group == binding_group)
        total = sum(len(group.points) for group in groups)
        first, last = (page - 1) * page_size, page * page_size
        position = 0
        paged_groups = []
        for group in groups:
            selected = group.points[max(0, first - position):max(0, last - position)]
            position += len(group.points)
            if selected:
                paged_groups.append({**_json(group), "points": [_json(point) for point in selected]})
        return NativeTrendsResponseModel.model_validate({
            "metric_id": metric_id, "groups": paged_groups, "total_points": total,
            "page": page, "page_size": page_size,
        })

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
        native_history = _native_history()
        if {item["run_id"] for item in reports} & {item.report.run_id for item in native_history}:
            raise HTTPException(status_code=409, detail="Ambiguous published run ID")
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
        if language is None and intent is None and ticker is None and gate is None:
            for item in native_history:
                report = item.report
                if status is not None and status != report.status:
                    continue
                filtered.append(NativePublishedSummaryModel.model_validate({
                    "protocol": report.protocol,
                    "protocol_version": report.protocol_version,
                    "run_id": report.run_id,
                    "status": report.status,
                    "published_at": item.published_at.isoformat(),
                    "report_digest": report.digest,
                    "case_count": len(report.cases),
                    "binding": _json(report.binding),
                    "aggregates": [_json(aggregate) for aggregate in report.aggregates],
                }).model_dump(mode="json"))
        filtered.sort(key=lambda item: item["run_id"])
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
        try:
            published = get_published_native_report(run_id, root=settings.data_public_evaluations_dir)
        except InvalidPublishedRunId as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except NativePublicationError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if published is not None:
            if get_public_report(run_id, root=settings.data_public_evaluations_dir) is not None:
                raise HTTPException(status_code=409, detail="Ambiguous published run ID")
            report = published.report
            return NativePublishedDetailModel.model_validate({
                "schema_version": 1,
                "published_at": published.published_at.isoformat(),
                "protocol": report.protocol,
                "protocol_version": report.protocol_version,
                "run_id": report.run_id,
                "status": report.status,
                "report_digest": report.digest,
                "case_count": len(report.cases),
                "binding": _json(report.binding),
                "metric_definitions": [_json(item) for item in report.metric_definitions],
                "aggregates": [_json(item) for item in report.aggregates],
            }).model_dump(mode="json")
        report = get_public_report(run_id, root=settings.data_public_evaluations_dir)
        if report is None:
            raise HTTPException(status_code=404, detail="Evaluation run not found")
        return report

    @router.get("/evaluation/runs/{run_id}/results", response_model=NativeResultsPageModel)
    async def evaluation_run_results(
        request: Request,
        run_id: str,
        case_id: str | None = Query(default=None, max_length=128),
        sort: Literal["case_id_asc"] = "case_id_asc",
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=100),
    ) -> NativeResultsPageModel:
        _query_keys(request, {"case_id", "sort", "page", "page_size"})
        report = _native(run_id).report
        cases = [item for item in report.cases if case_id is None or item.case_id == case_id]
        return NativeResultsPageModel.model_validate({
            "run_id": report.run_id,
            "report_digest": report.digest,
            "report_status": report.status,
            "metric_definitions": [_json(item) for item in report.metric_definitions],
            "aggregates": [_json(item) for item in report.aggregates],
            "items": [_json(item) for item in _page(cases, page, page_size)],
            "total": len(cases), "page": page, "page_size": page_size,
        })

    @router.post("/evaluation/compare", response_model=NativeCompareResponseModel)
    async def evaluation_compare(request: NativeCompareRequestModel) -> NativeCompareResponseModel:
        baseline = _native(request.baseline_run_id).report
        candidate = _native(request.candidate_run_id).report
        try:
            comparison = compare_native_reports(baseline, candidate, request.metric_ids)
        except UnknownNativeMetric as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except IncompatibleNativeReports as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        payload = _json(comparison)
        payload["total_cases"] = len(comparison.cases)
        payload["cases"] = [_json(item) for item in _page(list(comparison.cases), request.page, request.page_size)]
        payload["page"] = request.page
        payload["page_size"] = request.page_size
        return NativeCompareResponseModel.model_validate(payload)

    @router.get("/evaluation/failures", response_model=NativeFailuresResponseModel)
    async def evaluation_failures(
        request: Request,
        run_id: str = Query(max_length=128),
        category: Literal[
            "fallback_expectation_mismatch", "invalid_citation_index",
            "missing_required_keyword", "unavailable_prerequisite",
        ] | None = None,
        sort: Literal["category_case_metric_asc"] = "category_case_metric_asc",
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=100),
    ) -> NativeFailuresResponseModel:
        _query_keys(request, {"run_id", "category", "sort", "page", "page_size"})
        analysis = native_failures(_native(run_id).report)
        findings = [item for item in analysis.findings if category is None or item.category_id == category]
        return NativeFailuresResponseModel.model_validate({
            "run_id": analysis.run_id,
            "report_digest": analysis.report_digest,
            "report_status": analysis.report_status,
            "category_counts": [{"category_id": name, "count": count} for name, count in analysis.category_counts],
            "items": [_json(item) for item in _page(findings, page, page_size)],
            "total": len(findings), "page": page, "page_size": page_size,
        })

    return router
