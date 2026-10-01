"""Deterministic closed-world registry and validation boundary."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Literal

from pydantic import BaseModel, ValidationError

from src.agent.errors import AgentToolError
from src.agent.models import (
    AskRagInput, DocumentObservation, InspectRetrievalInput, ReadDocumentInput,
    RetrievalObservation, SearchDocumentsInput, ToolObservation,
)
from src.agent.policies import AgentExecutionContext
from src.agent.tools import ToolServices, ask_rag, inspect_retrieval, read_document, search_documents
from src.api.schemas import DiscoverySnapshotResponse, QueryResponse


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    access: Literal["public_corpus", "private_workspace"]
    side_effect: Literal["none", "ephemeral_snapshot", "provider_cache"]
    provider_execution: bool
    execute: Callable[[BaseModel], Any]

    def schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()


class AgentToolRegistry:
    def __init__(self, tools: tuple[AgentTool, ...]):
        names = [tool.name for tool in tools]
        if len(names) != len(set(names)):
            raise ValueError("duplicate Agent tool name")
        self._tools = {tool.name: tool for tool in tools}

    def list(self) -> tuple[AgentTool, ...]:
        return tuple(self._tools.values())

    def get(self, name: str) -> AgentTool:
        if not isinstance(name, str):
            raise AgentToolError("unknown_tool")
        try:
            return self._tools[name]
        except KeyError as error:
            raise AgentToolError("unknown_tool") from error

    async def invoke(
        self, name: str, arguments: dict[str, Any], context: AgentExecutionContext,
    ) -> ToolObservation:
        tool = self.get(name)
        if name not in context.policy.allowed_tools:
            raise AgentToolError("tool_not_allowed")
        if tool.provider_execution and not context.policy.allow_provider_execution:
            raise AgentToolError("provider_required")
        try:
            body = tool.input_model.model_validate(arguments)
        except (ValidationError, TypeError, ValueError) as error:
            raise AgentToolError("invalid_arguments") from error
        try:
            # Discovery/catalog work is synchronous. Keep it off the application
            # event loop; each worker awaits its one admitted call before another.
            result = await asyncio.to_thread(tool.execute, body)
            if inspect.isawaitable(result):
                result = await result
            data = tool.output_model.model_validate(result)
        except AgentToolError:
            raise
        except (ValidationError, ValueError) as error:
            raise AgentToolError("execution_failed") from error
        except Exception as error:
            # Exception text can contain provider credentials or filing content.
            raise AgentToolError("execution_failed") from error
        return ToolObservation(tool_name=name, data=data)


def build_tool_registry(services: ToolServices) -> AgentToolRegistry:
    """Only these four application-constructed callables can be selected."""
    return AgentToolRegistry((
        AgentTool("search_documents", "Search indexed filing chunks with BM25 discovery.",
                  SearchDocumentsInput, DiscoverySnapshotResponse, "public_corpus", "ephemeral_snapshot", False,
                  lambda body: search_documents(services, body)),
        AgentTool("inspect_retrieval", "Inspect provider-free retrieval stages and score families.",
                  InspectRetrievalInput, RetrievalObservation, "public_corpus", "none", False,
                  lambda body: inspect_retrieval(services, body)),
        AgentTool("read_document", "Read canonical document metadata and bounded indexed chunk previews.",
                  ReadDocumentInput, DocumentObservation, "public_corpus", "none", False,
                  lambda body: read_document(services, body)),
        AgentTool("ask_rag", "Run the existing grounded RAG query with a configured generator.",
                  AskRagInput, QueryResponse, "public_corpus", "provider_cache", True,
                  lambda body: ask_rag(services, body)),
    ))
