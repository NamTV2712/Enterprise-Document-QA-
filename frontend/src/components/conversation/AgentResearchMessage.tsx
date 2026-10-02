import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { AgentMessage } from "../../lib/assistantExecution";
import { getChunkDetail } from "../../lib/api";
import { useLocale } from "../../lib/i18n";
import { agentCopy, agentErrorMessage } from "../agent/agentCopy";
import { AgentEvaluation, AgentFinalResult, AgentResearch, AgentTrace, agentStateLabel, agentToolLabel } from "../agent/AgentRunSections";
import { isTerminalAgentState, useAgentWorkspace } from "../agent/useAgentWorkspace";
import { researchCopy } from "./researchCopy";
import "./research.css";

export function AgentResearchMessage({ message, onConnect, onOpenDocument }: {
  message: AgentMessage; onConnect: () => void; onOpenDocument: (id: string) => void;
}) {
  const { locale } = useLocale();
  const copy = agentCopy[locale], research = researchCopy[locale];
  const runId = message.assistantExecution.runId;
  const model = useAgentWorkspace(runId, { loadList: false });
  const [sourceError, setSourceError] = useState(false);
  const sourceRequest = useRef<AbortController | null>(null);
  useEffect(() => { setSourceError(false); return () => sourceRequest.current?.abort(); }, [runId, model.session.generation]);
  const run = model.run;
  const terminal = !!run && isTerminalAgentState(run.state);
  const result = model.result?.result ?? run?.result;
  const summary = result?.research;
  const latest = [...model.events].reverse().find((event) => event.summary?.tool_name);
  const tool = latest?.summary?.tool_name;
  const safeTools = ["search_documents", "inspect_retrieval", "read_document", "ask_rag"];
  const evidence = result?.evidence_refs ?? [];
  const openChunk = async (id: string) => {
    sourceRequest.current?.abort();
    const controller = new AbortController(); sourceRequest.current = controller; setSourceError(false);
    try {
      const chunk = await getChunkDetail(id, controller.signal);
      if (!controller.signal.aborted) onOpenDocument(chunk.document_id);
    } catch { if (!controller.signal.aborted) setSourceError(true); }
  };
  return <article id={`message-${message.id}`} tabIndex={0} className="research-agent-message" aria-label={research.deep} data-agent-run-id={runId}>
    <header><h3>{research.deep}</h3>{run && <span role="status" aria-live="polite">{agentStateLabel(run.state, copy)}</span>}</header>
    {model.session.status !== "connected" ? <div><p>{research.disconnected}</p><button type="button" className="secondary-action-button" onClick={onConnect}>{research.reconnect}</button></div>
      : model.detailError !== null ? <div role="status"><p>{model.detailError === 404 ? research.unavailable : agentErrorMessage(model.detailError, copy, copy.detailError)}</p>
        <button type="button" className="secondary-action-button" onClick={model.refreshDetail}>{copy.retry}</button></div>
        : !run ? <p role="status">{copy.loadingDetail}</p> : <>
          {!terminal && <p className="research-activity">{tool && safeTools.includes(tool) ? agentToolLabel(tool, copy) : copy.activity}
            {" · "}{new Set(model.events.flatMap((event) => event.summary?.evidence_refs.map((ref) => `${ref.kind}:${ref.value}`) ?? [])).size} {copy.evidenceAdded}</p>}
          {(run.state === "queued" || run.state === "running") && <button type="button" className="secondary-action-button"
            disabled={!model.session.canExecute || model.cancelPending} onClick={() => void model.cancel()}>{model.cancelPending ? copy.cancellingAction : copy.cancel}</button>}
          {model.cancelNotice && <p role="status">{({ requested: copy.cancelRequested, cancelled: copy.cancelDone, conflict: copy.cancelConflict, error: copy.cancelError })[model.cancelNotice]}</p>}
          {model.eventState === "error" && <p role="status">{copy.eventsError}<button type="button" className="research-text-action" onClick={model.refreshDetail}>{copy.retry}</button></p>}
          {terminal && <>
            <AgentFinalResult run={run} result={model.result} copy={copy} hideRefs />
            {evidence.length > 0 && <section aria-label={copy.evidence}><h4>{copy.evidence}</h4><ul className="research-source-list">{evidence.map((ref) => <li key={`${ref.kind}:${ref.value}`}>
              {ref.kind === "document_id" ? <button type="button" className="research-text-action" onClick={() => onOpenDocument(ref.value)}>{copy.openDocument}: {ref.value}</button>
                : ref.kind === "chunk_id" ? <button type="button" className="research-text-action" onClick={() => void openChunk(ref.value)}>{copy.openDocument}: {ref.value}</button>
                  : <span>{copy.finalRefs}: <code>{ref.value}</code></span>}
            </li>)}</ul></section>}
            {sourceError && <p role="status">{research.sourceUnavailable}</p>}
            {result && <section aria-label={research.summary}><h4>{research.summary}</h4>
              <p>{result.tool_call_count} {copy.toolBudget} · {result.observation_count} {copy.observations} · {evidence.length} {copy.evidenceAdded}</p>
              {summary ? <p>{summary.evidence.length} {copy.evidenceCount} · {summary.gaps.length} {copy.researchGaps}</p> : <p className="research-mode-hint">{research.genericSummary}</p>}
            </section>}
          </>}
          <details className="research-agent-details"><summary>{research.details}</summary>
            <p><code>{runId}</code> · {copy.revision}: {run.revision}</p>
            <h4>{copy.activity}</h4><AgentTrace events={model.events} copy={copy} locale={locale} />
            <AgentResearch run={run} summary={summary ?? null} copy={copy} onOpenDocument={onOpenDocument} idPrefix={message.id} />
            {model.evaluation && <AgentEvaluation report={model.evaluation} copy={copy} locale={locale} />}
          </details>
        </>}
    <Link className="research-text-action" to={`/agent/runs/${encodeURIComponent(runId)}`}>{research.fullRun}</Link>
  </article>;
}
