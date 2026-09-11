import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowRight, BarChart3, CheckCircle2, CircleSlash2, Download, FileJson, RefreshCw, ShieldAlert } from "lucide-react";
import { getEvaluationRun, getEvaluationRuns } from "../lib/api";
import { RECORDED_EVALUATION_RUN } from "../lib/recordedEvaluation";
import { EvaluationRun, EvaluationRunStatus } from "../types";
import { useLocale } from "../lib/i18n";
import { compareEvaluationRuns, EvaluationComparison } from "../lib/evaluationComparison";
import { describeRequestError } from "../lib/requestError";
import { SelectField } from "./ui/SelectField";
import { getWorkspaceNavItem } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";

type EvaluationMode = "live" | "recorded";
const WORKSPACE_META = getWorkspaceNavItem("evaluation");

function score(value: number | undefined): string {
  return value === undefined ? "—" : value.toFixed(3);
}

function csvCell(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

function CaseStatusIcon({ status }: { status: EvaluationRun["cases"][number]["status"] }) {
  if (status === "OK") return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />;
  if (status === "ERROR") return <AlertCircle className="h-3.5 w-3.5 text-rose-600 dark:text-rose-300" aria-hidden="true" />;
  return <CircleSlash2 className="h-3.5 w-3.5 text-amber-600 dark:text-amber-300" aria-hidden="true" />;
}

export function EvaluationPanel() {
  const { locale, t } = useLocale();
  const vi = locale === "vi";
  const ToolIcon = getSemanticIcon(WORKSPACE_META.icon);
  const [mode, setMode] = useState<EvaluationMode>("live");
  const [status, setStatus] = useState<EvaluationRunStatus | "">("");
  const [runs, setRuns] = useState<Array<{ run_id: string; title: string; status: EvaluationRunStatus; created_at: string; aggregate: Record<string, number>; case_count: number }>>([]);
  const [selected, setSelected] = useState<EvaluationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<EvaluationRun | null>(null);
  const [comparisonId, setComparisonId] = useState("");
  const listRequestId = useRef(0);
  const runRequestId = useRef(0);
  const selectedRunAbortRef = useRef<AbortController | null>(null);

  const load = useCallback(() => {
    const requestId = ++listRequestId.current;
    selectedRunAbortRef.current?.abort();
    selectedRunAbortRef.current = null;
    runRequestId.current += 1;
    setComparisonId("");
    setComparison(null);
    if (mode === "recorded") {
      setSelected(RECORDED_EVALUATION_RUN);
      setRuns([{
        run_id: RECORDED_EVALUATION_RUN.run_id,
        title: RECORDED_EVALUATION_RUN.title,
        status: RECORDED_EVALUATION_RUN.status,
        created_at: RECORDED_EVALUATION_RUN.created_at,
        aggregate: RECORDED_EVALUATION_RUN.aggregate,
        case_count: RECORDED_EVALUATION_RUN.cases.length,
      }]);
      setError(null);
      setLoading(false);
      return undefined;
    }
    setLoading(true);
    setError(null);
    setSelected(null);
    const controller = new AbortController();
    void getEvaluationRuns({ status: status || null }, controller.signal)
      .then((response) => {
        if (requestId !== listRequestId.current) return;
        setRuns(response.items);
        if (response.items[0]) {
          const selectedId = ++runRequestId.current;
          return getEvaluationRun(response.items[0].run_id, controller.signal).then((run) => {
            if (requestId === listRequestId.current && selectedId === runRequestId.current) setSelected(run);
          });
        }
        setSelected(null);
        return undefined;
      })
      .catch((reason) => {
        if (requestId !== listRequestId.current) return;
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(describeRequestError(reason, vi ? "Không thể tải báo cáo evaluation." : "Could not load evaluation reports.", vi ? "vi" : "en").message);
        setRuns([]);
        setSelected(null);
      })
      .finally(() => { if (requestId === listRequestId.current) setLoading(false); });
    return () => controller.abort();
  }, [mode, status, vi]);

  useEffect(() => {
    const cleanup = load();
    return typeof cleanup === "function" ? cleanup : undefined;
  }, [load]);

  useEffect(() => () => selectedRunAbortRef.current?.abort(), []);

  useEffect(() => {
    if (mode === "recorded" || !comparisonId) {
      setComparison(null);
      return;
    }
    const controller = new AbortController();
    const requestId = ++runRequestId.current;
    void getEvaluationRun(comparisonId, controller.signal).then((run) => {
      if (requestId === runRequestId.current) setComparison(run);
    }).catch((reason) => {
      if (requestId === runRequestId.current && !(reason instanceof DOMException && reason.name === "AbortError")) setComparison(null);
    });
    return () => controller.abort();
  }, [comparisonId, mode]);

  const selectRun = (runId: string) => {
    if (mode === "recorded") {
      setSelected(RECORDED_EVALUATION_RUN);
      return;
    }
    selectedRunAbortRef.current?.abort();
    const controller = new AbortController();
    selectedRunAbortRef.current = controller;
    const requestId = ++runRequestId.current;
    setSelected(null);
    setError(null);
    void getEvaluationRun(runId, controller.signal).then((run) => {
      if (requestId === runRequestId.current) setSelected(run);
    }).catch((reason) => {
      if (requestId === runRequestId.current && !(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(describeRequestError(reason, vi ? "Không thể tải chi tiết report." : "Could not load report details.", vi ? "vi" : "en").message);
      }
    });
  };

  const selectedCases = useMemo(() => selected?.cases ?? [], [selected]);
  const comparisonResult: EvaluationComparison | null = useMemo(
    () => selected && comparison ? compareEvaluationRuns(comparison, selected) : null,
    [comparison, selected],
  );

  const downloadSelected = (format: "json" | "csv") => {
    if (!selected) return;
    const content = format === "json"
      ? JSON.stringify(selected, null, 2)
      : [
          ["case_id", "language", "status", "question", "answer", "scores", "gates"].join(","),
          ...selected.cases.map((item) => [
            item.case_id,
            item.language,
            item.status,
            item.question,
            item.answer ?? "",
            item.scores,
            item.gates,
          ].map(csvCell).join(",")),
        ].join("\n");
    const blob = new Blob([content], {
      type: format === "json" ? "application/json" : "text/csv",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selected.run_id}.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="workspace-page workspace-page--wide evaluation-panel" aria-labelledby="evaluation-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="workspace-eyebrow text-violet-600 dark:text-violet-300"><ToolIcon className="h-3.5 w-3.5" aria-hidden="true" />{t(WORKSPACE_META.labelKey)}</p>
          <h1 id="evaluation-title" className="mt-1 text-2xl font-bold text-[var(--text-primary)]">{vi ? "Evaluation & experiments" : "Evaluation & experiments"}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--text-muted)]">{t(WORKSPACE_META.descriptionKey)} {vi ? "Recorded mode không gọi provider." : "Recorded mode never calls a provider."}</p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <SelectField className="min-w-36" label={vi ? "Nguồn" : "Mode"} value={mode} onValueChange={(value) => setMode(value as EvaluationMode)} options={[{ value: "live", label: vi ? "Live published" : "Live published" }, { value: "recorded", label: vi ? "Recorded demo" : "Recorded demo" }]} />
          {mode === "live" && <SelectField className="min-w-32" label={vi ? "Trạng thái" : "Status"} value={status} onValueChange={(value) => setStatus(value as EvaluationRunStatus | "")} options={[{ value: "", label: vi ? "Tất cả" : "All" }, { value: "official", label: "Official" }, { value: "candidate", label: "Candidate" }, { value: "historical", label: "Historical" }, { value: "incomplete", label: "Incomplete" }]} />}
          <button type="button" onClick={load} className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-[var(--border-subtle)] px-3 text-xs font-semibold text-[var(--text-primary)] hover:surface-muted-hover" aria-label={vi ? "Tải lại evaluation" : "Refresh evaluation"}><RefreshCw className="h-3.5 w-3.5" />{vi ? "Tải lại" : "Refresh"}</button>
        </div>
      </div>

      <section className="evaluation-workflow-guide" aria-labelledby="evaluation-workflow-title">
        <div>
          <h2 id="evaluation-workflow-title">{vi ? "Cách đọc evaluation" : "How evaluation works"}</h2>
          <p>{vi ? "Evaluation là báo cáo chỉ đọc về chất lượng và các gate đã ghi nhận; trang này không tự chạy provider." : "Evaluation is a read-only report of recorded quality scores and gates; this page never starts provider execution."}</p>
        </div>
        <ol>
          <li>{vi ? "Chọn report publish hoặc Recorded demo." : "Choose a published report or a recorded demo."}</li>
          <li>{vi ? "Mở case để xem answer, evidence và trạng thái." : "Open a case to inspect its answer, evidence, and status."}</li>
          <li>{vi ? "Chỉ so sánh các run có binding tương thích." : "Compare only runs with compatible evaluation bindings."}</li>
        </ol>
      </section>

      {error && <div role="alert" className="mt-5 flex items-center gap-2 rounded-xl state-warning-surface p-3 text-sm"><ShieldAlert className="h-4 w-4 shrink-0" />{error}</div>}
      {loading && <div className="mt-5 flex items-center gap-2 text-sm text-[var(--text-muted)]" role="status"><RefreshCw className="h-4 w-4 animate-spin" />{vi ? "Đang tải report..." : "Loading reports..."}</div>}
      {!loading && !error && runs.length === 0 && mode === "live" && <div className="mt-5 rounded-2xl border border-dashed border-[var(--border-strong)] p-8 text-center"><FileJson className="mx-auto h-8 w-8 text-[var(--text-subtle)]" /><p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">{vi ? "Chưa có report publish" : "No published reports yet"}</p><p className="mt-1 text-xs text-[var(--text-muted)]">{vi ? "Không có report live để mở. Bạn có thể xem một ví dụ đã ghi mà không gọi provider." : "There is no live report to open. You can view a recorded example without calling a provider."}</p><button type="button" className="workspace-link-button mt-4" onClick={() => setMode("recorded")}>{vi ? "Xem ví dụ đã ghi" : "View recorded example"}<ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></button></div>}

      {!loading && runs.length > 0 && <div className="evaluation-run-grid mt-5">
        <div className="space-y-2" aria-label={vi ? "Danh sách evaluation run" : "Evaluation run list"}>
          {runs.map((run) => <button key={run.run_id} type="button" onClick={() => selectRun(run.run_id)} className={`w-full rounded-xl border p-3 text-left transition-colors ${selected?.run_id === run.run_id ? "border-violet-500 bg-violet-500/10" : "border-[var(--border-subtle)] surface-raised hover:surface-muted-hover"}`}><div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold text-[var(--text-primary)]">{run.title}</span><span className="rounded-full border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{run.status}</span></div><div className="mt-2 text-xs text-[var(--text-muted)]">{run.case_count} cases · {new Date(run.created_at).toLocaleDateString()}</div></button>)}
        </div>
        {selected ? <article className="min-w-0 rounded-2xl border border-[var(--border-subtle)] surface-raised p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div className="min-w-0 break-words text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]"><BarChart3 className="mr-2 inline-block h-4 w-4 text-violet-600 dark:text-violet-300" />{selected.status} · {selected.run_id}</div><div className="flex shrink-0 items-center gap-1"><button type="button" onClick={() => downloadSelected("json")} className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-2 text-[10px] font-semibold text-[var(--text-primary)] hover:surface-muted-hover" aria-label={vi ? "Xuất evaluation JSON" : "Export evaluation JSON"}><Download className="h-3 w-3" />JSON</button><button type="button" onClick={() => downloadSelected("csv")} className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-2 text-[10px] font-semibold text-[var(--text-primary)] hover:surface-muted-hover" aria-label={vi ? "Xuất evaluation CSV" : "Export evaluation CSV"}><Download className="h-3 w-3" />CSV</button></div></div><h2 className="mt-2 break-words text-lg font-bold text-[var(--text-primary)]">{selected.title}</h2><div className="evaluation-metrics-grid mt-4">{Object.entries(selected.aggregate).map(([key, value]) => <div key={key} className="min-w-0 rounded-xl bg-[var(--surface-muted)] p-3"><div className="break-words text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{key.replaceAll("_", " ")}</div><div className="mt-1 text-lg font-bold text-[var(--text-primary)]">{key === "sample_count" ? value : score(value)}</div></div>)}</div>
          {mode === "live" && runs.length > 1 && <div className="mt-5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3"><div className="flex flex-wrap items-end gap-2"><SelectField className="min-w-52" label={vi ? "So sánh paired experiment" : "Paired experiment comparison"} value={comparisonId} onValueChange={setComparisonId} options={[{ value: "", label: vi ? "Chọn run..." : "Choose run..." }, ...runs.filter((run) => run.run_id !== selected.run_id).map((run) => ({ value: run.run_id, label: run.title }))]} /></div>{comparisonResult && (comparisonResult.compatible ? <div className="mt-3 grid gap-2 sm:grid-cols-2">{comparisonResult.metrics.map((metric) => <div key={metric.metric} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-2 text-xs"><div className="font-semibold text-[var(--text-primary)]">{metric.metric} Δ {metric.delta.toFixed(3)}</div><div className="mt-1 text-[var(--text-muted)]">95% CI [{metric.lower95.toFixed(3)}, {metric.upper95.toFixed(3)}] · n={metric.sampleCount} · {metric.resamples} resamples (seed {metric.seed})</div></div>)}</div> : <p className="mt-2 text-xs text-[var(--state-warning-text)]">{comparisonResult.reason}</p>)}</div>}
          <div className="mt-5 space-y-2">{selectedCases.map((item) => <details key={item.case_id} className="rounded-xl border border-[var(--border-subtle)] p-3"><summary className="evaluation-case-summary cursor-pointer text-sm font-semibold text-[var(--text-primary)]"><span className="text-[10px] uppercase text-[var(--text-muted)]">{item.language}</span><span className="min-w-0 break-words">{item.question}</span><span className={`inline-flex items-center gap-1 text-xs ${item.status === "OK" ? "text-emerald-600 dark:text-emerald-300" : item.status === "ERROR" ? "text-rose-600 dark:text-rose-300" : "text-amber-600 dark:text-amber-300"}`}><CaseStatusIcon status={item.status} />{item.status}</span></summary><p className="mt-3 text-sm leading-relaxed text-[var(--text-muted)]">{item.answer ?? (vi ? "Không có câu trả lời." : "No answer recorded.")}</p>{item.evidence.map((evidence) => <div key={evidence.citation} className="mt-2 rounded-lg bg-[var(--surface-muted)] p-2 text-xs text-[var(--text-muted)]"><strong className="text-[var(--text-primary)]">{evidence.citation}</strong><div className="mt-1">{evidence.excerpt}</div></div>)}</details>)}</div><p className="mt-4 text-xs text-[var(--text-muted)]">{selected.notes.join(" ")}</p></article> : <div className="rounded-2xl border border-dashed border-[var(--border-strong)] p-8 text-center text-sm text-[var(--text-muted)]">{vi ? "Chọn một run để xem case, scores và evidence." : "Select a run to inspect cases, scores, and evidence."}</div>}
      </div>}
    </section>
  );
}
