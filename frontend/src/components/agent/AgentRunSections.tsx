import type {
  AgentEvaluationReport, AgentEvent, AgentMetricResult, AgentResearchSummary, AgentRun, AgentRunResult, AgentToolName,
} from "../../lib/agentTypes";
import type { AgentCopy } from "./agentCopy";

export function agentStateLabel(state: AgentRun["state"], copy: AgentCopy): string {
  const labels = {
    queued: copy.stateQueued, running: copy.stateRunning, cancelling: copy.stateCancelling,
    cancelled: copy.stateCancelled, succeeded: copy.stateSucceeded, failed: copy.stateFailed,
    interrupted: copy.stateInterrupted,
  };
  return labels[state];
}

export function agentToolLabel(name: string, copy: AgentCopy): string {
  const labels: Record<AgentToolName, string> = {
    search_documents: copy.toolSearch, inspect_retrieval: copy.toolInspect,
    read_document: copy.toolRead, ask_rag: copy.toolRag,
  };
  return Object.hasOwn(labels, name) ? labels[name as AgentToolName] : copy.eventUnknown;
}

export function agentDate(value: string | null, locale: "en" | "vi", fallback: string): string {
  if (!value) return fallback;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : date.toLocaleString(locale === "vi" ? "vi-VN" : "en-US", { timeZone: "UTC", timeZoneName: "short" });
}

function eventLabel(event: AgentEvent, copy: AgentCopy): string {
  if (event.event_type === "created") return copy.eventCreated;
  if (event.event_type === "state_changed") return copy.eventState;
  if (event.event_type === "step_changed") return copy.eventStep;
  if (event.event_type === "cancellation_requested") return copy.eventCancelRequested;
  if (event.event_type === "cancelled") return copy.eventCancelled;
  if (event.event_type === "interrupted") return copy.eventInterrupted;
  if (event.event_type === "agent_decision") {
    const summary = event.summary;
    return summary?.decision_kind === "tool" && summary.tool_name
      ? agentToolLabel(summary.tool_name, copy) : copy.eventDecision;
  }
  return copy.eventUnknown;
}

export function AgentTrace({ events, copy, locale }: { events: AgentEvent[]; copy: AgentCopy; locale: "en" | "vi" }) {
  if (!events.length) return <p className="agent-muted">{copy.noEvents}</p>;
  return <ol className="agent-trace-list" aria-label={copy.activity} tabIndex={0}>
    {events.map((event) => <li key={`${event.run_id}:${event.sequence}`} className="agent-trace-item">
      <span className="agent-trace-sequence" aria-label={`${copy.event} ${event.sequence}`}>{event.sequence}</span>
      <div className="agent-trace-content">
        <div className="agent-trace-heading"><strong>{eventLabel(event, copy)}</strong><time dateTime={event.occurred_at}>{agentDate(event.occurred_at, locale, copy.notReported)}</time></div>
        <div className="agent-trace-meta">
          {event.state && <span>{agentStateLabel(event.state, copy)}</span>}
          {event.summary?.objective_id && <span>{copy.objectiveId}: <code>{event.summary.objective_id}</code></span>}
          {event.summary && <span>{event.summary.outcome}</span>}
          {event.summary && event.summary.evidence_count > 0 && <span>{event.summary.evidence_count} {copy.evidenceAdded}</span>}
          {(event.summary?.failure_code || event.reason_code) && <span>{copy.eventFailure}: <code>{event.summary?.failure_code ?? event.reason_code}</code></span>}
        </div>
      </div>
    </li>)}
  </ol>;
}

function coverageLabel(coverage: "none" | "some" | "sufficient", copy: AgentCopy): string {
  return coverage === "sufficient" ? copy.evidenceThreshold : coverage === "some" ? copy.someEvidence : copy.noCoverage;
}

function gapLabel(code: string, copy: AgentCopy): string {
  const labels: Record<string, string> = {
    no_evidence: copy.gapNoEvidence, below_threshold: copy.gapBelowThreshold,
    search_exhausted: copy.gapSearchExhausted, ledger_full: copy.gapLedgerFull,
  };
  return labels[code] ?? code;
}

export function AgentResearch({ run, summary, copy, onOpenDocument, idPrefix = "agent" }: {
  run: AgentRun; summary: AgentResearchSummary | null; copy: AgentCopy; onOpenDocument: (documentId: string) => void; idPrefix?: string;
}) {
  const configured = run.frozen.research;
  if (!configured) return null;
  const statuses = new Map(summary?.objectives.map((item) => [item.objective_id, item]));
  const gaps = new Map(summary?.gaps.map((item) => [item.objective_id, item.code]));
  return <>
    <section className="console-card agent-section" aria-labelledby={`${idPrefix}-objectives-title`}>
      <div className="console-card__header"><h3 id={`${idPrefix}-objectives-title`}>{copy.researchObjectives}</h3></div>
      <div className="agent-section-body agent-objectives">
        {configured.objectives.map((objective) => {
          const status = statuses.get(objective.objective_id);
          return <article className="agent-objective" key={objective.objective_id}>
            <div className="agent-objective-heading"><strong>{objective.question}</strong><code>{objective.objective_id}</code></div>
            <div className="agent-meta-row">
              {objective.ticker_scope && <span>{objective.ticker_scope}</span>}
              <span>{status ? coverageLabel(status.coverage, copy) : copy.notReported}</span>
              {status && <span>{status.evidence_count} {copy.evidenceCount} · {status.search_attempts} {copy.searchAttempts}</span>}
              {gaps.has(objective.objective_id) && <span className="agent-gap">{gapLabel(gaps.get(objective.objective_id)!, copy)}</span>}
            </div>
          </article>;
        })}
      </div>
    </section>
    {summary && <section className="console-card agent-section" aria-labelledby={`${idPrefix}-gaps-title`}>
      <div className="console-card__header"><h3 id={`${idPrefix}-gaps-title`}>{copy.researchGaps}</h3></div>
      <div className="agent-section-body">{summary.gaps.length ? <ul className="agent-gap-list">{summary.gaps.map((gap) =>
        <li key={gap.objective_id}><span className="agent-gap">{gapLabel(gap.code, copy)}</span><code>{gap.objective_id}</code></li>)}</ul>
        : <p className="agent-muted">{copy.noGaps}</p>}</div>
    </section>}
    <section className="console-card agent-section" aria-labelledby={`${idPrefix}-evidence-title`}>
      <div className="console-card__header"><h3 id={`${idPrefix}-evidence-title`}>{copy.evidence}</h3></div>
      <div className="agent-section-body">
        <p className="agent-muted">{copy.evidenceNote}</p>
        {summary?.evidence_capped && <p className="agent-notice">{copy.ledgerCapped}</p>}
        {!summary?.evidence.length ? <p>{copy.noEvidence}</p> : <ul className="agent-evidence-list">{summary.evidence.map((item) =>
          <li key={`${item.document_id ?? ""}:${item.chunk_id}`} className="agent-evidence-card">
            <div className="agent-evidence-primary"><strong>{item.ticker ?? copy.evidence}</strong><code>{item.document_id ?? item.chunk_id}</code></div>
            {item.document_id && <code className="agent-long-id">{item.chunk_id}</code>}
            <div className="agent-meta-row"><span>{copy.associated}: {item.objective_ids.join(", ")}</span><span>{copy.firstTool}: {agentToolLabel(item.first_tool, copy)}</span><span>{copy.firstStep}: {item.first_step}</span></div>
            {item.document_id && <button type="button" className="console-btn" onClick={() => onOpenDocument(item.document_id!)}>{copy.openDocument}</button>}
          </li>)}</ul>}
      </div>
    </section>
  </>;
}

const METRIC_GROUPS = [
  ["groupOutcome", ["execution_completed", "invalid_final_attempt_count"]],
  ["groupTools", ["recorded_tool_decision_count", "admitted_tool_call_count", "tool_admission_fraction", "invalid_tool_attempt_count", "duplicate_rejection_count", "tool_failure_fraction", "tool_unavailable_count"]],
  ["groupBudgets", ["step_budget_utilization", "tool_budget_utilization", "budget_exhausted"]],
  ["groupEvidence", ["evidence_identity_validity", "final_reference_validity"]],
  ["groupResearch", ["objective_coverage", "unresolved_gap_fraction", "research_evidence_count", "distinct_document_count", "distinct_chunk_count"]],
  ["groupPolicy", ["policy_denial_attempt_count", "decision_provider_unavailable"]],
] as const;

const VI_METRIC_LABELS: Record<string, string> = {
  execution_completed: "Thực thi hoàn tất", recorded_tool_decision_count: "Quyết định công cụ đã ghi",
  admitted_tool_call_count: "Lần gọi công cụ được nhận", tool_admission_fraction: "Tỷ lệ công cụ được nhận",
  invalid_tool_attempt_count: "Lần thử công cụ không hợp lệ", policy_denial_attempt_count: "Lần bị chính sách từ chối",
  duplicate_rejection_count: "Lần lặp bị từ chối", tool_failure_fraction: "Tỷ lệ công cụ thất bại",
  tool_unavailable_count: "Lần công cụ không khả dụng", invalid_final_attempt_count: "Lần kết luận không hợp lệ",
  step_budget_utilization: "Mức dùng ngân sách bước", tool_budget_utilization: "Mức dùng ngân sách công cụ",
  budget_exhausted: "Cạn ngân sách", decision_provider_unavailable: "Provider quyết định không khả dụng",
  evidence_identity_validity: "Tính hợp lệ danh tính bằng chứng", final_reference_validity: "Tính hợp lệ tham chiếu cuối",
  objective_coverage: "Độ phủ mục tiêu", unresolved_gap_fraction: "Tỷ lệ khoảng trống chưa giải quyết",
  research_evidence_count: "Số mục bằng chứng", distinct_document_count: "Số tài liệu khác nhau",
  distinct_chunk_count: "Số đoạn khác nhau",
};

function metricText(metric: AgentMetricResult, copy: AgentCopy, locale: "en" | "vi"): string {
  if (metric.status === "unavailable") return copy.unavailable;
  if (metric.status === "not_applicable") return copy.notApplicable;
  if (typeof metric.value === "boolean") return locale === "vi" ? (metric.value ? "Có" : "Không") : (metric.value ? "True" : "False");
  if (typeof metric.value === "number") return metric.denominator === null ? String(metric.value) : metric.value.toFixed(4);
  return copy.unavailable;
}

export function AgentEvaluation({ report, copy, locale }: { report: AgentEvaluationReport; copy: AgentCopy; locale: "en" | "vi" }) {
  const definitions = new Map(report.metric_definitions.map((item) => [item.metric_id, item]));
  const results = new Map(report.metrics.map((item) => [item.metric_id, item]));
  return <div className="agent-evaluation-body">
    <p className="agent-muted">{copy.evaluationHint}</p>
    {METRIC_GROUPS.map(([group, names]) => <section key={group} className="agent-metric-group" aria-label={copy[group]}>
      <h4>{copy[group]}</h4>
      <div className="agent-metric-grid">{names.map((name) => {
        const id = `native_agent.${name}`;
        const definition = definitions.get(id);
        const result = results.get(id);
        if (!definition || !result) return null;
        return <div className="agent-metric" key={id}>
          <div className="agent-metric-heading"><span>{locale === "vi" ? VI_METRIC_LABELS[name] ?? definition.label : definition.label}</span><strong>{metricText(result, copy, locale)}</strong></div>
          <small>{result.status === "computed" ? copy.computed : result.status === "unavailable" ? copy.unavailable : copy.notApplicable}</small>
          {result.status === "computed" && result.denominator !== null && <small>{copy.numerator}: {result.numerator} · {copy.denominator}: {result.denominator}</small>}
          <details><summary>{locale === "vi" ? "Ý nghĩa và giới hạn" : "Meaning and limits"}</summary><p>{definition.meaning} {definition.non_meaning}</p><code>{definition.metric_id} · v{definition.metric_version}</code></details>
        </div>;
      })}</div>
    </section>)}
    <p className="agent-limitation">{copy.limitation}</p>
    <details className="agent-provenance"><summary>{copy.technical}</summary><dl><div><dt>{copy.digest}</dt><dd><code>{report.digest}</code></dd></div><div><dt>Protocol</dt><dd>{report.protocol} v{report.protocol_version}</dd></div><div><dt>Run revision</dt><dd>{report.provenance.run_revision}</dd></div></dl></details>
  </div>;
}

export function AgentFinalResult({ run, result, copy, hideRefs = false }: { run: AgentRun; result: AgentRunResult | null; copy: AgentCopy; hideRefs?: boolean }) {
  const terminal = result?.result ?? run.result;
  const failureCode = terminal?.failure?.code ?? result?.failure?.code ?? run.failure?.code;
  return <div className="agent-section-body">
    {failureCode === "decision_provider_unavailable" && <p className="agent-notice">{copy.providerUnavailable}</p>}
    <div className="agent-meta-row"><span>{agentStateLabel(run.state, copy)}</span>{terminal && <span>{terminal.agent_status}</span>}{failureCode && <code>{failureCode}</code>}</div>
    {terminal?.agent_status === "completed" && terminal.answer !== null ? <>
      <h4>{copy.answer}</h4><div className="agent-answer">{terminal.answer}</div>
    </> : <p className="agent-muted">{run.state === "queued" || run.state === "running" || run.state === "cancelling" ? copy.noResult : copy.noAnswer}</p>}
    {!hideRefs && !!terminal?.evidence_refs.length && <div><h4>{copy.finalRefs}</h4><ul className="agent-final-refs">{terminal.evidence_refs.map((ref) => <li key={`${ref.kind}:${ref.value}`}><span>{ref.kind}</span><code>{ref.value}</code></li>)}</ul></div>}
  </div>;
}
