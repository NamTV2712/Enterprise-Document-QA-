"""Deterministic research policy inside the one AGENT-002 execution loop."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter

from pydantic import BaseModel

from src.agent.research_models import (
    ResearchAction, ResearchConfig, ResearchEvidence, ResearchGap,
    ResearchObjectiveStatus, ResearchSummary, ResearchView,
)
from src.agent.state import AgentLimits, AgentObservation, EvidenceRef, FailureCode


_DOCUMENT_TICKER = re.compile(r"^([A-Z]{1,5}(?:-[A-Z])?):[A-Za-z0-9_.-]+$")


def validate_research_limits(config: ResearchConfig, limits: AgentLimits) -> None:
    if config.max_evidence_entries > limits.max_observations * limits.max_evidence_per_observation:
        raise ValueError("research evidence ceiling exceeds frozen observation capacity")
    if config.max_search_attempts_per_objective > limits.per_tool_calls["search_documents"]:
        raise ValueError("research search ceiling exceeds frozen search budget")
    if not limits.max_tool_calls or not limits.max_observations:
        raise ValueError("research requires a nonzero tool and observation budget")


def _fingerprint(tool_name: str, arguments: BaseModel) -> str:
    encoded = json.dumps(
        [tool_name, arguments.model_dump(mode="json")], ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _ticker(document_id: str | None) -> str | None:
    if document_id is None:
        return None
    match = _DOCUMENT_TICKER.fullmatch(document_id)
    return match.group(1) if match else None


class ResearchSession:
    """One bounded ledger; it never chooses or invokes a tool."""

    def __init__(self, config: ResearchConfig, limits: AgentLimits) -> None:
        validate_research_limits(config, limits)
        self.config = config
        self._ledger: list[ResearchEvidence] = []
        self._actions: list[ResearchAction] = []
        self._seen: set[tuple[str, str]] = set()
        self._search_attempts: Counter[str] = Counter()
        self._evidence_capped = False

    def _objective(self, objective_id: str | None):
        return next((item for item in self.config.objectives if item.objective_id == objective_id), None)

    def before_tool(
        self, objective_id: str | None, tool_name: str, arguments: BaseModel,
    ) -> FailureCode | None:
        objective = self._objective(objective_id)
        if objective is None:
            return "research_objective_required"
        scope = objective.ticker_scope
        if scope:
            if tool_name == "read_document":
                if _ticker(getattr(arguments, "document_id", None)) != scope:
                    return "research_scope_mismatch"
            elif getattr(arguments, "ticker", None) != scope:
                return "research_scope_mismatch"
        signature = _fingerprint(tool_name, arguments)
        if (objective.objective_id, signature) in self._seen:
            return "duplicate_tool_call"
        if (tool_name == "search_documents" and
                self._search_attempts[objective.objective_id] >= self.config.max_search_attempts_per_objective):
            return "research_search_limit"
        return None

    def start_tool(self, objective_id: str, tool_name: str, arguments: BaseModel) -> None:
        self._seen.add((objective_id, _fingerprint(tool_name, arguments)))
        if tool_name == "search_documents":
            self._search_attempts[objective_id] += 1

    def observed(
        self, objective_id: str, tool_name: str, arguments: BaseModel,
        observation: AgentObservation, step: int,
    ) -> None:
        objective = self._objective(objective_id)
        assert objective is not None
        before_count = sum(objective_id in item.objective_ids for item in self._ledger)
        for record in observation.evidence:
            if record.chunk_id is None:
                continue
            # AGENT-002's projection validated both canonical identities.
            EvidenceRef(kind="chunk_id", value=record.chunk_id)
            if record.document_id is not None:
                EvidenceRef(kind="document_id", value=record.document_id)
            ticker = _ticker(record.document_id)
            if objective.ticker_scope and ticker != objective.ticker_scope:
                continue
            key = (record.document_id or "", record.chunk_id)
            existing = next((i for i, item in enumerate(self._ledger)
                             if (item.document_id or "", item.chunk_id) == key), None)
            if existing is not None:
                item = self._ledger[existing]
                if objective_id not in item.objective_ids:
                    self._ledger[existing] = item.model_copy(update={
                        "objective_ids": (*item.objective_ids, objective_id),
                    })
                continue
            if len(self._ledger) >= self.config.max_evidence_entries:
                self._evidence_capped = True
                continue
            self._ledger.append(ResearchEvidence(
                document_id=record.document_id, chunk_id=record.chunk_id,
                ticker=ticker, objective_ids=(objective_id,),
                first_tool=tool_name, first_step=step,
            ))
        after_count = sum(objective_id in item.objective_ids for item in self._ledger)
        query = getattr(arguments, "query", None) if tool_name == "search_documents" else None
        self._actions.append(ResearchAction(
            objective_id=objective_id, tool_name=tool_name,
            argument_fingerprint=_fingerprint(tool_name, arguments), query=query,
            outcome=(
                "observed" if after_count > before_count else
                "no_new_evidence" if observation.evidence else "empty"
            ),
        ))

    def summary(self) -> ResearchSummary:
        statuses: list[ResearchObjectiveStatus] = []
        gaps: list[ResearchGap] = []
        for objective in self.config.objectives:
            count = sum(objective.objective_id in entry.objective_ids for entry in self._ledger)
            coverage = (
                "none" if count == 0 else
                "some" if count < self.config.min_evidence_per_objective else "sufficient"
            )
            attempts = self._search_attempts[objective.objective_id]
            statuses.append(ResearchObjectiveStatus(
                objective_id=objective.objective_id, coverage=coverage,
                evidence_count=count, search_attempts=attempts,
            ))
            if coverage != "sufficient":
                code = (
                    "ledger_full" if self._evidence_capped else
                    "search_exhausted" if attempts >= self.config.max_search_attempts_per_objective else
                    "no_evidence" if count == 0 else "below_threshold"
                )
                gaps.append(ResearchGap(objective_id=objective.objective_id, code=code))
        return ResearchSummary(
            objectives=tuple(statuses), evidence=tuple(self._ledger),
            gaps=tuple(gaps), evidence_capped=self._evidence_capped,
        )

    def view(self) -> ResearchView:
        return ResearchView(**self.summary().model_dump(mode="python"),
                            config=self.config, actions=tuple(self._actions))

    def validate_final(
        self, refs: tuple[EvidenceRef, ...], unresolved_ids: tuple[str, ...],
    ) -> FailureCode | None:
        if len(refs) > 12:
            return "research_reference_limit"
        summary = self.summary()
        gap_ids = {gap.objective_id for gap in summary.gaps}
        if len(unresolved_ids) != len(set(unresolved_ids)) or set(unresolved_ids) != gap_ids:
            return "research_unresolved_mismatch"
        cited = {(ref.kind, ref.value) for ref in refs}
        allowed = {
            (kind, value)
            for entry in summary.evidence
            for kind, value in (("chunk_id", entry.chunk_id), ("document_id", entry.document_id))
            if value is not None
        }
        if not cited <= allowed:
            return "invalid_evidence_reference"
        for objective in summary.objectives:
            if objective.coverage != "sufficient":
                continue
            if not any(
                objective.objective_id in entry.objective_ids and (
                    ("chunk_id", entry.chunk_id) in cited or
                    (entry.document_id is not None and ("document_id", entry.document_id) in cited)
                ) for entry in summary.evidence
            ):
                return "research_objective_uncited"
        return None
