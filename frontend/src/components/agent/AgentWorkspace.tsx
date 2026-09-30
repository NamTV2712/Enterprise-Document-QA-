import { useEffect, useRef, useState, type FormEvent } from "react";
import { Activity, AlertTriangle, ArrowLeft, FileText, LockKeyhole, Plus, RefreshCw, ShieldCheck, X } from "lucide-react";

import { useLocale } from "../../lib/i18n";
import { ModalDialog } from "../ui/ModalDialog";
import { agentCopy } from "./agentCopy";
import { AgentEvaluation, AgentFinalResult, AgentResearch, AgentTrace, agentDate, agentStateLabel, agentToolLabel } from "./AgentRunSections";
import { isTerminalAgentState, useAgentWorkspace } from "./useAgentWorkspace";

interface AgentWorkspaceProps {
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
  onClearSelectedRun: () => void;
  onOpenDocument: (documentId: string) => void;
}

interface ObjectiveDraft { question: string; ticker: string }

function errorMessage(status: number | null, copy: typeof agentCopy.en | typeof agentCopy.vi, fallback: string): string {
  if (status === 401 || status === 403) return copy.accessError;
  if (status === 404) return copy.unavailableError;
  if (status === 0) return copy.transportError;
  return fallback;
}

export function AgentWorkspace({ selectedRunId, onSelectRun, onClearSelectedRun, onOpenDocument }: AgentWorkspaceProps) {
  const { locale } = useLocale();
  const copy = agentCopy[locale];
  const model = useAgentWorkspace(selectedRunId);
  const [connectOpen, setConnectOpen] = useState(false);
  const [tokenDraft, setTokenDraft] = useState("");
  const [connectError, setConnectError] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [goal, setGoal] = useState("");
  const [runLocale, setRunLocale] = useState<"en" | "vi">(locale);
  const [mode, setMode] = useState<"generic" | "research">("generic");
  const [objectives, setObjectives] = useState<ObjectiveDraft[]>([{ question: "", ticker: "" }]);
  const [formError, setFormError] = useState(false);
  const tokenInput = useRef<HTMLInputElement>(null);
  const goalInput = useRef<HTMLTextAreaElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const listHeading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (selectedRunId) detailHeading.current?.focus();
    else listHeading.current?.focus();
  }, [selectedRunId]);

  const closeConnect = () => { setConnectOpen(false); setTokenDraft(""); setConnectError(false); };
  const handleConnect = async (event: FormEvent) => {
    event.preventDefault();
    setConnectError(false);
    try { await model.session.connect(tokenDraft); closeConnect(); }
    catch { setConnectError(true); }
  };
  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    const cleanGoal = goal.trim();
    const validResearch = mode === "generic" || (objectives.length >= 1 && objectives.length <= 6 && objectives.every((item) =>
      item.question.trim().length >= 5 && item.question.trim().length <= 120
      && (!item.ticker.trim() || /^[A-Z]{1,5}(?:-[A-Z])?$/.test(item.ticker.trim().toUpperCase()))));
    if (cleanGoal.length < 5 || cleanGoal.length > 500 || !validResearch) { setFormError(true); return; }
    setFormError(false);
    const body = {
      goal: cleanGoal, locale: runLocale,
      ...(mode === "research" ? { research: { version: "agent_research_v1" as const,
        objectives: objectives.map((item, index) => ({
          objective_id: `objective_${index + 1}`, question: item.question.trim(), ticker_scope: item.ticker.trim().toUpperCase() || null,
        })) } } : {}),
    };
    const created = await model.create(body);
    if (created) {
      setCreateOpen(false); setGoal(""); setMode("generic"); setObjectives([{ question: "", ticker: "" }]);
      onSelectRun(created.run_id);
    }
  };
  const connected = !!model.token;
  const run = model.run;
  const canCancel = !!run && model.session.canExecute && (run.state === "queued" || run.state === "running") && !model.cancelPending;

  return <div className={`agent-workspace ${selectedRunId ? "has-selected-run" : ""}`} aria-labelledby="agent-title">
    <header className="agent-header">
      <div><span className="agent-eyebrow"><Activity aria-hidden="true" /> {copy.title}</span><h1 id="agent-title">{copy.title}</h1><p>{copy.subtitle}</p></div>
      <div className="agent-header-actions">
        <span className="agent-connection" aria-label={connected ? (model.session.canExecute ? copy.connected : copy.readOnly) : copy.disconnected}>
          {connected ? <ShieldCheck aria-hidden="true" /> : <LockKeyhole aria-hidden="true" />}
          {connected ? (model.session.canExecute ? copy.connected : copy.readOnly) : copy.disconnected}
        </span>
        {connected ? <button type="button" className="console-btn" onClick={() => { model.session.disconnect(); onClearSelectedRun(); }}>{copy.disconnect}</button>
          : <button type="button" className="console-btn console-btn--primary" onClick={() => setConnectOpen(true)}>{copy.connect}</button>}
      </div>
    </header>

    {!connected ? <section className="console-card agent-private-state"><LockKeyhole aria-hidden="true" /><h2>{copy.disconnected}</h2><p>{copy.connectionBody}</p><button type="button" className="console-btn console-btn--primary" onClick={() => setConnectOpen(true)}>{copy.connect}</button></section>
      : <>
        <div className="agent-runtime-note" role="note"><AlertTriangle aria-hidden="true" /><p>{copy.executionWarning}</p></div>
        <div className="agent-toolbar">
          <button type="button" className="console-btn" onClick={model.refreshList}><RefreshCw aria-hidden="true" />{copy.refresh}</button>
          {model.session.canExecute && <button type="button" className="console-btn console-btn--primary" onClick={() => { setRunLocale(locale); setCreateOpen(true); }}><Plus aria-hidden="true" />{copy.create}</button>}
        </div>
        <div className="agent-columns">
          <section className="console-card agent-run-list" aria-labelledby="agent-runs-title">
            <div className="console-card__header"><div><h2 ref={listHeading} id="agent-runs-title" tabIndex={-1}>{copy.runs}</h2><p>{copy.runsHint}</p></div></div>
            {model.listState === "loading" && <p className="agent-inline-state" role="status">{copy.loadingRuns}</p>}
            {model.listState === "error" && <div className="agent-inline-state" role="alert"><p>{errorMessage(model.listError, copy, copy.listError)}</p><button type="button" className="console-btn" onClick={model.refreshList}>{copy.retry}</button></div>}
            {model.listState === "ready" && model.list?.total === 0 && <p className="agent-inline-state">{copy.emptyRuns}</p>}
            {model.list && model.list.items.length > 0 && <ul className="agent-run-items">{model.list.items.map((item) =>
              <li key={item.run_id}><button type="button" className={`agent-run-item ${selectedRunId === item.run_id ? "is-selected" : ""}`} aria-current={selectedRunId === item.run_id ? "page" : undefined} onClick={() => onSelectRun(item.run_id)}>
                <span className="agent-run-item-top"><strong>{item.frozen.goal}</strong><span className={`agent-state agent-state--${item.state}`}>{agentStateLabel(item.state, copy)}</span></span>
                <code className="agent-long-id">{item.run_id}</code><span className="agent-run-item-bottom"><time dateTime={item.created_at}>{agentDate(item.created_at, locale, copy.notReported)}</time><span>{item.frozen.research ? copy.research : copy.generic}</span><span>{copy.revision} {item.revision}</span></span>
              </button></li>)}</ul>}
            {model.list && model.list.total > model.list.page_size && <nav className="agent-pagination" aria-label={copy.runs}>
              <button type="button" className="console-btn" disabled={model.page <= 1} onClick={() => model.setPage((page) => page - 1)}>{copy.previous}</button>
              <span>{copy.page} {model.page} {copy.of} {Math.ceil(model.list.total / model.list.page_size)}</span>
              <button type="button" className="console-btn" disabled={model.page * model.list.page_size >= model.list.total} onClick={() => model.setPage((page) => page + 1)}>{copy.next}</button>
            </nav>}
          </section>

          <section className="agent-run-detail" aria-labelledby="agent-detail-title">
            <div className="agent-detail-top"><button type="button" className="console-btn agent-back" onClick={() => { onClearSelectedRun(); listHeading.current?.focus(); }}><ArrowLeft aria-hidden="true" />{copy.backToRuns}</button><h2 ref={detailHeading} id="agent-detail-title" tabIndex={-1}>{copy.selected}</h2>{selectedRunId && <button type="button" className="console-btn" onClick={model.refreshDetail}><RefreshCw aria-hidden="true" />{copy.refresh}</button>}</div>
            {!selectedRunId && <div className="console-card agent-empty-detail"><FileText aria-hidden="true" /><p>{copy.selectRun}</p></div>}
            {selectedRunId && model.detailState === "loading" && <div className="console-card agent-inline-state" role="status">{copy.loadingDetail}</div>}
            {selectedRunId && model.detailState === "error" && <div className="console-card agent-inline-state" role="alert"><p>{model.detailError === 404 ? copy.unknownRun : errorMessage(model.detailError, copy, copy.detailError)}</p><button type="button" className="console-btn" onClick={model.refreshDetail}>{copy.retry}</button></div>}
            {run && <>
              <div className="console-card agent-section">
                <div className="agent-section-body"><div className="agent-run-title"><div><strong>{run.frozen.goal}</strong><code className="agent-long-id">{run.run_id}</code></div><span className={`agent-state agent-state--${run.state}`}>{agentStateLabel(run.state, copy)}</span></div>
                  <dl className="agent-facts"><div><dt>{copy.revision}</dt><dd>{run.revision}</dd></div><div><dt>{copy.created}</dt><dd>{agentDate(run.created_at, locale, copy.notReported)}</dd></div><div><dt>{copy.started}</dt><dd>{agentDate(run.started_at, locale, copy.notReported)}</dd></div><div><dt>{copy.finished}</dt><dd>{agentDate(run.finished_at, locale, copy.notReported)}</dd></div></dl>
                  {canCancel && <button type="button" className="console-btn agent-cancel" onClick={() => void model.cancel()}>{model.cancelPending ? copy.cancellingAction : copy.cancel}</button>}
                  {model.cancelNotice && <p className="agent-notice" role="status">{model.cancelNotice === "requested" ? copy.cancelRequested : model.cancelNotice === "cancelled" ? copy.cancelDone : model.cancelNotice === "conflict" ? copy.cancelConflict : copy.cancelError}</p>}
                  {run.state === "cancelling" && model.cancelNotice !== "requested" && <p className="agent-muted">{copy.cancelRequested}</p>}
                </div>
              </div>
              <section className="console-card agent-section" aria-labelledby="agent-policy-title"><div className="console-card__header"><h3 id="agent-policy-title">{copy.frozenPolicy}</h3></div><div className="agent-section-body">
                <dl className="agent-facts"><div><dt>{copy.decisionModel}</dt><dd><code>{run.frozen.decision_model_id}</code></dd></div><div><dt>{copy.allowedTools}</dt><dd>{run.frozen.allowed_tools.map((tool) => agentToolLabel(tool, copy)).join(", ") || copy.notReported}</dd></div><div><dt>{copy.decisionProviderPermission}</dt><dd>{run.frozen.allow_decision_provider_execution ? copy.permitted : copy.blocked}</dd></div><div><dt>{copy.ragProviderPermission}</dt><dd>{run.frozen.allow_provider_tool_execution ? copy.permitted : copy.blocked}</dd></div></dl>
                <div className="agent-budget-grid"><div><span>{copy.decisionBudget}</span><strong>{run.result?.step_count ?? "—"} / {run.frozen.limits.max_steps}</strong></div><div><span>{copy.decisionCalls}</span><strong>{run.result?.decision_call_count ?? "—"} / {run.frozen.limits.max_steps}</strong></div><div><span>{copy.toolBudget}</span><strong>{run.result?.tool_call_count ?? "—"} / {run.frozen.limits.max_tool_calls}</strong></div><div><span>{copy.observations}</span><strong>{run.result?.observation_count ?? "—"} / {run.frozen.limits.max_observations}</strong></div></div>
                <ul className="agent-tool-budgets">{Object.entries(run.frozen.limits.per_tool_calls).map(([tool, limit]) => <li key={tool}><span>{agentToolLabel(tool, copy)}</span><strong>{run.result?.per_tool_calls[tool as keyof typeof run.result.per_tool_calls] ?? "—"} / {limit}</strong></li>)}</ul>
              </div></section>
              <section className="console-card agent-section" aria-labelledby="agent-trace-title"><div className="console-card__header"><div><h3 id="agent-trace-title">{copy.activity}</h3><p>{copy.activityHint}</p></div></div><div className="agent-section-body">
                {model.eventState === "loading" && <p role="status">{copy.loadingEvents}</p>}
                <AgentTrace events={model.events} copy={copy} locale={locale} />
                <p className="agent-muted">{model.eventState === "error" ? errorMessage(model.eventError, copy, copy.eventsError) : model.eventState === "closed" ? copy.eventsClosed : copy.eventsCurrent} {model.eventCursor > 0 ? `#${model.eventCursor}` : ""}</p>
              </div></section>
              <AgentResearch run={run} summary={model.result?.result?.research ?? run.result?.research ?? null} copy={copy} onOpenDocument={onOpenDocument} />
              <section className="console-card agent-section" aria-labelledby="agent-result-title"><div className="console-card__header"><h3 id="agent-result-title">{copy.finalResult}</h3></div><AgentFinalResult run={run} result={model.result} copy={copy} /></section>
              <section className="console-card agent-section" aria-labelledby="agent-evaluation-title"><div className="console-card__header"><h3 id="agent-evaluation-title">{copy.evaluation}</h3></div>
                {model.evaluationState === "loading" && <p className="agent-inline-state" role="status">{copy.evaluationLoading}</p>}
                {model.evaluationState === "not_applicable" && <p className="agent-inline-state">{copy.evaluationPending}</p>}
                {model.evaluationState === "error" && <div className="agent-inline-state" role="alert"><p>{copy.evaluationError}</p><button type="button" className="console-btn" onClick={model.refreshDetail}>{copy.retry}</button></div>}
                {model.evaluation && <AgentEvaluation report={model.evaluation} copy={copy} locale={locale} />}
                {isTerminalAgentState(run.state) && model.evaluationState === "idle" && <p className="agent-inline-state">{copy.evaluationLoading}</p>}
              </section>
            </>}
          </section>
        </div>
      </>}

    <ModalDialog open={connectOpen} onClose={closeConnect} labelledBy="agent-connect-title" initialFocusRef={tokenInput} className="agent-dialog console-card">
      <div className="agent-dialog-header"><h2 id="agent-connect-title">{copy.connect}</h2><button type="button" className="console-btn" aria-label={copy.close} onClick={closeConnect}><X aria-hidden="true" /></button></div>
      <form onSubmit={(event) => void handleConnect(event)}><label htmlFor="agent-token">{copy.token}</label><input id="agent-token" ref={tokenInput} type="password" autoComplete="off" value={tokenDraft} onChange={(event) => setTokenDraft(event.target.value)} /><p className="agent-muted">{copy.tokenHint}</p>{connectError && <p role="alert" className="agent-notice">{copy.accessError}</p>}<button type="submit" className="console-btn console-btn--primary" disabled={!tokenDraft.trim() || model.session.status === "connecting"}>{copy.verify}</button></form>
    </ModalDialog>

    <ModalDialog open={createOpen} onClose={() => { if (!model.createPending) setCreateOpen(false); }} labelledBy="agent-create-title" initialFocusRef={goalInput} className="agent-dialog agent-create-dialog console-card">
      <div className="agent-dialog-header"><h2 id="agent-create-title">{copy.createTitle}</h2><button type="button" className="console-btn" aria-label={copy.close} onClick={() => setCreateOpen(false)} disabled={model.createPending}><X aria-hidden="true" /></button></div>
      <p className="agent-notice">{copy.createHint}</p>
      <form onSubmit={(event) => void handleCreate(event)}><label htmlFor="agent-goal">{copy.goal}</label><textarea id="agent-goal" ref={goalInput} value={goal} onChange={(event) => setGoal(event.target.value)} maxLength={500} rows={3} /><p className="agent-muted">{copy.goalHint}</p>
        <div className="agent-form-row"><label htmlFor="agent-mode">{copy.mode}<select id="agent-mode" value={mode} onChange={(event) => setMode(event.target.value as "generic" | "research")}><option value="generic">{copy.generic}</option><option value="research">{copy.research}</option></select></label><label htmlFor="agent-language">{copy.language}<select id="agent-language" value={runLocale} onChange={(event) => setRunLocale(event.target.value as "en" | "vi")}><option value="en">English</option><option value="vi">Tiếng Việt</option></select></label></div>
        {mode === "research" && <fieldset className="agent-objective-form"><legend>{copy.objectives}</legend>{objectives.map((item, index) => <div key={index} className="agent-objective-draft"><strong>{copy.objective} {index + 1}</strong><label>{copy.objectiveQuestion}<input value={item.question} maxLength={120} onChange={(event) => setObjectives((current) => current.map((draft, position) => position === index ? { ...draft, question: event.target.value } : draft))} /></label><label>{copy.tickerScope}<input value={item.ticker} maxLength={7} onChange={(event) => setObjectives((current) => current.map((draft, position) => position === index ? { ...draft, ticker: event.target.value.toUpperCase() } : draft))} /></label>{objectives.length > 1 && <button type="button" className="console-btn" onClick={() => setObjectives((current) => current.filter((_, position) => position !== index))}>{copy.removeObjective}</button>}</div>)}<button type="button" className="console-btn" disabled={objectives.length >= 6} onClick={() => setObjectives((current) => [...current, { question: "", ticker: "" }])}>{copy.addObjective}</button></fieldset>}
        {formError && <p role="alert" className="agent-notice">{copy.createInvalid}</p>}{model.createError !== null && <p role="alert" className="agent-notice">{errorMessage(model.createError, copy, copy.detailError)}</p>}
        <button type="submit" className="console-btn console-btn--primary" disabled={model.createPending}>{model.createPending ? copy.creating : copy.createSubmit}</button>
      </form>
    </ModalDialog>
  </div>;
}
