"""Adapters over existing product services, with no HTTP self-calls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from fastapi import HTTPException
from src.agent.errors import AgentToolError
from src.agent.models import (
    AskRagInput, DocumentObservation, InspectRetrievalInput, ReadDocumentInput,
    RetrievalObservation, SearchDocumentsInput,
)
from src.api.discovery import DiscoveryError, DiscoveryService
from src.api.schemas import DiscoverySnapshotResponse, QueryResponse


class ToolServices:
    """Explicit application-owned dependencies; no import or URL comes from a model."""

    def __init__(
        self,
        *,
        discovery: Callable[[], DiscoveryService],
        inspect: Callable[[InspectRetrievalInput], Awaitable[dict[str, Any]]],
        catalog: Callable[[], Sequence[dict[str, Any]]],
        document_chunks: Callable[[], dict[str, list[dict[str, Any]]]],
        rag_query: Callable[[AskRagInput], Awaitable[QueryResponse]],
    ) -> None:
        self.discovery = discovery
        self.inspect = inspect
        self.catalog = catalog
        self.document_chunks = document_chunks
        self.rag_query = rag_query


def search_documents(services: ToolServices, body: SearchDocumentsInput) -> DiscoverySnapshotResponse:
    try:
        snapshot = services.discovery().search(**body.model_dump())
    except DiscoveryError as error:
        raise AgentToolError("invalid_arguments") from error
    except HTTPException as error:
        raise AgentToolError("unavailable" if error.status_code == 503 else "execution_failed") from error
    return DiscoverySnapshotResponse.model_validate(snapshot.as_payload(body.page, body.page_size))


async def inspect_retrieval(services: ToolServices, body: InspectRetrievalInput) -> RetrievalObservation:
    try:
        return RetrievalObservation.model_validate(await services.inspect(body))
    except ValueError as error:
        raise AgentToolError("invalid_arguments") from error
    except HTTPException as error:
        raise AgentToolError("unavailable" if error.status_code == 503 else "execution_failed") from error


def read_document(services: ToolServices, body: ReadDocumentInput) -> DocumentObservation:
    try:
        rows = services.catalog()
    except HTTPException as error:
        raise AgentToolError("unavailable" if error.status_code == 503 else "execution_failed") from error
    row = next((item for item in rows if item["document_id"] == body.document_id), None)
    if row is None:
        raise AgentToolError("unavailable")
    chunks = services.document_chunks().get(body.document_id, [])
    start = (body.page - 1) * body.page_size
    return DocumentObservation.model_validate({
        "document_id": body.document_id,
        "ticker": row.get("ticker"),
        "filing_date": row.get("filing_date"),
        "report_date": row.get("report_date"),
        "sections": row.get("sections") or [],
        "chunk_count": row.get("chunk_count", len(chunks)),
        "items": [
            {
                "chunk_id": chunk.get("chunk_id"),
                "section": chunk.get("section"),
                "text_preview": str(chunk.get("text") or "")[:500],
                "text_length": len(str(chunk.get("text") or "")),
            }
            for chunk in chunks[start : start + body.page_size]
        ],
        "total": len(chunks),
        "page": body.page,
        "page_size": body.page_size,
    })


async def ask_rag(services: ToolServices, body: AskRagInput) -> QueryResponse:
    try:
        return await services.rag_query(body)
    except ValueError as error:
        raise AgentToolError("invalid_arguments") from error
    except HTTPException as error:
        raise AgentToolError("unavailable" if error.status_code == 503 else "execution_failed") from error
