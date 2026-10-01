"""Opt-in ASGI timing through the final body send, including finite Agent SSE."""
from __future__ import annotations

import asyncio
import logging
import time

from src.workspace.attribution import AGENT_ROUTES, capture, span

logger = logging.getLogger(__name__)


class PerformanceMiddleware:
    def __init__(self, app, *, enabled, sink):
        self.app, self.enabled, self.sink = app, enabled, sink

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.enabled() or not scope.get("path", "").startswith("/agent/runs"):
            return await self.app(scope, receive, send)
        status, streaming, ended = 500, False, None

        async def observed_send(message):
            nonlocal status, streaming, ended
            if message["type"] == "http.response.start":
                status = message["status"]
                streaming = any(key == b"content-type" and value.startswith(b"text/event-stream")
                                for key, value in message.get("headers", ()))
            if streaming and message["type"] == "http.response.body":
                with span("sse.send"):
                    await send(message)
            else:
                await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                ended = time.perf_counter_ns()

        try:
            with capture("api") as trace:
                with span("api.total") as root:
                    try:
                        await self.app(scope, receive, observed_send)
                    finally:
                        if ended is not None:
                            root["end_ns"] = ended
                            root["outcome"] = "rejected" if 400 <= status < 500 else "failed" if status >= 500 else "completed"
        finally:
            route = getattr(scope.get("route"), "path", None)
            correlation = scope.get("state", {}).get("request_id")
            if route in AGENT_ROUTES and correlation is not None and scope.get("state", {}).get("performance_workspace_authorized", False):
                try:
                    await self.sink(trace, correlation_id=correlation, route_template=route)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.warning("performance_telemetry_write_failed")
