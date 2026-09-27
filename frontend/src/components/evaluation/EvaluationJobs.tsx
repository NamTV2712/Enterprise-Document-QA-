import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Check, Link2, LoaderCircle, LockKeyhole, Play, RefreshCw, Square, X } from "lucide-react";
import { ModalDialog } from "../ui/ModalDialog";
import { evaluationApi, evaluationErrorMessage } from "../../lib/evaluationApi";
import { pipelineErrorMessage } from "../../lib/pipelineApi";
import type { EvaluationJob, EvaluationJobCreate, EvaluationJobState, NativeMetricDefinition } from "../../lib/evaluationTypes";
import { useLocalWorkspaceSession } from "../../lib/localWorkspaceSession";
import { NativeCases } from "./NativeMetrics";
import { useEvaluationCreation } from "./useEvaluationCreation";
import { useEvaluationJob } from "./useEvaluationJob";
import type { EvaluationLocale } from "./NativeMetrics";

const metricIds: EvaluationJobCreate["metrics"] = ["native.faithfulness", "native.answer_relevancy", "native.context_precision", "native.citation_index_validity", "native.keyword_recall_proxy", "native.fallback_correctness"];
const terminal = new Set<EvaluationJobState>(["cancelled", "succeeded", "failed", "interrupted"]);
function date(value: string, locale: EvaluationLocale) { const parsed = new Date(value); return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString(locale === "vi" ? "vi-VN" : "en-US"); }
function stateLabel(state: EvaluationJobState) { return state; }

export function EvaluationJobs({ selectedJobId, onSelectJob, definitions, locale = "en" }: {
  selectedJobId: string | null; onSelectJob: (id: string) => void; definitions: NativeMetricDefinition[]; locale?: EvaluationLocale;
}) {
  const vi = locale === "vi";
  const session = useLocalWorkspaceSession();
  const [tokenDraft, setTokenDraft] = useState(""); const [connectErrorStatus, setConnectErrorStatus] = useState<number | null>(null);
  const [jobs, setJobs] = useState<EvaluationJob[]>([]); const [total, setTotal] = useState(0);
  const [listLoading, setListLoading] = useState(false); const [listError, setListError] = useState<number | null>(null);
  const [refresh, setRefresh] = useState(0); const [page, setPage] = useState(1); const [jobState, setJobState] = useState<EvaluationJobState | "all">("all");
  const [resultPage, setResultPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false); const [artifactId, setArtifactId] = useState(""); const [budget, setBudget] = useState("6");
  const firstCreateControl = useRef<HTMLInputElement>(null);
  const selected = useEvaluationJob(selectedJobId, resultPage);
  const creation = useEvaluationCreation((job) => { setCreateOpen(false); setArtifactId(""); setBudget("6"); setRefresh((value) => value + 1); onSelectJob(job.id); });

  useEffect(() => {
    const token = session.getToken(); const controller = new AbortController(); let live = true;
    setJobs([]); setTotal(0); setListError(null); setListLoading(Boolean(token && session.status === "connected"));
    if (!token || session.status !== "connected") return () => { live = false; controller.abort(); };
    void evaluationApi.listJobs(token, { page, page_size: 25, state: jobState === "all" ? undefined : jobState }, controller.signal).then((result) => {
      if (!live) return; setJobs(result.items); setTotal(result.total);
    }).catch((error) => {
      if (!live || controller.signal.aborted) return;
      const status = typeof error === "object" && error && "status" in error ? Number(error.status) : 0;
      setListError(status); if (status === 401) session.invalidateIfCurrent(token, session.generation);
    }).finally(() => { if (live) setListLoading(false); });
    return () => { live = false; controller.abort(); };
  }, [jobState, page, refresh, session.generation, session.status]);
  useEffect(() => { setResultPage(1); }, [selectedJobId]);

  const parsedBudget = Number(budget);
  const createValid = /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/.test(artifactId) && Number.isInteger(parsedBudget) && parsedBudget >= 1 && parsedBudget <= 15000;
  const jobDefinitions = selected.results?.metric_definitions.length ? selected.results.metric_definitions : definitions;
  const progress = selected.job?.progress;
  const submitConnect = async (event: React.FormEvent) => {
    event.preventDefault(); setConnectErrorStatus(null);
    try { await session.connect(tokenDraft); setTokenDraft(""); }
    catch (error) {
      setTokenDraft("");
      setConnectErrorStatus(typeof error === "object" && error && "status" in error ? Number(error.status) : 0);
    }
  };
  const create = () => {
    if (!createValid) return;
    void creation.submit({ artifact_id: artifactId, engine: "native", metrics: metricIds, mode: "provider_backed", budget: parsedBudget });
  };
  const displayedJobs = useMemo(() => selected.job && !jobs.some((job) => job.id === selected.job?.id) ? [selected.job, ...jobs] : jobs, [jobs, selected.job]);
  return <section className="evaluation-jobs" aria-labelledby="evaluation-jobs-title">
    <header className="evaluation-section-header"><div><h2 id="evaluation-jobs-title">{vi ? "Evaluation jobs riêng tư" : "Private evaluation jobs"}</h2><p>{vi ? "Các job frozen, có ngân sách và receipt bền vững. Hoàn thành không tự publish." : "Frozen, budgeted jobs with durable receipts. Completion does not publish automatically."}</p></div>
      {session.status === "connected" && <div className="evaluation-actions"><span className="evaluation-connected"><Check aria-hidden="true" />{session.canExecute ? (vi ? "Đã kết nối · có thể chạy" : "Connected · execution enabled") : (vi ? "Đã kết nối · chỉ đọc" : "Connected · read only")}</span><button type="button" className="console-btn" onClick={session.disconnect}>{vi ? "Ngắt kết nối" : "Disconnect"}</button><button type="button" className="console-btn console-btn--primary" disabled={!session.canExecute} onClick={() => setCreateOpen(true)}><Play aria-hidden="true" />{vi ? "Evaluation mới" : "New evaluation"}</button></div>}
    </header>
    {session.status !== "connected" ? <div className="evaluation-connect">
      <LockKeyhole aria-hidden="true" /><div><h3>{vi ? "Kết nối workspace cục bộ" : "Connect the local workspace"}</h3><p>{vi ? "Token chỉ nằm trong bộ nhớ và chỉ gửi tới các route riêng tư. Public metrics và analytics vẫn ẩn danh." : "The token stays in memory and is sent only to private routes. Public metrics and analytics stay anonymous."}</p></div>
      <form onSubmit={(event) => { void submitConnect(event); }}><label htmlFor="evaluation-token">{vi ? "Local workspace token" : "Local workspace token"}</label><div><input id="evaluation-token" type="password" autoComplete="off" value={tokenDraft} onChange={(event) => setTokenDraft(event.target.value)} /><button type="submit" className="console-btn console-btn--primary" disabled={session.status === "connecting" || !tokenDraft.trim()}>{session.status === "connecting" ? <LoaderCircle className="animate-spin" /> : <Link2 />}{vi ? "Kết nối" : "Connect"}</button></div>{connectErrorStatus !== null && <p role="alert">{pipelineErrorMessage(connectErrorStatus, locale)}</p>}</form>
    </div> : <div className="evaluation-job-layout">
      <div className="evaluation-job-list console-card">
        <div className="console-card__header"><div><h3>{vi ? "Lịch sử job" : "Job history"}</h3><p>{total} {vi ? "job" : "jobs"}</p></div><div className="evaluation-actions"><label>{vi ? "Trạng thái" : "State"}<select value={jobState} onChange={(event) => { setJobState(event.target.value as EvaluationJobState | "all"); setPage(1); }}><option value="all">{vi ? "Tất cả" : "All"}</option>{["queued", "running", "cancelling", "cancelled", "succeeded", "failed", "interrupted"].map((state) => <option value={state} key={state}>{state}</option>)}</select></label><button type="button" className="console-icon-btn" aria-label={vi ? "Làm mới jobs" : "Refresh jobs"} onClick={() => setRefresh((value) => value + 1)}><RefreshCw className={listLoading ? "animate-spin" : ""} /></button></div></div>
        {listError !== null ? <div role="alert" className="evaluation-alert"><AlertTriangle />{evaluationErrorMessage(listError, locale)}</div>
          : listLoading ? <div role="status" className="evaluation-empty"><LoaderCircle className="animate-spin" /><strong>{vi ? "Đang tải jobs…" : "Loading jobs…"}</strong></div>
          : displayedJobs.length === 0 ? <div className="evaluation-empty"><strong>{vi ? "Chưa có evaluation job" : "No evaluation jobs yet"}</strong><p>{vi ? "Tạo job chỉ khi artifact đã đăng ký và ngân sách provider_attempt_slot đã biết." : "Create one only with a registered artifact and a known provider_attempt_slot budget."}</p></div>
          : <div className="evaluation-job-cards">{displayedJobs.map((job) => <button type="button" key={job.id} className={selectedJobId === job.id ? "is-selected" : ""} onClick={() => onSelectJob(job.id)}><span><strong>{job.id}</strong><small>{date(job.created_at, locale)}</small></span><span className={`evaluation-state evaluation-state--${job.state}`}>{stateLabel(job.state)}</span><span>{job.budget_consumed}/{job.frozen.budget_limit} provider_attempt_slot</span></button>)}</div>}
        <nav className="evaluation-pager" aria-label={vi ? "Trang lịch sử job" : "Job history pages"}><button type="button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>{vi ? "Trước" : "Previous"}</button><span>{vi ? "Trang" : "Page"} {page}</span><button type="button" disabled={page * 25 >= total} onClick={() => setPage((value) => value + 1)}>{vi ? "Tiếp" : "Next"}</button></nav>
      </div>
      <aside className="evaluation-job-detail console-card" aria-label={vi ? "Chi tiết evaluation job" : "Evaluation job detail"}>
        {!selectedJobId ? <div className="evaluation-empty"><strong>{vi ? "Chọn một job" : "Select a job"}</strong><p>{vi ? "Chi tiết, steps, receipts và kết quả giữ nguyên theo ID backend." : "Detail, steps, receipts and results remain bound to the backend ID."}</p></div>
          : selected.loading && !selected.job ? <div role="status" className="evaluation-empty"><LoaderCircle className="animate-spin" /><strong>{vi ? "Đang tải job…" : "Loading job…"}</strong></div>
          : selected.errorStatus !== null && !selected.job ? <div role="alert" className="evaluation-alert"><AlertTriangle />{evaluationErrorMessage(selected.errorStatus, locale)}<button type="button" className="console-btn" onClick={selected.reload}>{vi ? "Tải lại" : "Reload"}</button></div>
          : selected.job && <>
            <div className="console-card__header"><div><h3>{selected.job.id}</h3><p>{vi ? "Snapshot frozen · không thể chỉnh sửa" : "Frozen snapshot · not editable"}</p></div><span className={`evaluation-state evaluation-state--${selected.job.state}`}>{selected.job.state}</span></div>
            <div className="console-card__body evaluation-job-body">
              {selected.job.failure && <div role="alert" className={`evaluation-alert ${selected.job.failure.code === "budget_exhausted" ? "evaluation-alert--budget" : ""}`}><AlertTriangle /><div><strong>{selected.job.failure.code}</strong><p>{selected.job.failure.message}</p>{selected.job.failure.code === "budget_exhausted" && <p>{vi ? "Đây là exhaustion của provider_attempt_slot, không phải điểm 0 hoặc model failure." : "This is provider_attempt_slot exhaustion, not a zero score or generic model failure."}</p>}</div></div>}
              {selected.cancelErrorStatus !== null && <div role="alert" className="evaluation-alert"><AlertTriangle />{evaluationErrorMessage(selected.cancelErrorStatus, locale)}</div>}
              {selected.eventErrorStatus !== null && <div className="evaluation-notice"><AlertTriangle />{vi ? "Live update bị gián đoạn; trạng thái bền vững phía trên không đổi." : "Live update was interrupted; the durable state above is unchanged."}</div>}
              <dl className="evaluation-job-facts"><div><dt>{vi ? "Artifact" : "Artifact"}</dt><dd>{selected.job.frozen.artifact_id}</dd></div><div><dt>{vi ? "Dataset" : "Dataset"}</dt><dd>{selected.job.frozen.binding.dataset_id} · {selected.job.frozen.binding.dataset_revision}</dd></div><div><dt>{vi ? "Cases frozen" : "Frozen cases"}</dt><dd>{selected.job.frozen.case_ids.length}</dd></div><div><dt>{vi ? "Ngân sách" : "Budget"}</dt><dd>{selected.job.budget_consumed} / {selected.job.frozen.budget_limit} {selected.job.frozen.budget_unit}</dd></div><div><dt>{vi ? "Tiến độ bền vững" : "Durable progress"}</dt><dd>{progress?.current === null || progress?.total === null ? (vi ? "Không rõ" : "Unknown") : `${progress.current} / ${progress.total}`} {progress?.stage ? `· ${progress.stage}` : ""}</dd></div><div><dt>{vi ? "Publication" : "Publication"}</dt><dd>{selected.job.publication_status}</dd></div></dl>
              <section className="evaluation-steps" aria-labelledby="evaluation-job-steps"><h4 id="evaluation-job-steps">{vi ? "Hai bước bền vững" : "Two durable steps"}</h4><ol>{selected.job.steps.map((step) => <li key={step.step_id}><span>{step.ordinal}</span><div><strong>{step.name}</strong><small>{step.state}</small></div></li>)}</ol></section>
              <details><summary>{vi ? "Binding và provenance frozen" : "Frozen binding and provenance"}</summary><dl className="evaluation-provenance"><div><dt>Protocol</dt><dd>{selected.job.frozen.protocol} v{selected.job.frozen.protocol_version}</dd></div><div><dt>Engine</dt><dd>{selected.job.frozen.engine} v{selected.job.frozen.engine_version}</dd></div><div><dt>Generator</dt><dd>{selected.job.frozen.binding.generator_model_id}</dd></div><div><dt>Judge</dt><dd>{selected.job.frozen.binding.judge_model_id ?? (vi ? "Chưa được báo cáo" : "Not reported")}</dd></div><div><dt>Snapshot digest</dt><dd>{selected.job.frozen.snapshot_digest}</dd></div><div><dt>{vi ? "Yêu cầu tối đa" : "Maximum required attempts"}</dt><dd>{selected.job.frozen.maximum_required_attempts} {selected.job.frozen.budget_unit}</dd></div></dl></details>
              {selected.results && <NativeCases items={selected.results.items} definitions={jobDefinitions} total={selected.results.total} page={selected.results.page} pageSize={selected.results.page_size} onPage={setResultPage} locale={locale} />}
              <div className="evaluation-job-actions"><button type="button" className="console-btn" onClick={selected.reload}><RefreshCw />{vi ? "Đối chiếu lại" : "Reconcile"}</button><button type="button" className="console-btn console-btn--danger" disabled={!session.canExecute || selected.cancelling || !["queued", "running"].includes(selected.job.state)} onClick={() => { void selected.cancel(); }}><Square />{selected.cancelling ? (vi ? "Đang yêu cầu…" : "Requesting…") : (vi ? "Yêu cầu hủy" : "Request cancellation")}</button></div>
              {terminal.has(selected.job.state) && <p className="evaluation-note">{selected.job.state === "interrupted" ? (vi ? "Interrupted là terminal. Backend không hỗ trợ resume/retry/restart." : "Interrupted is terminal. The backend provides no resume, retry, or restart action.") : (vi ? `Trạng thái terminal: ${selected.job.state}.` : `Terminal state: ${selected.job.state}.`)}</p>}
            </div>
          </>}
      </aside>
    </div>}
    <ModalDialog open={createOpen} onClose={() => { if (!creation.busy) setCreateOpen(false); }} labelledBy="evaluation-create-title" describedBy="evaluation-create-description" initialFocusRef={firstCreateControl} className="evaluation-modal">
      <header><div><h2 id="evaluation-create-title">{vi ? "Tạo evaluation frozen" : "Create a frozen evaluation"}</h2><p id="evaluation-create-description">{vi ? "Backend sẽ freeze dataset, case order, metrics, evidence, model, prompt, runtime và budget." : "The backend freezes dataset, case order, metrics, evidence, model, prompts, runtime and budget."}</p></div><button type="button" className="console-icon-btn" aria-label={vi ? "Đóng" : "Close"} disabled={creation.busy} onClick={() => setCreateOpen(false)}><X /></button></header>
      <div className="evaluation-modal__body"><label htmlFor="evaluation-artifact">{vi ? "Artifact ID đã đăng ký" : "Registered artifact ID"}</label><input ref={firstCreateControl} id="evaluation-artifact" value={artifactId} onChange={(event) => setArtifactId(event.target.value)} maxLength={100} autoComplete="off" /><small>A-Z, a-z, 0-9, dot, underscore or hyphen; no path.</small><label htmlFor="evaluation-budget">{vi ? "Ngân sách provider attempt slot" : "Provider attempt slot budget"}</label><input id="evaluation-budget" type="number" min={1} max={15000} step={1} value={budget} onChange={(event) => setBudget(event.target.value)} /><small>{vi ? "1–15.000 provider_attempt_slot. Không phải USD, credits hoặc tokens. Backend kiểm tra giới hạn và preflight." : "1–15,000 provider_attempt_slot. Not USD, credits or tokens. The backend owns limits and preflight."}</small><div className="evaluation-modal__metrics"><strong>{vi ? "Sáu metric native frozen" : "Six frozen native metrics"}</strong>{definitions.map((definition) => <span key={definition.metric_id}>{definition.label} · v{definition.metric_version}</span>)}</div>{creation.errorStatus !== null && <div role="alert" className="evaluation-alert"><AlertTriangle />{evaluationErrorMessage(creation.errorStatus, locale)}</div>}</div>
      <footer><button type="button" className="console-btn" disabled={creation.busy} onClick={() => setCreateOpen(false)}>{vi ? "Đóng" : "Close"}</button><button type="button" className="console-btn console-btn--primary" disabled={!createValid || creation.busy} onClick={create}>{creation.busy ? <LoaderCircle className="animate-spin" /> : <Play />}{vi ? "Freeze và xếp hàng" : "Freeze and queue"}</button></footer>
    </ModalDialog>
  </section>;
}
