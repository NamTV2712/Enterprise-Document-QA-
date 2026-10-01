import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLocale } from "../lib/i18n";
import { useLocalWorkspaceSession } from "../lib/localWorkspaceSession";
import { operationalApi, OperationalApiError } from "../lib/operationalApi";
import { analyticsRanges, analyticsIntervals, analyticsMetrics, outcomes, type AnalyticsMetric, type AnalyticsRange, type AnalyticsInterval, type AnalyticsTimeseries } from "../lib/operationalTypes";
import { useOperationalRead } from "../hooks/useOperationalRead";
import { OperationalHeader, LocalConnection, ReadState, durationText, outcomeLabel } from "./operations/OperationalShared";

const metricLabels: Record<AnalyticsMetric, [string, string]> = {
  request_count: ["Request count", "Số yêu cầu"], request_failure_count: ["Failure count", "Số thất bại"], request_duration_p50_ms: ["p50 measured duration", "Thời gian đo p50"], request_duration_p95_ms: ["p95 measured duration", "Thời gian đo p95"], terminal_job_count: ["Terminal job count", "Số job kết thúc"],
};
function Timeseries({ data, vi }: { data: AnalyticsTimeseries; vi: boolean }) {
  const values = data.points.filter(p => p.value !== null), max = Math.max(1, ...values.map(p => p.value!));
  return <>
    <p>{vi ? "Bucket UTC từ server · tối đa 720. Mỗi điểm là một quan sát." : "Server UTC buckets · maximum 720. Each point is one observation."}</p>
    <p className="operations-window">{data.started_at} — {data.ended_at} · UTC · {data.unit === "milliseconds" ? (vi ? "Đơn vị: ms" : "Unit: ms") : (vi ? "Đơn vị: số lượng" : "Unit: count")}</p>
    {!values.length ? <p className="operations-state">{vi ? "Không có quần thể đo lường trong khoảng này." : "No measured population in this range."}</p> : <svg className="operations-chart" viewBox="0 0 800 170" role="img" aria-label={`${metricLabels[data.metric][vi ? 1 : 0]} · UTC · ${data.unit}`}>
      <text x="5" y="15" fill="currentColor">{max.toLocaleString()} {data.unit === "count" ? "" : "ms"}</text><line x1="50" y1="145" x2="790" y2="145" stroke="currentColor" opacity=".4" />
      {data.points.map((p, i) => p.value === null ? null : <circle key={p.started_at} cx={50 + (i / Math.max(1, data.points.length - 1)) * 730} cy={145 - (p.value / max) * 115} r="3" fill="var(--accent-text)"><title>{p.started_at}: {p.value} {data.unit}; n={p.denominator}</title></circle>)}
      <text x="50" y="165" fill="currentColor">{data.started_at.slice(0, 16)} UTC</text><text x="790" y="165" textAnchor="end" fill="currentColor">{data.ended_at.slice(0, 16)} UTC</text>
    </svg>}
    <details><summary>{vi ? "Bảng bucket và quần thể" : "Bucket table and populations"} ({data.points.length})</summary><div className="operations-table-scroll" tabIndex={0} role="region" aria-label={vi ? "Bucket UTC" : "UTC buckets"}><table><caption>{metricLabels[data.metric][vi ? 1 : 0]} · UTC</caption><thead><tr><th>{vi ? "Bắt đầu" : "Start"}</th><th>{vi ? "Kết thúc" : "End"}</th><th>{vi ? "Giá trị" : "Value"}</th><th>{vi ? "Quần thể" : "Population"}</th></tr></thead><tbody>{data.points.map(p => <tr key={p.started_at}><td>{p.started_at}</td><td>{p.ended_at}</td><td>{data.unit === "milliseconds" ? durationText(p.value, vi) : p.value === null ? (vi ? "Không khả dụng" : "Unavailable") : p.value}</td><td>{p.denominator}</td></tr>)}</tbody></table></div></details>
  </>;
}
export function AnalyticsPanel() {
  const { locale } = useLocale(), vi = locale === "vi", session = useLocalWorkspaceSession();
  const token = session.getToken() ?? "";
  const [query, setQuery] = useSearchParams(), [refresh, setRefresh] = useState(0);
  const range = (query.get("range") ?? "24h") as AnalyticsRange, interval = (query.get("interval") ?? "hour") as AnalyticsInterval, metric = (query.get("metric") ?? "request_count") as AnalyticsMetric;
  const valid = analyticsRanges.includes(range) && analyticsIntervals.includes(interval) && analyticsMetrics.includes(metric);
  const summaryLoad = useCallback((signal: AbortSignal) => valid ? operationalApi.summary(token, range, signal) : Promise.reject(new OperationalApiError(422)), [range, token, valid]);
  const seriesLoad = useCallback((signal: AbortSignal) => valid ? operationalApi.timeseries(token, range, interval, metric, signal) : Promise.reject(new OperationalApiError(422)), [range, interval, metric, token, valid]);
  const summary = useOperationalRead(`summary:${range}:${valid}:${refresh}`, summaryLoad), series = useOperationalRead(`series:${range}:${interval}:${metric}:${refresh}`, seriesLoad);
  function select(key: string, value: string) { const next = new URLSearchParams(query); next.set(key, value); setQuery(next); }
  const data = summary.data;
  return <section className="workspace-page workspace-page--wide operations-page" aria-label={vi ? "Phân tích vận hành" : "Operational analytics"}>
    <OperationalHeader title={vi ? "Phân tích" : "Analytics"} description={vi ? "Quần thể yêu cầu kết thúc và job từ server. Nội dung nghiên cứu không được thu thập." : "Server terminal request and job populations. Research content is not collected."} refresh={() => setRefresh(n => n + 1)} />
    <LocalConnection />
    <div className="operations-controls"><label>{vi ? "Khoảng thời gian" : "Time range"}<select aria-label={vi ? "Khoảng thời gian" : "Time range"} value={range} onChange={e => select("range", e.target.value)}>{analyticsRanges.map(r => <option key={r} value={r}>{r === "24h" ? (vi ? "24 giờ" : "24 hours") : r === "7d" ? (vi ? "7 ngày" : "7 days") : (vi ? "30 ngày" : "30 days")}</option>)}</select></label>{!valid && <button onClick={() => setQuery({})} className="secondary-action-button">{vi ? "Đặt lại" : "Reset controls"}</button>}</div>
    <ReadState {...summary} />
    {data && <>
      <p className="operations-window">{data.started_at} — {data.ended_at} · UTC · {vi ? "Giữ telemetry 30 ngày" : "30-day telemetry retention"}</p>
      <div className="operations-metrics">
        <article className="operations-card"><h2>{vi ? "Yêu cầu kết thúc" : "Terminal requests"}</h2><strong>{data.requests.terminal_count}</strong><p>{vi ? "Quần thể trong khoảng đã chọn" : "Population in selected range"}</p></article>
        {(["success_rate", "failure_rate"] as const).map(key => { const rate = data.requests[key]; return <article key={key} className="operations-card"><h2>{key === "success_rate" ? (vi ? "Tỷ lệ thành công" : "Success rate") : (vi ? "Tỷ lệ thất bại" : "Failure rate")}</h2><strong>{rate.value === null ? (vi ? "Không khả dụng" : "Unavailable") : `${(rate.value * 100).toLocaleString(locale, { maximumFractionDigits: 2 })}%`}</strong><p>{rate.numerator} / {rate.denominator} {vi ? "yêu cầu" : "requests"}</p></article>; })}
        <article className="operations-card"><h2>{vi ? "Thời gian toàn thao tác" : "Whole-operation duration"}</h2><strong>{durationText(data.requests.duration_ms.p50, vi)}</strong><p>p50 · p95 {durationText(data.requests.duration_ms.p95, vi)}</p><p>{data.requests.duration_ms.known_count} {vi ? "đã đo" : "measured"} · {data.requests.duration_ms.unknown_count} {vi ? "chưa đo" : "not measured"}</p></article>
      </div>
      {data.requests.terminal_count === 0 && <p role="status" className="operations-state">{vi ? "Chưa có yêu cầu kết thúc trong khoảng này." : "No terminal requests recorded in this range."}</p>}
      <div className="operations-groups"><article className="operations-card"><h2>{vi ? "Kết quả yêu cầu" : "Request outcomes"}</h2><dl>{outcomes.map(outcome => <div key={outcome}><dt>{outcomeLabel(outcome, vi)}</dt><dd>{data.requests.outcomes[outcome]}</dd></div>)}</dl></article><article className="operations-card"><h2>{vi ? "Job kết thúc" : "Terminal jobs"} · {data.terminal_jobs.terminal_count}</h2><dl>{Object.entries(data.terminal_jobs.by_namespace).map(([key, count]) => <div key={key}><dt>{outcomeLabel(key, vi)}</dt><dd>{count}</dd></div>)}</dl><dl>{Object.entries(data.terminal_jobs.by_outcome).map(([key, count]) => <div key={key}><dt>{outcomeLabel(key, vi)}</dt><dd>{count}</dd></div>)}</dl><p>{vi ? "Nguồn: job chính thức. Budget exhaustion nằm trong failed theo summary; Logs giữ mã và severity." : "Source: canonical jobs. Budget exhaustion is included in failed by this summary; Logs preserves its code and severity."}</p></article></div>
    </>}
    {!summary.disconnected && <article className="operations-card"><h2>{vi ? "Diễn biến theo thời gian" : "Timeseries"}</h2><div className="operations-controls"><label>{vi ? "Chỉ số" : "Metric"}<select aria-label={vi ? "Chỉ số" : "Metric"} value={metric} onChange={e => select("metric", e.target.value)}>{analyticsMetrics.map(m => <option key={m} value={m}>{metricLabels[m][vi ? 1 : 0]}</option>)}</select></label><label>{vi ? "Khoảng bucket" : "Interval"}<select aria-label={vi ? "Khoảng bucket" : "Interval"} value={interval} onChange={e => select("interval", e.target.value)}><option value="hour">{vi ? "Giờ (UTC)" : "Hour (UTC)"}</option><option value="day">{vi ? "Ngày (UTC)" : "Day (UTC)"}</option></select></label></div><ReadState {...series} />{series.data && <Timeseries data={series.data} vi={vi} />}</article>}
  </section>;
}
