import { useEffect, useMemo, useState } from "react";
import { BarChart3, CheckCircle2, Download, FileJson, RefreshCw, ShieldAlert } from "lucide-react";
import { getEvaluationRun, getEvaluationRuns } from "../lib/api";
import { RECORDED_EVALUATION_RUN } from "../lib/recordedEvaluation";
import { EvaluationRun, EvaluationRunStatus } from "../types";
import { useLocale } from "../lib/i18n";
import { compareEvaluationRuns, EvaluationComparison } from "../lib/evaluationComparison";

type EvaluationMode = "live" | "recorded";

function score(value: number | undefined): string {
  return value === undefined ? "—" : value.toFixed(3);
}

function csvCell(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

export function EvaluationPanel() {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [mode, setMode] = useState<EvaluationMode>("live");
  const [status, setStatus] = useState<EvaluationRunStatus | "">("");
  const [runs, setRuns] = useState<Array<{ run_id: string; title: string; status: EvaluationRunStatus; created_at: string; aggregate: Record<string, number>; case_count: number }>>([]);
  const [selected, setSelected] = useState<EvaluationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<EvaluationRun | null>(null);
  const [comparisonId, setComparisonId] = useState("");

  const load = () => {
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
      return;
    }
    setLoading(true);
    setError(null);
    const controller = new AbortController();
    void getEvaluationRuns({ status: status || null }, controller.signal)
      .then((response) => {
        setRuns(response.items);
        if (response.items[0]) {
          return getEvaluationRun(response.items[0].run_id, controller.signal).then(setSelected);
        }
        setSelected(null);
        return undefined;
      })
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : String(reason));
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  };

  useEffect(() => {
    const cleanup = load();
    return typeof cleanup === "function" ? cleanup : undefined;
  }, [mode, status]);

  useEffect(() => {
    if (mode === "recorded" || !comparisonId) {
      setComparison(null);
      return;
    }
    const controller = new AbortController();
    void getEvaluationRun(comparisonId, controller.signal).then(setComparison).catch((reason) => {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) setComparison(null);
    });
    return () => controller.abort();
  }, [comparisonId, mode]);

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
    <section className="mx-auto w-full max-w-6xl px-3 py-6 md:px-6" aria-labelledby="evaluation-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600 dark:text-violet-300">{vi ? "Đánh giá có kiểm chứng" : "Verifiable evaluation"}</p>
          <h1 id="evaluation-title" className="mt-1 text-2xl font-bold text-[var(--text-primary)]">{vi ? "Evaluation & experiments" : "Evaluation & experiments"}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--text-muted)]">{vi ? "Chỉ report đã publish và có provenance mới được hiển thị. Recorded mode không gọi provider." : "Only published reports with provenance are shown. Recorded mode never calls a provider."}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs font-semibold text-[var(--text-muted)]">{vi ? "Nguồn" : "Mode"}
            <select aria-label={vi ? "Nguồn đánh giá" : "Evaluation mode"} value={mode} onChange={(event) => setMode(event.target.value as EvaluationMode)} className="control-select ml-2 min-h-9 py-1 text-xs">
              <option value="live">{vi ? "Live published" : "Live published"}</option>
              <option value="recorded">{vi ? "Recorded demo" : "Recorded demo"}</option>
            </select>
          </label>
          {mode === "live" && <label className="text-xs font-semibold text-[var(--text-muted)]">{vi ? "Trạng thái" : "Status"}
            <select aria-label={vi ? "Trạng thái report" : "Report status"} value={status} onChange={(event) => setStatus(event.target.value as EvaluationRunStatus | "")} className="control-select ml-2 min-h-9 py-1 text-xs">
              <option value="">{vi ? "Tất cả" : "All"}</option>
              <option value="official">Official</option><option value="candidate">Candidate</option><option value="historical">Historical</option><option value="incomplete">Incomplete</option>
            </select>
          </label>}
          <button type="button" onClick={load} className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-[var(--border-subtle)] px-3 text-xs font-semibold text-[var(--text-primary)] hover:surface-muted-hover" aria-label={vi ? "Tải lại evaluation" : "Refresh evaluation"}><RefreshCw className="h-3.5 w-3.5" />{vi ? "Tải lại" : "Refresh"}</button>
        </div>
      </div>

      {error && <div role="alert" className="mt-5 flex items-center gap-2 rounded-xl state-warning-surface p-3 text-sm"><ShieldAlert className="h-4 w-4 shrink-0" />{error}</div>}
      {loading && <div className="mt-5 flex items-center gap-2 text-sm text-[var(--text-muted)]" role="status"><RefreshCw className="h-4 w-4 animate-spin" />{vi ? "Đang tải report..." : "Loading reports..."}</div>}
      {!loading && !error && runs.length === 0 && mode === "live" && <div className="mt-5 rounded-2xl border border-dashed border-[var(--border-strong)] p-8 text-center"><FileJson className="mx-auto h-8 w-8 text-[var(--text-subtle)]" /><p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">{vi ? "Chưa có report publish" : "No published reports yet"}</p><p className="mt-1 text-xs text-[var(--text-muted)]">{vi ? "Chuyển sang Recorded demo để xem luồng dashboard mà không gọi provider." : "Switch to Recorded demo to preview the dashboard without provider calls."}</p></div>}

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(230px,0.7fr)_minmax(0,1.3fr)]">
        <div className="space-y-2">
          {runs.map((run) => <button key={run.run_id} type="button" onClick={() => mode === "recorded" ? setSelected(RECORDED_EVALUATION_RUN) : void getEvaluationRun(run.run_id).then(setSelected)} className={`w-full rounded-xl border p-3 text-left transition-colors ${selected?.run_id === run.run_id ? "border-violet-500 bg-violet-500/10" : "border-[var(--border-subtle)] surface-raised hover:surface-muted-hover"}`}><div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold text-[var(--text-primary)]">{run.title}</span><span className="rounded-full border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{run.status}</span></div><div className="mt-2 text-xs text-[var(--text-muted)]">{run.case_count} cases · {new Date(run.created_at).toLocaleDateString()}</div></button>)}
        </div>
        {selected ? <article className="rounded-2xl border border-[var(--border-subtle)] surface-raised p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]"><BarChart3 className="h-4 w-4 text-violet-600 dark:text-violet-300" />{selected.status} · {selected.run_id}</div><div className="flex items-center gap-1"><button type="button" onClick={() => downloadSelected("json")} className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-2 text-[10px] font-semibold text-[var(--text-primary)] hover:surface-muted-hover" aria-label={vi ? "Xuất evaluation JSON" : "Export evaluation JSON"}><Download className="h-3 w-3" />JSON</button><button type="button" onClick={() => downloadSelected("csv")} className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-2 text-[10px] font-semibold text-[var(--text-primary)] hover:surface-muted-hover" aria-label={vi ? "Xuất evaluation CSV" : "Export evaluation CSV"}><Download className="h-3 w-3" />CSV</button></div></div><h2 className="mt-2 text-lg font-bold text-[var(--text-primary)]">{selected.title}</h2><div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">{Object.entries(selected.aggregate).map(([key, value]) => <div key={key} className="rounded-xl bg-[var(--surface-muted)] p-3"><div className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{key.replaceAll("_", " ")}</div><div className="mt-1 text-lg font-bold text-[var(--text-primary)]">{key === "sample_count" ? value : score(value)}</div></div>)}</div>
          {mode === "live" && runs.length > 1 && <div className="mt-5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3"><div className="flex flex-wrap items-center gap-2"><span className="text-xs font-semibold text-[var(--text-primary)]">{vi ? "So sánh paired experiment" : "Paired experiment comparison"}</span><select aria-label={vi ? "Chọn run đối chiếu" : "Choose comparison run"} value={comparisonId} onChange={(event) => setComparisonId(event.target.value)} className="control-select min-h-8 text-xs"><option value="">{vi ? "Chọn run..." : "Choose run..."}</option>{runs.filter((run) => run.run_id !== selected.run_id).map((run) => <option key={run.run_id} value={run.run_id}>{run.title}</option>)}</select></div>{comparisonResult && (comparisonResult.compatible ? <div className="mt-3 grid gap-2 sm:grid-cols-2">{comparisonResult.metrics.map((metric) => <div key={metric.metric} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-2 text-xs"><div className="font-semibold text-[var(--text-primary)]">{metric.metric} Δ {metric.delta.toFixed(3)}</div><div className="mt-1 text-[var(--text-muted)]">95% CI [{metric.lower95.toFixed(3)}, {metric.upper95.toFixed(3)}] · n={metric.sampleCount} · {metric.resamples} resamples (seed {metric.seed})</div></div>)}</div> : <p className="mt-2 text-xs text-[var(--state-warning-text)]">{comparisonResult.reason}</p>)}</div>}
          <div className="mt-5 space-y-2">{selectedCases.map((item) => <details key={item.case_id} className="rounded-xl border border-[var(--border-subtle)] p-3"><summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)]"><span className="mr-2 text-[10px] uppercase text-[var(--text-muted)]">{item.language}</span>{item.question}<span className="float-right inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-300"><CheckCircle2 className="h-3.5 w-3.5" />{item.status}</span></summary><p className="mt-3 text-sm leading-relaxed text-[var(--text-muted)]">{item.answer ?? (vi ? "Không có câu trả lời." : "No answer recorded.")}</p>{item.evidence.map((evidence) => <div key={evidence.citation} className="mt-2 rounded-lg bg-[var(--surface-muted)] p-2 text-xs text-[var(--text-muted)]"><strong className="text-[var(--text-primary)]">{evidence.citation}</strong><div className="mt-1">{evidence.excerpt}</div></div>)}</details>)}</div><p className="mt-4 text-xs text-[var(--text-muted)]">{selected.notes.join(" ")}</p></article> : <div className="rounded-2xl border border-dashed border-[var(--border-strong)] p-8 text-center text-sm text-[var(--text-muted)]">{vi ? "Chọn một run để xem case, scores và evidence." : "Select a run to inspect cases, scores, and evidence."}</div>}
      </div>
    </section>
  );
}
