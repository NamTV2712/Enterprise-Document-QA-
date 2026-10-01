"""OBS-001 bounded, content-free monotonic attribution; no independent store."""
from __future__ import annotations

import asyncio
import functools
import inspect
import itertools
import math
import time
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROTOCOL = "obs-001-attribution-v1"
PHASES = frozenset({
    "api.total", "api.access", "api.validation", "api.freeze", "api.admission",
    "api.read", "api.service_init", "workspace.serialized_wait", "workspace.connection_open",
    "workspace.transaction", "workspace.read", "workspace.initialize", "workspace.critical_section",
    "worker.cycle", "worker.claim", "worker.poll_wait", "worker.service", "worker.queue_wait",
    "agent.decision", "agent.provider", "agent.tool.search_documents", "agent.tool.inspect_retrieval",
    "agent.tool.read_document", "agent.tool.ask_rag", "agent.persist_result", "retrieval.search",
    "retrieval.inspect", "generator.transport", "evaluation.compute", "sse.read_events",
    "sse.serialize", "sse.send",
})
OPERATIONS = frozenset({"none", "job_create", "job_claim", "job_transition", "job_step",
    "job_read", "job_list", "job_event_read", "job_event_append", "job_cancel", "job_recover"})
OUTCOMES = frozenset({"completed", "rejected", "failed", "cancelled"})
MAX_API_SPANS = 128
MAX_RUN_SPANS = 512
MAX_GROUPS = 64
MAX_DURATION_MS = 86_400_000
MAX_SUMMARY_BYTES = 16384
AGENT_ROUTES = frozenset({"/agent/runs", "/agent/runs/{run_id}", "/agent/runs/{run_id}/results",
    "/agent/runs/{run_id}/evaluation", "/agent/runs/{run_id}/events", "/agent/runs/{run_id}/cancel"})


def statistics(values, *, signed=False):
    """Nearest rank, with the SCALE-002 minimum populations; no finite coercion."""
    samples = sorted(values)
    if any(type(value) not in (int, float) or not math.isfinite(value) or not signed and value < 0 for value in samples):
        raise ValueError("invalid performance sample")
    result = {"count": len(samples), "max": max(samples) if samples else None}
    for name, quantile, minimum in (("p50", .50, 2), ("p95", .95, 20), ("p99", .99, 100)):
        result[name] = samples[math.ceil(quantile * len(samples)) - 1] if len(samples) >= minimum else None
    return result


def aggregate_summaries(summaries, *, truncated=False):
    """Per-terminal phase total populations; nested phase totals are inclusive."""
    groups = {}
    for summary in summaries:
        for phase in summary.phases:
            key = (summary.source, phase.phase, phase.operation)
            values, outcomes, count = groups.setdefault(key, ([], Counter(), []))
            values.append(phase.total_ms)
            count.append(phase.count)
            outcomes.update({name: getattr(phase, name) for name in OUTCOMES})
    return {"protocol": PROTOCOL, "terminal_count": len(summaries), "truncated": truncated,
            "dropped_spans": sum(summary.dropped for summary in summaries),
            "population": "inclusive_phase_total_per_terminal",
            "phases": [{"source": source, "phase": phase, "operation": operation,
                        "invocations": sum(count), "duration_ms": statistics(values), "outcomes": dict(outcomes)}
                       for (source, phase, operation), (values, outcomes, count) in sorted(groups.items())]}


class SafeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class TimingSpan(SafeModel):
    phase: str
    operation: str = "none"
    outcome: Literal["completed", "rejected", "failed", "cancelled"] = "completed"
    ordinal: int = Field(ge=1, le=1_000_000)
    parent: int | None = Field(default=None, ge=1, le=1_000_000)
    start_ns: int = Field(ge=0, le=9_223_372_036_854_775_807)
    end_ns: int = Field(ge=0, le=9_223_372_036_854_775_807)

    @field_validator("phase")
    @classmethod
    def phase_allowlist(cls, value):
        if value not in PHASES:
            raise ValueError("unsupported attribution phase")
        return value

    @field_validator("operation")
    @classmethod
    def operation_allowlist(cls, value):
        if value not in OPERATIONS:
            raise ValueError("unsupported attribution operation")
        return value

    @model_validator(mode="after")
    def monotonic(self):
        if self.end_ns < self.start_ns or self.duration_ms > MAX_DURATION_MS:
            raise ValueError("invalid monotonic interval")
        if self.parent is not None and self.parent >= self.ordinal:
            raise ValueError("invalid span parent")
        return self

    @property
    def duration_ms(self):
        return (self.end_ns - self.start_ns) / 1_000_000


class PhaseSummary(SafeModel):
    phase: str
    operation: str
    count: int = Field(ge=1, le=MAX_RUN_SPANS)
    total_ms: float = Field(ge=0, le=MAX_RUN_SPANS * MAX_DURATION_MS, allow_inf_nan=False)
    max_ms: float = Field(ge=0, le=MAX_DURATION_MS, allow_inf_nan=False)
    completed: int = Field(ge=0, le=MAX_RUN_SPANS)
    rejected: int = Field(ge=0, le=MAX_RUN_SPANS)
    failed: int = Field(ge=0, le=MAX_RUN_SPANS)
    cancelled: int = Field(ge=0, le=MAX_RUN_SPANS)

    @model_validator(mode="after")
    def allowlist(self):
        if self.phase not in PHASES or self.operation not in OPERATIONS:
            raise ValueError("unsupported attribution classification")
        if self.completed + self.rejected + self.failed + self.cancelled != self.count:
            raise ValueError("invalid attribution outcome count")
        if self.max_ms > self.total_ms:
            raise ValueError("invalid attribution aggregate")
        return self


class TimingSummary(SafeModel):
    protocol: Literal["obs-001-attribution-v1"] = PROTOCOL
    source: Literal["api", "worker"]
    span_count: int = Field(ge=0, le=MAX_RUN_SPANS)
    dropped: int = Field(ge=0, le=1_000_000)
    remainder_ms: float | None = Field(default=None, ge=0, le=MAX_DURATION_MS, allow_inf_nan=False)
    phases: tuple[PhaseSummary, ...] = Field(max_length=MAX_GROUPS)

    @model_validator(mode="after")
    def bounded(self):
        if self.source == "api" and self.span_count > MAX_API_SPANS:
            raise ValueError("API span budget exceeded")
        keys = [(phase.phase, phase.operation) for phase in self.phases]
        if len(set(keys)) != len(keys) or sum(phase.count for phase in self.phases) != self.span_count:
            raise ValueError("invalid attribution group count")
        if len(self.model_dump_json().encode("utf-8")) > MAX_SUMMARY_BYTES:
            raise ValueError("attribution summary byte bound exceeded")
        return self


_current: ContextVar[Trace | None] = ContextVar("performance_trace", default=None)
_parent: ContextVar[int | None] = ContextVar("performance_parent", default=None)
_operation: ContextVar[str] = ContextVar("performance_operation", default="none")
# Defer DB observations until the outer serialized boundary releases its lock.
_deferred: ContextVar[dict | None] = ContextVar("performance_db_deferred", default=None)


class Trace:
    def __init__(self, source: Literal["api", "worker"], *, clock=None):
        if source not in ("api", "worker"):
            raise ValueError("unsupported attribution source")
        self.source = source
        self.clock = clock or time.perf_counter_ns
        self.limit = MAX_API_SPANS if source == "api" else MAX_RUN_SPANS
        self._ids = itertools.count(1)
        self._lock = Lock()
        self.records: list[TimingSpan] = []
        self.groups: set[tuple[str, str]] = set()
        self.dropped = 0
        self.closed = False

    def record(self, phase, start_ns, end_ns, *, outcome="completed", ordinal=None, parent=None,
               operation=None):
        value = TimingSpan(phase=phase, start_ns=start_ns, end_ns=end_ns, outcome=outcome,
            ordinal=ordinal or min(next(self._ids), 1_000_000), parent=parent,
            operation=_operation.get() if operation is None else operation)
        with self._lock:
            if self.closed:
                return
            key = (value.phase, value.operation)
            root = value.phase in ("api.total", "worker.cycle")
            if len(self.records) >= self.limit and root:
                self.records.pop()
                self.dropped = min(self.dropped + 1, 1_000_000)
            group_limit = MAX_GROUPS if root else MAX_GROUPS - 1
            if len(self.records) >= self.limit or key not in self.groups and len(self.groups) >= group_limit:
                self.dropped = min(self.dropped + 1, 1_000_000)
                return
            self.groups.add(key)
            self.records.append(value)

    def summary(self):
        with self._lock:
            records, dropped = tuple(self.records), self.dropped
        grouped = {}
        for value in records:
            grouped.setdefault((value.phase, value.operation), []).append(value)
        phases = []
        for (phase, operation), values in sorted(grouped.items()):
            outcomes = Counter(value.outcome for value in values)
            phases.append(PhaseSummary(phase=phase, operation=operation, count=len(values),
                total_ms=float(sum(value.duration_ms for value in values)),
                max_ms=float(max(value.duration_ms for value in values)),
                **{key: outcomes[key] for key in OUTCOMES}))
        remainder = None
        roots = [item for item in records if item.phase == "api.total"]
        if self.source == "api" and not dropped and len(roots) == 1:
            root = roots[0]
            intervals = sorted((max(item.start_ns, root.start_ns), min(item.end_ns, root.end_ns))
                for item in records if item is not root and item.end_ns > root.start_ns
                and item.start_ns < root.end_ns)
            covered, endpoint = 0, root.start_ns
            for start, end in intervals:
                covered += max(0, end - max(endpoint, start))
                endpoint = max(endpoint, end)
            remainder = float((root.end_ns - root.start_ns - covered) / 1_000_000)
        return TimingSummary(source=self.source, span_count=len(records), dropped=dropped,
                             remainder_ms=remainder, phases=tuple(phases))


@contextmanager
def capture(source, *, clock=None):
    trace = Trace(source, clock=clock)
    token, parent = _current.set(trace), _parent.set(None)
    try:
        yield trace
    finally:
        with trace._lock:
            trace.closed = True
        _parent.reset(parent)
        _current.reset(token)


def record_interval(phase, start_ns, end_ns, *, outcome="completed"):
    trace = _current.get()
    if trace is None:
        return
    entry = (trace, phase, start_ns, end_ns, outcome, _parent.get(), _operation.get(), None)
    pending = _deferred.get()
    if pending is not None:
        _defer(entry, pending)
    else:
        trace.record(phase, start_ns, end_ns, outcome=outcome, parent=_parent.get())


@contextmanager
def defer_database_observations():
    if _current.get() is None or _deferred.get() is not None:
        yield
        return
    pending = {"entries": [], "dropped": 0, "limit": _current.get().limit}
    token = _deferred.set(pending)
    try:
        yield
    finally:
        _deferred.reset(token)
        trace = _current.get()
        with trace._lock:
            trace.dropped = min(1_000_000, trace.dropped + pending["dropped"])
        for trace, phase, start, end, outcome, parent, operation, ordinal in pending["entries"]:
            trace.record(phase, start, end, outcome=outcome, parent=parent,
                         operation=operation, ordinal=ordinal)


def _defer(entry, pending):
    if len(pending["entries"]) < pending["limit"]:
        pending["entries"].append(entry)
    else:
        pending["dropped"] = min(1_000_000, pending["dropped"] + 1)


@contextmanager
def span(phase):
    if phase not in PHASES:
        raise ValueError("unsupported attribution phase")
    trace = _current.get()
    if trace is None:
        yield None
        return
    started, ordinal, parent = trace.clock(), min(next(trace._ids), 1_000_000), _parent.get()
    token = _parent.set(ordinal)
    outcome = "completed"
    override = {}
    try:
        yield override
    except BaseException as error:
        outcome = ("cancelled" if isinstance(error, asyncio.CancelledError) else
                   "rejected" if 400 <= getattr(error, "status_code", 0) < 500 else "failed")
        raise
    finally:
        ended = override["end_ns"] if "end_ns" in override else trace.clock()
        outcome = override.get("outcome", outcome)
        _parent.reset(token)
        pending = _deferred.get()
        if pending is None:
            trace.record(phase, started, ended, outcome=outcome, ordinal=ordinal, parent=parent)
        else:
            # The parent ordinal is reserved before nested work, even when its
            # observation is emitted after releasing the reentrant DB boundary.
            _defer((trace, phase, started, ended, outcome, parent, _operation.get(), ordinal), pending)


def timed(phase, *, operation=None):
    if phase not in PHASES or operation is not None and operation not in OPERATIONS:
        raise ValueError("unsupported attribution classification")
    def decorate(function):
        @functools.wraps(function)
        async def asynchronous(*args, **kwargs):
            token = _operation.set(operation or _operation.get())
            try:
                with span(phase):
                    return await function(*args, **kwargs)
            finally:
                _operation.reset(token)
        @functools.wraps(function)
        def synchronous(*args, **kwargs):
            token = _operation.set(operation or _operation.get())
            try:
                with span(phase):
                    return function(*args, **kwargs)
            finally:
                _operation.reset(token)
        wrapped = asynchronous if inspect.iscoroutinefunction(function) else synchronous
        # FastAPI resolves dependency annotations from the callable's globals.
        # Preserve evaluated types rather than moving string annotations into
        # this module's namespace when wrapping repository-owned dependencies.
        wrapped.__signature__ = inspect.signature(function, eval_str=True)
        return wrapped
    return decorate


def classified(operation):
    """Label owned repository work without timing another overlapping wrapper."""
    if operation not in OPERATIONS:
        raise ValueError("unsupported attribution operation")
    def decorate(function):
        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            token = _operation.set(operation)
            try:
                return function(*args, **kwargs)
            finally:
                _operation.reset(token)
        return wrapped
    return decorate
