import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLocale } from "../../lib/i18n";
import { useLocalWorkspaceSession } from "../../lib/localWorkspaceSession";
import { operationalApi, OperationalApiError } from "../../lib/operationalApi";
import { levels, type LogCategory, type LogLevel } from "../../lib/operationalTypes";
import { useOperationalRead } from "../../hooks/useOperationalRead";
import { LocalConnection, OperationalHeader, ReadState, durationText, outcomeLabel } from "./OperationalShared";

export function LogsPage() {
  const { locale } = useLocale(), vi = locale === "vi", session = useLocalWorkspaceSession();
  const token = session.getToken() ?? "";
  const [query, setQuery] = useSearchParams(), [refresh, setRefresh] = useState(0);
  const category = query.get("category") ?? "all", level = query.get("level") ?? "all", cursor = query.get("cursor") ?? "";
  const valid = ["all", "request", "job"].includes(category) && ["all", ...levels].includes(level) && cursor.length <= 512;
  const load = useCallback((signal: AbortSignal) => valid ? operationalApi.logs(token, { category: category === "all" ? undefined : category as LogCategory, level: level === "all" ? undefined : level as LogLevel, cursor: cursor || undefined, limit: 50 }, signal) : Promise.reject(new OperationalApiError(422)), [token, category, level, cursor, valid]);
  const state = useOperationalRead(`logs:${category}:${level}:${cursor}:${refresh}`, load);
  function filter(key: string, value: string) { const next = new URLSearchParams(query); next.delete("cursor"); if (value === "all") next.delete(key); else next.set(key, value); setQuery(next); }
  return <section className="workspace-page workspace-page--wide operations-page" aria-label={vi ? "Nhật ký vận hành" : "Operational logs"}>
    <OperationalHeader title={vi ? "Nhật ký" : "Logs"} description={vi ? "Nhật ký đã làm sạch trong 7 ngày: yêu cầu và job kết thúc. Không bao gồm log tiến trình." : "Sanitized seven-day request and terminal-job records. Conventional process logs are not included."} refresh={() => setRefresh(n => n + 1)} />
    <LocalConnection />
    <div className="operations-controls"><label>{vi ? "Loại" : "Category"}<select aria-label={vi ? "Loại" : "Category"} value={category} onChange={e => filter("category", e.target.value)}><option value="all">{vi ? "Mọi bản ghi API" : "All API records"}</option><option value="request">{vi ? "Yêu cầu" : "Requests"}</option><option value="job">{vi ? "Job" : "Jobs"}</option></select></label><label>{vi ? "Mức độ" : "Severity"}<select aria-label={vi ? "Mức độ" : "Severity"} value={level} onChange={e => filter("level", e.target.value)}><option value="all">{vi ? "Mọi mức độ" : "All levels"}</option>{levels.map(l => <option key={l} value={l}>{outcomeLabel(l, vi)}</option>)}</select></label>{!valid && <button className="secondary-action-button" onClick={() => setQuery({})}>{vi ? "Đặt lại" : "Reset controls"}</button>}</div>
    <ReadState {...state} />
    {state.data && <>
      {!state.data.items.length && <p className="operations-state" role="status">{vi ? "Không có bản ghi cho bộ lọc này trong 7 ngày." : "No records for these filters in the seven-day window."}</p>}
      <ol className="operations-logs" aria-label={vi ? "Bản ghi theo thứ tự server" : "Records in server order"}>{state.data.items.map(row => <li key={row.record_id} className="operations-card">
        <div className="operations-log-heading"><span className={`operations-level operations-level--${row.level}`}>{outcomeLabel(row.level, vi)}</span><h2>{outcomeLabel(row.subsystem, vi)} · {row.category === "request" ? (vi ? "yêu cầu" : "request") : "job"}</h2><span>{outcomeLabel(row.outcome, vi)}</span><time dateTime={row.occurred_at}>{row.occurred_at} · UTC</time></div>
        <p>{row.route_template ?? row.domain_id} · {durationText(row.duration_ms, vi)}{row.error_code ? ` · ${row.error_code}` : ""}</p>
        <details><summary>{vi ? "Chi tiết bản ghi" : "Record details"}</summary><dl><div><dt>{vi ? "ID bản ghi" : "Record ID"}</dt><dd>{row.record_id}</dd></div><div><dt>{row.category === "request" ? (vi ? "ID tương quan yêu cầu" : "Request correlation ID") : (vi ? "ID tương quan job" : "Job correlation ID")}</dt><dd>{row.correlation_id}</dd></div>{row.domain_id && <div><dt>Job ID</dt><dd>{row.domain_id}</dd></div>}<div><dt>{vi ? "Loại sự kiện" : "Event kind"}</dt><dd>{row.kind}</dd></div>{Object.entries(row.metadata).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl></details>
      </li>)}</ol>
      <nav className="operations-pagination" aria-label={vi ? "Phân trang nhật ký" : "Log pagination"}>{cursor && <button className="secondary-action-button" onClick={() => { const next = new URLSearchParams(query); next.delete("cursor"); setQuery(next); }}>{vi ? "Bản ghi mới nhất" : "Newest records"}</button>}<p>{state.data.items.length} {vi ? "bản ghi trên trang" : "records on this page"} · {vi ? "Tối đa" : "Limit"} {state.data.limit}</p><button className="secondary-action-button" disabled={!state.data.has_more || !state.data.next_cursor} onClick={() => { if (!state.data?.next_cursor) return; const next = new URLSearchParams(query); next.set("cursor", state.data.next_cursor); setQuery(next); }}>{vi ? "Trang tiếp" : "Next page"}</button></nav>
    </>}
  </section>;
}
