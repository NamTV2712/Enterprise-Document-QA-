import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  CircleSlash2,
  Download,
  FileJson,
  LineChart,
  RefreshCw,
  Search,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { getEvaluationRun, getEvaluationRuns } from "../lib/api";
import { EvaluationRun, EvaluationRunStatus } from "../types";
import { useLocale } from "../lib/i18n";
import { compareEvaluationRuns, EvaluationComparison } from "../lib/evaluationComparison";
import { describeRequestError } from "../lib/requestError";
import { SelectField } from "./ui/SelectField";

const METRIC_COLORS = ["var(--primary)", "var(--success)", "#A855F7", "#D97706"];
const PREFERRED_METRICS = ["faithfulness", "answer_relevancy", "context_precision", "overall"];

function score(value: number | undefined): string {
  return value === undefined ? "—" : value.toFixed(3);
}

function metricLabel(key: string): string {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function csvCell(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

/** Derive a bounded 0..1 case score for distribution buckets. */
function caseOverall(item: EvaluationRun["cases"][number]): number | null {
  const values = Object.values(item.scores).filter((value) => typeof value === "number" && Number.isFinite(value));
  if (values.length === 0) return null;
  const overall = item.scores.overall;
  if (typeof overall === "number" && overall >= 0 && overall <= 1) return overall;
  const bounded = values.filter((value) => value >= 0 && value <= 1);
  if (bounded.length === 0) return null;
  return bounded.reduce((sum, value) => sum + value, 0) / bounded.length;
}

function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null;
  const width = 88;
  const height = 30;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * (width - 6) + 3;
    const y = height - 4 - ((value - min) / span) * (height - 8);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg className="console-spark" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline className="console-spark__line" style={{ stroke: color }} points={points.join(" ")} />
      <circle className="console-spark__dot" style={{ fill: color }} cx={points[points.length - 1].split(",")[0]} cy={points[points.length - 1].split(",")[1]} r="2.5" />
    </svg>
  );
}

function CaseStatusIcon({ status }: { status: EvaluationRun["cases"][number]["status"] }) {
  if (status === "OK") return <CheckCircle2 className="h-3.5 w-3.5" style={{ color: "var(--success)" }} aria-hidden="true" />;
  if (status === "ERROR") return <AlertCircle className="h-3.5 w-3.5" style={{ color: "var(--danger)" }} aria-hidden="true" />;
  return <CircleSlash2 className="h-3.5 w-3.5" style={{ color: "var(--warning)" }} aria-hidden="true" />;
}

export function EvaluationPanel() {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [status, setStatus] = useState<EvaluationRunStatus | "">("");
  const [runs, setRuns] = useState<Array<{ run_id: string; title: string; status: EvaluationRunStatus; created_at: string; aggregate: Record<string, number>; case_count: number }>>([]);
  const [selected, setSelected] = useState<EvaluationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<EvaluationRun | null>(null);
  const [comparisonId, setComparisonId] = useState("");
  const [runFilter, setRunFilter] = useState("");
  const listRequestId = useRef(0);
  const selectedRunRequestId = useRef(0);
  const comparisonRequestId = useRef(0);
  const selectedRunAbortRef = useRef<AbortController | null>(null);

  const load = useCallback(() => {
    const requestId = ++listRequestId.current;
    selectedRunAbortRef.current?.abort();
    selectedRunAbortRef.current = null;
    selectedRunRequestId.current += 1;
    comparisonRequestId.current += 1;
    setComparisonId("");
    setComparison(null);
    setLoading(true);
    setError(null);
    setSelected(null);
    const controller = new AbortController();
    void getEvaluationRuns({ status: status || null }, controller.signal)
      .then((response) => {
        if (requestId !== listRequestId.current) return;
        setRuns(response.items);
        if (response.items[0]) {
          const selectedId = ++selectedRunRequestId.current;
          return getEvaluationRun(response.items[0].run_id, controller.signal).then((run) => {
            if (requestId === listRequestId.current && selectedId === selectedRunRequestId.current) setSelected(run);
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
  }, [status, vi]);

  useEffect(() => {
    const cleanup = load();
    return typeof cleanup === "function" ? cleanup : undefined;
  }, [load]);

  useEffect(() => () => selectedRunAbortRef.current?.abort(), []);

  useEffect(() => {
    if (!comparisonId) {
      setComparison(null);
      return;
    }
    const controller = new AbortController();
    const requestId = ++comparisonRequestId.current;
    void getEvaluationRun(comparisonId, controller.signal).then((run) => {
      if (requestId === comparisonRequestId.current) setComparison(run);
    }).catch((reason) => {
      if (requestId === comparisonRequestId.current && !(reason instanceof DOMException && reason.name === "AbortError")) setComparison(null);
    });
    return () => controller.abort();
  }, [comparisonId]);

  const selectRun = (runId: string) => {
    selectedRunAbortRef.current?.abort();
    const controller = new AbortController();
    selectedRunAbortRef.current = controller;
    const requestId = ++selectedRunRequestId.current;
    setSelected(null);
    setError(null);
    void getEvaluationRun(runId, controller.signal).then((run) => {
      if (requestId === selectedRunRequestId.current) setSelected(run);
    }).catch((reason) => {
      if (requestId === selectedRunRequestId.current && !(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(describeRequestError(reason, vi ? "Không thể tải chi tiết report." : "Could not load report details.", vi ? "vi" : "en").message);
      }
    });
  };

  const selectedCases = useMemo(() => selected?.cases ?? [], [selected]);
  const comparisonResult: EvaluationComparison | null = useMemo(
    () => selected && comparison ? compareEvaluationRuns(comparison, selected) : null,
    [comparison, selected],
  );

  /** KPI metrics from the selected run, ordered by the preferred metric names. */
  const kpis = useMemo(() => {
    if (!selected) return [];
    const keys = Object.keys(selected.aggregate)
      .filter((key) => typeof selected.aggregate[key] === "number")
      .sort((left, right) => {
        const leftIndex = PREFERRED_METRICS.indexOf(left);
        const rightIndex = PREFERRED_METRICS.indexOf(right);
        return (leftIndex === -1 ? 99 : leftIndex) - (rightIndex === -1 ? 99 : rightIndex);
      })
      .slice(0, 5);
    const selectedIndex = runs.findIndex((run) => run.run_id === selected.run_id);
    const previous = selectedIndex >= 0 ? runs[selectedIndex + 1] : undefined;
    return keys.map((key) => {
      const values = [selected.aggregate[key], ...runs.map((run) => run.aggregate[key]).filter((value): value is number => typeof value === "number")].reverse();
      const previousValue = previous?.aggregate[key];
      const delta = typeof previousValue === "number" ? selected.aggregate[key] - previousValue : null;
      return { key, value: selected.aggregate[key], delta, values, isCount: key === "sample_count" };
    });
  }, [runs, selected]);

  /** Trend series across published runs, oldest to newest. */
  const trend = useMemo(() => {
    const chronological = [...runs].sort((left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime());
    if (chronological.length < 2) return null;
    const metricKeys = PREFERRED_METRICS.filter((key) => chronological.every((run) => typeof run.aggregate[key] === "number"));
    if (metricKeys.length === 0) return null;
    return {
      runs: chronological,
      metricKeys,
    };
  }, [runs]);

  const distribution = useMemo(() => {
    const buckets = [
      { label: "< 0.60", min: -1, max: 0.6, color: "var(--danger)", count: 0 },
      { label: "0.60 – 0.80", min: 0.6, max: 0.8, color: "#F59E0B", count: 0 },
      { label: "0.80 – 0.90", min: 0.8, max: 0.9, color: "var(--primary)", count: 0 },
      { label: "0.90 – <1.0", min: 0.9, max: 1, color: "#14B8A6", count: 0 },
      { label: "1.0", min: 1, max: 1.0000001, color: "var(--success)", count: 0 },
    ];
    let scored = 0;
    for (const item of selectedCases) {
      const overall = caseOverall(item);
      if (overall === null) continue;
      scored += 1;
      const bucket = buckets.find((candidate) => overall >= candidate.min && overall < candidate.max) ?? buckets[buckets.length - 1];
      bucket.count += 1;
    }
    if (scored === 0) return null;
    const max = Math.max(...buckets.map((bucket) => bucket.count));
    return { buckets, max };
  }, [selectedCases]);

  const filteredRuns = useMemo(() => {
    const needle = runFilter.trim().toLowerCase();
    if (!needle) return runs;
    return runs.filter((run) => run.title.toLowerCase().includes(needle) || run.run_id.toLowerCase().includes(needle));
  }, [runFilter, runs]);

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

  const trendWidth = 620;
  const trendHeight = 210;
  const trendPadding = { left: 34, right: 12, top: 12, bottom: 26 };

  return (
    <section className="workspace-page workspace-page--wide evaluation-panel console-view-enter" aria-labelledby="evaluation-title">
      <div className="console-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><ClipboardCheck aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="evaluation-title" className="console-page-header__title">{vi ? "Evaluation" : "Evaluation"}</h1>
            <p className="console-page-header__subtitle">
              {vi
                ? "Đo chất lượng, độ chính xác và độ tin cậy của hệ thống RAG qua các report publish chỉ đọc."
                : "Measure RAG quality, accuracy, and reliability through read-only published reports."}
            </p>
          </div>
        </div>
        <div className="console-page-header__actions">
          <SelectField className="header-view-select min-w-32" label={vi ? "Trạng thái" : "Status"} value={status} onValueChange={(value) => setStatus(value as EvaluationRunStatus | "")} options={[{ value: "", label: vi ? "Tất cả" : "All" }, { value: "official", label: "Official" }, { value: "candidate", label: "Candidate" }, { value: "historical", label: "Historical" }, { value: "incomplete", label: "Incomplete" }]} />
          <button type="button" onClick={load} className="console-btn" aria-label={vi ? "Tải lại evaluation" : "Refresh evaluation"}>
            <RefreshCw className={loading ? "animate-spin" : ""} aria-hidden="true" />
            {vi ? "Làm mới" : "Refresh"}
          </button>
        </div>
      </div>

      {error && <div role="alert" className="flex items-center gap-2 rounded-xl state-warning-surface p-3 text-sm"><ShieldAlert className="h-4 w-4 shrink-0" />{error}</div>}
      {loading && <div className="console-loading" role="status"><span className="console-loading__spinner" aria-hidden="true" />{vi ? "Đang tải report..." : "Loading reports..."}</div>}
      {!loading && !error && runs.length === 0 && (
        <div className="console-card"><div className="console-empty">
          <FileJson aria-hidden="true" />
          <strong>{status ? (vi ? "Không có report phù hợp" : "No reports match this filter") : (vi ? "Chưa có report public" : "No published reports yet")}</strong>
          <p>{status
            ? (vi ? "Không có report public nào khớp trạng thái đã chọn. Hãy thử trạng thái khác." : "No published report matches the selected status. Try another status filter.")
            : (vi ? "Backend chưa cung cấp report evaluation public nào để mở. Không hiển thị số liệu thay thế." : "The backend has not provided a public evaluation report to open. No substitute metrics are shown.")}</p>
        </div></div>
      )}

      {!loading && runs.length > 0 && (
        <div className="console-layout">
          <div className="console-layout__main">
            {kpis.length > 0 && (
              <div className="console-stats">
                {kpis.map((kpi, index) => (
                  <div key={kpi.key} className="console-stat">
                    <div className={`console-stat__icon ${kpi.isCount ? "" : "console-stat__icon--success"}`}>
                      {kpi.isCount ? <ClipboardCheck aria-hidden="true" /> : <TrendingUp aria-hidden="true" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-2">
                        <span className="console-stat__value">{kpi.isCount ? kpi.value : score(kpi.value)}</span>
                        {kpi.delta !== null && !kpi.isCount && (
                          <span className={`inline-flex items-center gap-0.5 text-[11px] font-bold ${kpi.delta >= 0 ? "text-[var(--success)]" : "text-[var(--danger)]"}`}>
                            {kpi.delta >= 0 ? <ArrowUpRight className="h-3 w-3" aria-hidden="true" /> : <ArrowDownRight className="h-3 w-3" aria-hidden="true" />}
                            {kpi.delta >= 0 ? "+" : ""}{kpi.delta.toFixed(3)}
                          </span>
                        )}
                      </div>
                      <div className="console-stat__label">{metricLabel(kpi.key)}</div>
                      <Sparkline values={kpi.values} color={METRIC_COLORS[index % METRIC_COLORS.length]} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="console-card">
              <div className="console-card__header">
                <div className="min-w-0">
                  <h2 className="console-card__title">{vi ? "Evaluation Runs" : "Evaluation Runs"}</h2>
                  <p className="console-card__subtitle">{vi ? "Các run evaluation gần đây trên tập dữ liệu và cấu hình khác nhau." : "Recent evaluation runs across datasets and configurations."}</p>
                </div>
                <div className="console-input-row min-w-0 max-w-56 flex-1 sm:flex-none">
                  <Search aria-hidden="true" />
                  <input
                    className="console-input"
                    value={runFilter}
                    onChange={(event) => setRunFilter(event.target.value)}
                    placeholder={vi ? "Tìm run…" : "Search runs…"}
                    aria-label={vi ? "Tìm evaluation run" : "Search runs"}
                  />
                </div>
              </div>
              <div className="console-table-wrap">
                <table className="console-table">
                  <thead>
                    <tr>
                      <th scope="col" className="w-8">#</th>
                      <th scope="col">{vi ? "Run" : "Run Name"}</th>
                      <th scope="col">{vi ? "Trạng thái" : "Status"}</th>
                      <th scope="col">{vi ? "Điểm overall" : "Overall"}</th>
                      <th scope="col" className="text-right">{vi ? "Số case" : "Cases"}</th>
                      <th scope="col">{vi ? "Thời gian" : "Time"}</th>
                      <th scope="col" className="text-right">{vi ? "Hành động" : "Actions"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRuns.map((run, index) => {
                      const isSelected = selected?.run_id === run.run_id;
                      const overall = run.aggregate.overall ?? run.aggregate.overall_judge_average;
                      return (
                        <tr key={run.run_id} className={isSelected ? "is-selected" : ""} aria-selected={isSelected} onClick={() => selectRun(run.run_id)}>
                          <td className="console-table__secondary">{index + 1}</td>
                          <td>
                            <div className="console-table__primary">{run.title}</div>
                            <div className="console-table__secondary font-mono">{run.run_id}</div>
                          </td>
                          <td>
                            <span className={`console-pill ${run.status === "official" ? "console-pill--high" : run.status === "incomplete" ? "console-pill--low" : "console-pill--info"}`}>
                              {run.status}
                            </span>
                          </td>
                          <td><span className="console-table__primary">{score(overall)}</span></td>
                          <td className="text-right console-table__secondary">{run.case_count}</td>
                          <td><span className="console-table__secondary">{formatDateTime(run.created_at)}</span></td>
                          <td>
                            <span className="flex items-center justify-end gap-1" onClick={(event) => event.stopPropagation()}>
                              <button type="button" className="console-btn" onClick={() => selectRun(run.run_id)}>
                                <BarChart3 aria-hidden="true" />
                                {vi ? "Mở report" : "Open Report"}
                              </button>
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {filteredRuns.length === 0 && (
                      <tr><td colSpan={7}><div className="console-empty"><Search aria-hidden="true" /><strong>{vi ? "Không có run phù hợp" : "No matching runs"}</strong></div></td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {trend && (
              <div className="console-card">
                <div className="console-card__header">
                  <div className="min-w-0">
                    <h2 className="console-card__title">{vi ? "Xu hướng evaluation" : "Evaluation Trend"}</h2>
                    <p className="console-card__subtitle">{vi ? "Theo dõi chỉ số qua các run publish để xem cải thiện." : "Track key metrics across published runs."}</p>
                  </div>
                  <span className="console-chip">{trend.runs.length} {vi ? "run" : "runs"}</span>
                </div>
                <div className="console-card__body pb-1">
                  <svg className="console-chart" viewBox={`0 0 ${trendWidth} ${trendHeight}`} role="img" aria-label={vi ? "Biểu đồ xu hướng evaluation" : "Evaluation trend chart"}>
                    {[0, 0.2, 0.4, 0.6, 0.8, 1].map((tick) => {
                      const y = trendHeight - trendPadding.bottom - tick * (trendHeight - trendPadding.top - trendPadding.bottom);
                      return (
                        <g key={tick}>
                          <line className="grid-line" x1={trendPadding.left} x2={trendWidth - trendPadding.right} y1={y} y2={y} />
                          <text className="axis-label" x={trendPadding.left - 6} y={y + 3} textAnchor="end">{tick.toFixed(1)}</text>
                        </g>
                      );
                    })}
                    {trend.metricKeys.map((key, metricIndex) => {
                      const points = trend.runs.map((run, runIndex) => {
                        const x = trendPadding.left + (runIndex / (trend.runs.length - 1)) * (trendWidth - trendPadding.left - trendPadding.right);
                        const y = trendHeight - trendPadding.bottom - run.aggregate[key] * (trendHeight - trendPadding.top - trendPadding.bottom);
                        return { x, y };
                      });
                      const color = METRIC_COLORS[metricIndex % METRIC_COLORS.length];
                      return (
                        <g key={key}>
                          <polyline fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" points={points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ")} />
                          {points.map((point, pointIndex) => <circle key={pointIndex} cx={point.x} cy={point.y} r="2.6" fill={color} />)}
                        </g>
                      );
                    })}
                    {trend.runs.map((run, runIndex) => {
                      const x = trendPadding.left + (runIndex / (trend.runs.length - 1)) * (trendWidth - trendPadding.left - trendPadding.right);
                      return (
                        <text key={run.run_id} className="axis-label" x={x} y={trendHeight - 8} textAnchor="middle">
                          {new Date(run.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                        </text>
                      );
                    })}
                  </svg>
                </div>
                <div className="console-legend">
                  {trend.metricKeys.map((key, index) => (
                    <span key={key} className="console-legend__item">
                      <span className="console-legend__swatch" style={{ background: METRIC_COLORS[index % METRIC_COLORS.length] }} aria-hidden="true" />
                      {metricLabel(key)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="grid gap-4 xl:grid-cols-2">
              {distribution && (
                <div className="console-card">
                  <div className="console-card__header">
                    <div className="min-w-0">
                      <h2 className="console-card__title">{vi ? "Phân bổ điểm case" : "Case Score Distribution"}</h2>
                      <p className="console-card__subtitle">{vi ? "Số case theo khoảng điểm tổng hợp trong run đã chọn." : "Cases per aggregate score bucket in the selected run."}</p>
                    </div>
                  </div>
                  <div className="console-card__body">
                    <div className="console-bars">
                      {distribution.buckets.map((bucket) => (
                        <div key={bucket.label} className="console-bars__row">
                          <span className="console-bars__label">{bucket.label}</span>
                          <span className="console-bars__track">
                            <span className="console-bars__fill" style={{ width: `${distribution.max === 0 ? 0 : (bucket.count / distribution.max) * 100}%`, background: bucket.color }} />
                          </span>
                          <span className="console-bars__value">{bucket.count}<small>{distribution.max === 0 ? "0%" : `${Math.round((bucket.count / selectedCases.length) * 100)}%`}</small></span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div className="console-card">
                <div className="console-card__header">
                  <div className="min-w-0">
                    <h2 className="console-card__title" id="evaluation-cases-title">{vi ? "Chi tiết case" : "Case Details"}</h2>
                    <p className="console-card__subtitle">{vi ? "Mở từng case để xem câu trả lời, evidence và gate." : "Open a case to inspect its answer, evidence, and gates."}</p>
                  </div>
                  <span className="console-chip">{selectedCases.length} {vi ? "case" : "cases"}</span>
                </div>
                <div className="console-card__body max-h-96 space-y-2 overflow-y-auto">
                  {selectedCases.map((item) => (
                    <details key={item.case_id} className="rounded-xl border border-[var(--border-subtle)] p-3">
                      <summary className="evaluation-case-summary cursor-pointer text-sm font-semibold text-[var(--text-primary)]">
                        <span className="text-[10px] uppercase text-[var(--text-muted)]">{item.language}</span>
                        <span className="min-w-0 break-words">{item.question}</span>
                        <span className={`inline-flex items-center gap-1 text-xs ${item.status === "OK" ? "text-[var(--success)]" : item.status === "ERROR" ? "text-[var(--danger)]" : "text-[var(--warning)]"}`}>
                          <CaseStatusIcon status={item.status} />{item.status}
                        </span>
                      </summary>
                      <p className="mt-3 text-sm leading-relaxed text-[var(--text-muted)]">{item.answer ?? (vi ? "Không có câu trả lời." : "No answer recorded.")}</p>
                      {item.evidence.map((evidence) => (
                        <div key={evidence.citation} className="mt-2 rounded-lg bg-[var(--surface-muted)] p-2 text-xs text-[var(--text-muted)]">
                          <strong className="text-[var(--text-primary)]">{evidence.citation}</strong>
                          <div className="mt-1">{evidence.excerpt}</div>
                        </div>
                      ))}
                    </details>
                  ))}
                  {selectedCases.length === 0 && <div className="console-empty"><Activity aria-hidden="true" /><strong>{vi ? "Chưa chọn run" : "No run selected"}</strong></div>}
                </div>
              </div>
            </div>
          </div>

          <aside className="console-layout__aside" aria-label={vi ? "Evaluation mới nhất" : "Latest evaluation"}>
            <div className="console-card">
              <div className="console-card__header">
                <h2 className="console-card__title">{vi ? "Evaluation mới nhất" : "Latest Evaluation"}</h2>
                {selected && <span className={`console-pill ${selected.status === "official" ? "console-pill--high" : "console-pill--info"}`}>{selected.status}</span>}
              </div>
              {selected ? (
                <div className="console-card__body space-y-4">
                  <div>
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">{selected.title}</h3>
                    <p className="mt-0.5 text-xs text-[var(--text-muted)]">{vi ? "Hoàn tất" : "Completed"} {formatDateTime(selected.created_at)}</p>
                  </div>
                  <dl className="console-meta-grid">
                    <div><dt>Run ID</dt><dd className="font-mono text-xs">{selected.run_id}</dd></div>
                    <div><dt>{vi ? "Số case" : "Cases"}</dt><dd>{selected.cases.length}</dd></div>
                    <div><dt>{vi ? "Trạng thái" : "Status"}</dt><dd>{selected.status}</dd></div>
                    <div><dt>{vi ? "Điểm overall" : "Overall"}</dt><dd>{score(selected.aggregate.overall ?? selected.aggregate.overall_judge_average)}</dd></div>
                  </dl>
                  {selected.notes.length > 0 && (
                    <p className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3 text-[13px] leading-relaxed text-[var(--text-muted)]">
                      {selected.notes.join(" ")}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => downloadSelected("json")} className="console-btn" aria-label="Export evaluation JSON">
                      <Download aria-hidden="true" />JSON
                    </button>
                    <button type="button" onClick={() => downloadSelected("csv")} className="console-btn" aria-label="Export evaluation CSV">
                      <Download aria-hidden="true" />CSV
                    </button>
                  </div>
                  {runs.length > 1 && (
                    <details>
                      <summary className="cursor-pointer text-xs font-semibold text-[var(--accent-text)]">{vi ? "So sánh paired experiment" : "Paired experiment comparison"}</summary>
                      <div className="mt-2">
                        <SelectField
                          label={vi ? "Chọn run đối chiếu" : "Comparison run"}
                          value={comparisonId}
                          onValueChange={setComparisonId}
                          options={[{ value: "", label: vi ? "Chọn run..." : "Choose run..." }, ...runs.filter((run) => run.run_id !== selected.run_id).map((run) => ({ value: run.run_id, label: run.title }))]}
                        />
                        {comparisonResult && (comparisonResult.compatible ? (
                          <div className="mt-2 space-y-1.5">
                            {comparisonResult.metrics.map((metric) => (
                              <div key={metric.metric} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-2 text-xs">
                                <div className="font-semibold text-[var(--text-primary)]">{metric.metric} Δ {metric.delta.toFixed(3)}</div>
                                <div className="mt-1 text-[var(--text-muted)]">95% CI [{metric.lower95.toFixed(3)}, {metric.upper95.toFixed(3)}] · n={metric.sampleCount} · {metric.resamples} resamples (seed {metric.seed})</div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-2 text-xs text-[var(--state-warning-text)]">{comparisonResult.reason}</p>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              ) : (
                <div className="console-empty"><LineChart aria-hidden="true" /><strong>{vi ? "Chọn một run" : "Select a run"}</strong><p>{vi ? "Chọn một hàng trong bảng để xem tổng quan và xuất report." : "Pick a row in the table to see the summary and export the report."}</p></div>
              )}
            </div>
          </aside>
        </div>
      )}
    </section>
  );
}
