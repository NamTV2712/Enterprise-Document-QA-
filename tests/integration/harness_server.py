"""Deterministic HTTP/SSE harness server for frontend integration tests.

Serves the REAL FastAPI application (routes, middleware, validation,
session memory, SSE transport) with the retrieval pipeline and provider
replaced by deterministic fixtures installed through the application
lifespan. Runs on loopback only. No Groq credentials, no corpus, no
real models are touched.

Optional env switches:
  HARNESS_PORT              port for the app (default 8765)
  HARSESS proxy port: PROXY_PORT  re-chunking TCP proxy port (default 8766)
  HARNESS_RATE_BURST        LLM_RATE_LIMIT_BURST override (default 2/minute)
  HARNESS_TRUSTED_PROXY     when "1", trusts loopback peers for X-Forwarded-For
  HARNESS_DECOMPOSED_TIMEOUT seconds (default 0.5)

Control endpoints (test-only, added by the harness, never by production
code):
  POST /__harness__/state {"pipeline_ready": bool}
  POST /__harness__/memory/reset          (simulate a backend restart)
  POST /__harness__/failure {"mode": ...} ("omit_done" | "error_after_token"
        | "decomposed_error" | "decomposed_slow" | "clear")

A re-chunking TCP proxy listens on PROXY_PORT and forwards to the app,
splitting every forwarded chunk at byte offsets that cut between SSE
events and through multi-byte UTF-8 sequences; the frontend must still
parse events correctly.

The app and proxy are never exposed beyond 127.0.0.1.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Every harness owns an isolated temporary directory.  If a caller does not
# provide one, create it outside the repository so diagnostics can never
# overwrite a developer's working-tree artifact.
_HARNESS_TEMP_DIR = Path(
    os.environ.get("HARNESS_TEMP_DIR")
    or tempfile.mkdtemp(prefix="enterprise-document-qa-harness-")
).resolve()
_HARNESS_TEMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HARNESS_TEMP_DIR"] = str(_HARNESS_TEMP_DIR)

# Harness settings must exist before configs.settings is imported.
os.environ.setdefault("GROQ_API_KEY", "harness-fake-key")
os.environ.setdefault("GROQ_API_KEY2", "harness-fake-key-2")
os.environ.setdefault("QDRANT_MODE", "local")
os.environ.setdefault("QDRANT_LOCAL_PATH", str(_HARNESS_TEMP_DIR / "qdrant"))
os.environ.setdefault("QDRANT_INDEX_MANIFEST_PATH", str(_HARNESS_TEMP_DIR / "index_manifest.json"))
os.environ.setdefault("EMBEDDING_MODEL_ID", "nomic-ai/nomic-embed-text-v1.5")
os.environ.setdefault("EMBEDDING_MODEL_REVISION", "harness-revision")
os.environ.setdefault(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:4173,http://127.0.0.1:4173,http://localhost:4175",
)
os.environ.setdefault("LLM_RATE_LIMIT_BURST", os.environ.get("HARNESS_RATE_BURST", "1000/minute"))
os.environ.setdefault("LLM_RATE_LIMIT_DAILY", "1000/day")
os.environ.setdefault("DECOMPOSED_RATE_LIMIT", "100/minute")
os.environ.setdefault("CACHE_TEST_RATE_LIMIT", "100/minute")
os.environ.setdefault("TRUSTED_PROXY_CIDRS", "127.0.0.1/32" if os.environ.get("HARNESS_TRUSTED_PROXY") == "1" else "")

APP_PORT = int(os.environ.get("HARNESS_PORT", "8765"))
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8766"))
DECOMPOSED_TIMEOUT = float(os.environ.get("HARNESS_DECOMPOSED_TIMEOUT", "0.5"))

failure_mode: dict[str, str] = {"mode": "clear"}

from fastapi import FastAPI  # noqa: E402  (harness settings first)

import src.api.app as app_module  # noqa: E402
from src.generation.generator import RAGResponse  # noqa: E402
from src.memory.conversation_memory import ConversationMemory  # noqa: E402
from src.retrieval.retriever import RetrievedChunk  # noqa: E402
from src.retrieval.semantic_cache import SemanticCache  # noqa: E402

SSE_TOKENS = ["Harness ", "answer with ", "évidence ", "for: "]  # é is multi-byte

HARNESS_DOCUMENT_CHUNKS = [
    {
        "chunk_id": "AAPL_harness_0000",
        "ticker": "AAPL",
        "section": "mdna",
        "filing_date": "2025-10-31",
        "report_date": "2025-09-27",
        "accession_number": "HARNESS",
        "chunk_index": 0,
        "score": 0.9,
        "text": "Harness indexed excerpt for AAPL.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/harness/aapl.htm",
    },
    {
        "chunk_id": "AAPL_harness_0001",
        "ticker": "AAPL",
        "section": "mdna",
        "filing_date": "2025-10-31",
        "report_date": "2025-09-27",
        "accession_number": "HARNESS",
        "chunk_index": 1,
        "score": 0.7,
        "text": "Harness neighboring indexed excerpt for AAPL.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/harness/aapl.htm",
    },
    {
        "chunk_id": "MSFT_harness_0000",
        "ticker": "MSFT",
        "section": "mdna",
        "filing_date": "2025-07-30",
        "report_date": "2025-06-30",
        "accession_number": "HARNESS",
        "chunk_index": 0,
        "score": 0.9,
        "text": "Harness indexed excerpt for MSFT.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/harness/msft.htm",
    },
    {
        "chunk_id": "MSFT_harness_0001",
        "ticker": "MSFT",
        "section": "mdna",
        "filing_date": "2025-07-30",
        "report_date": "2025-06-30",
        "accession_number": "HARNESS",
        "chunk_index": 1,
        "score": 0.7,
        "text": "Harness neighboring indexed excerpt for MSFT.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/harness/msft.htm",
    },
]


def _chunk(ticker: str | None) -> RetrievedChunk:
    selected_ticker = ticker or "AAPL"
    raw = next(
        (chunk for chunk in HARNESS_DOCUMENT_CHUNKS if chunk["ticker"] == selected_ticker and chunk["chunk_index"] == 0),
        HARNESS_DOCUMENT_CHUNKS[0],
    )
    return RetrievedChunk.from_raw(raw, score=0.9)


class FakeRetriever:
    def __init__(self) -> None:
        self._all_chunks = list(HARNESS_DOCUMENT_CHUNKS)

    def embed_query(self, query: str) -> list[float]:
        return [0.1] * 8

    def retrieve(self, query: str, top_k: int = 5, ticker: str | None = None, section: str | None = None):
        if failure_mode["mode"] == "decomposed_slow":
            import time

            time.sleep(1.2)
        return [_chunk(ticker)]

    def retrieve_with_embedding(self, query: str, query_embedding, top_k: int = 5, ticker=None, section=None):
        if failure_mode["mode"] == "decomposed_slow":
            import time

            time.sleep(1.2)
        return [_chunk(ticker)]


class FakeGenerator:
    model = "harness/gpt-fake"

    def _create_groq_chat_completion(self, _retry_limit: int | None = None, **kwargs: Any):
        messages = kwargs.get("messages", [])
        system = messages[0]["content"] if messages else ""
        if failure_mode["mode"] == "decomposed_error" and "synthesizing" in system.lower():
            raise RuntimeError("harness decomposed failure")
        if "decomposition" in system.lower() or "sub-queries" in system:
            plan = {
                "needs_decomposition": True,
                "sub_queries": [
                    {"query": "Apple cloud revenue", "ticker": "AAPL", "section": "mdna"},
                    {"query": "Microsoft cloud revenue", "ticker": "MSFT", "section": "mdna"},
                ],
            }
            content = json.dumps(plan)
        elif "synthesizing" in system.lower() or "comparative" in system.lower():
            content = "Apple and Microsoft both disclose cloud revenue growth [Source 1]."
        else:
            content = "Rewritten: standalone retrieval question."
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )

    def generate(self, query: str, chunks, conversation_history=None) -> RAGResponse:
        answer = f"Harness answer for: {query} [Source 1]."
        return RAGResponse(answer=answer, retrieved_chunks=chunks, model_used=self.model)

    def generate_stream(self, query: str, chunks, conversation_history=None, cancel_event=None):
        for token in SSE_TOKENS:
            if cancel_event is not None and cancel_event.is_set():
                return
            yield token
        if cancel_event is not None and cancel_event.is_set():
            return
        yield f"{query} [Source 1]."


class FakePipeline:
    def __init__(self) -> None:
        self.retriever = FakeRetriever()
        self.generator = FakeGenerator()
        self.memory = ConversationMemory()
        self.cache = SemanticCache()

    def _embed_query_once(self, question: str) -> list[float]:
        return [0.1] * 8

    def _retrieve_with_optional_embedding(self, question, query_embedding, top_k, ticker, section):
        return self.retriever.retrieve_with_embedding(query=question, query_embedding=query_embedding, top_k=top_k, ticker=ticker, section=section)

    def query(self, question: str, top_k: int = 5, ticker=None, section=None, session_id=None, answer_language="en"):
        chunks = self.retriever.retrieve_with_embedding(
            query=question, query_embedding=[0.1] * 8, top_k=top_k, ticker=ticker, section=section
        )
        if session_id:
            from src.memory.conversation_memory import Turn

            self.memory.add_turn(session_id, Turn(user_message=question, assistant_message=f"Harness answer for: {question} [Source 1]."))
        return RAGResponse(
            answer=f"Harness answer for: {question} [Source 1].",
            retrieved_chunks=chunks,
            model_used=self.generator.model,
            answer_language=answer_language,
        )

    def query_stream(self, question: str, top_k: int = 5, ticker=None, section=None,
                     conversation_history=None, session_id=None, cancel_event=None,
                     answer_language="en", request_id: str | None = None):
        request_id = request_id or "harness-request"
        sequence = 0

        def stage(stage_id: str, status: str, elapsed_ms: float | None = None, counters: dict[str, int] | None = None):
            nonlocal sequence
            sequence += 1
            payload: dict[str, Any] = {
                "version": 1,
                "request_id": request_id,
                "sequence": sequence,
                "stage_id": stage_id,
                "status": status,
            }
            if elapsed_ms is not None:
                payload["elapsed_ms"] = elapsed_ms
            if counters:
                payload["counters"] = counters
            return ("stage", payload)

        yield stage("query_preparation", "running")
        yield stage("query_preparation", "success", 1.1)
        chunks = self.retriever.retrieve_with_embedding(
            query=question, query_embedding=[0.1] * 8, top_k=top_k, ticker=ticker, section=section
        )
        yield stage("retrieval", "success", 8.4, {"source_count": len(chunks)})
        yield ("sources", self._sources(chunks))
        full = ""
        for token in self.generator.generate_stream(question, chunks, cancel_event=cancel_event):
            if cancel_event is not None and cancel_event.is_set():
                return
            full += token
            yield ("token", token)
        if cancel_event is not None and cancel_event.is_set():
            return
        if session_id:
            from src.memory.conversation_memory import Turn

            self.memory.add_turn(session_id, Turn(user_message=question, assistant_message=full))
        if failure_mode["mode"] != "omit_done":
            yield (
                "done",
                {
                    "request_id": request_id,
                    "request_status": "completed",
                    "execution": {
                        "request_id": request_id,
                        "elapsed_ms": 24.0,
                        "stages": [
                            {"name": "query_preparation", "elapsed_ms": 1.1, "status": "completed"},
                            {"name": "retrieval", "elapsed_ms": 8.4, "status": "completed"},
                        ],
                    },
                },
            )
        # "omit_done" ends the stream without a done event on purpose.

    @staticmethod
    def _sources(chunks):
        return [
            {
                "citation": c.citation,
                "score": round(c.score, 4),
                "text_preview": c.text[:200],
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "ticker": c.ticker,
                "filing_type": c.filing_type,
                "section": c.section,
                "filing_date": c.filing_date,
                "report_date": c.report_date,
                "chunk_index": c.chunk_index,
                "source_url": c.source_url,
                "rank": index + 1,
                "score_kind": c.score_kind,
                "text": c.text,
            }
            for index, c in enumerate(chunks)
        ]


@dataclass
class HarnessState:
    pipeline_ready: bool = True
    pipeline: Any = field(default_factory=FakePipeline)


harness = HarnessState()


def _install_harness_lifespan() -> None:
    """Replace the production lifespan with a deterministic one."""

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def harness_lifespan(_app: FastAPI):
        pipeline = FakePipeline()
        _state: dict[str, Any] = app_module._state
        _state.clear()
        _state["pipeline"] = pipeline if harness.pipeline_ready else None
        _state["decomposer"] = app_module.QueryDecomposer(pipeline=pipeline)
        _state["store"] = SimpleNamespace(close=lambda: None)
        searchable = {"AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA"}
        _state["corpus"] = {"searchable_company_count": len(searchable), "indexed_chunk_count": 42}
        _state["supported_tickers"] = sorted(searchable)
        yield
        _state.clear()

    app_module.app.router.lifespan_context = harness_lifespan


def _install_control_routes() -> None:
    control = FastAPI()

    @control.post("/state")
    async def set_state(payload: dict):  # noqa: ANN201
        harness.pipeline_ready = bool(payload.get("pipeline_ready", True))
        # Mutate the live application state: the lifespan only runs once.
        if payload.get("pipeline_ready"):
            if app_module._state.get("pipeline") is None and harness.pipeline is not None:
                app_module._state["pipeline"] = harness.pipeline
                app_module._state["decomposer"] = app_module.QueryDecomposer(
                    pipeline=harness.pipeline
                )
        else:
            app_module._state["pipeline"] = None
            app_module._state["decomposer"] = None
        return {"pipeline_ready": bool(app_module._state.get("pipeline"))}

    @control.post("/memory/reset")
    async def memory_reset():  # noqa: ANN201
        pipeline = app_module._state.get("pipeline")
        if pipeline is not None and hasattr(pipeline, "memory"):
            pipeline.memory._sessions.clear()
        return {"cleared": True}

    @control.post("/failure")
    async def set_failure(payload: dict):  # noqa: ANN201
        failure_mode["mode"] = payload.get("mode", "clear")
        return {"mode": failure_mode["mode"]}

    app_module.app.mount("/__harness__", control)


def run_app() -> None:
    import faulthandler

    _install_harness_lifespan()
    _install_control_routes()
    # Patch the decomposed timeout so a slow sub-query trips 504 quickly.
    app_module.DECOMPOSED_TIMEOUT_SECONDS = DECOMPOSED_TIMEOUT
    app_module.QUERY_TIMEOUT_SECONDS = 2.0

    # Debug aid: periodically dump all thread stacks so a hang can be
    # attributed to the exact awaiting frame.
    stack_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f"harness_stacks-{APP_PORT}-",
        suffix=".txt",
        dir=_HARNESS_TEMP_DIR,
        delete=False,
    )
    faulthandler.dump_traceback_later(15, repeat=True, file=stack_file)

    import uvicorn

    # proxy_headers=False: only the application's TRUSTED_PROXY_CIDRS layer
    # may interpret X-Forwarded-For (mirrors the release Dockerfile).
    uvicorn.run(
        app_module.app,
        host="127.0.0.1",
        port=APP_PORT,
        log_level="warning",
        proxy_headers=False,
        access_log=False,
    )


# --- Re-chunking TCP proxy -------------------------------------------------

async def _pump(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, split_bytes: bool) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            if split_bytes and len(data) > 3:
                # Forward one byte at a time: guaranteed to cut between SSE
                # events, mid-JSON, and through multi-byte UTF-8 sequences.
                for byte in data:
                    writer.write(bytes([byte]))
                    await writer.drain()
            else:
                writer.write(data)
                await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def _handle_proxy(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection("127.0.0.1", APP_PORT)
    except ConnectionError:
        client_writer.close()
        return
    to_upstream = asyncio.create_task(_pump(client_reader, upstream_writer, split_bytes=False))
    to_client = asyncio.create_task(_pump(upstream_reader, client_writer, split_bytes=True))
    await asyncio.gather(to_upstream, to_client, return_exceptions=True)


async def run_proxy() -> None:
    server = await asyncio.start_server(_handle_proxy, "127.0.0.1", PROXY_PORT)
    async with server:
        await server.serve_forever()


def main() -> int:
    import threading

    for port in (APP_PORT, PROXY_PORT):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"harness port {port} is already occupied; refusing to reuse it") from exc

    proxy_thread = threading.Thread(target=lambda: asyncio.run(run_proxy()), daemon=True)
    proxy_thread.start()
    print(f"HARNESS_READY app=127.0.0.1:{APP_PORT} proxy=127.0.0.1:{PROXY_PORT}", flush=True)
    run_app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
