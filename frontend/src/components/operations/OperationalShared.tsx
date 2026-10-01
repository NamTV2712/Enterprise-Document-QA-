import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { useLocale } from "../../lib/i18n";
import { useLocalWorkspaceSession } from "../../lib/localWorkspaceSession";
import { operationalErrorMessage } from "../../lib/operationalApi";
import { pipelineErrorMessage, PipelineApiError } from "../../lib/pipelineApi";
import "./operations.css";

export function OperationalHeader({ title, description, refresh }: { title: string; description: string; refresh?: () => void }) {
  const { locale } = useLocale();
  return <header className="operations-header"><div><p className="workspace-eyebrow">{locale === "vi" ? "Workspace · vận hành" : "Workspace · operations"}</p><h1>{title}</h1><p>{description}</p></div>{refresh && <button className="secondary-action-button" onClick={refresh}><RefreshCw size={16} aria-hidden="true" />{locale === "vi" ? "Làm mới" : "Refresh"}</button>}</header>;
}
export function LocalConnection() {
  const { locale } = useLocale(), vi = locale === "vi", session = useLocalWorkspaceSession();
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  return <section className="operations-connection operations-card" aria-label={vi ? "Kết nối cục bộ" : "Local connection"}>
    <div><h2>{vi ? "Workspace cục bộ" : "Local workspace"}</h2><p>{session.status === "connected" ? (vi ? "Đã kết nối · token chỉ trong bộ nhớ" : "Connected · token held in memory only") : (vi ? "Kết nối để đọc dữ liệu riêng tư. Tải lại sẽ xóa thông tin xác thực." : "Connect to read private data. Reload clears the credential.")}</p></div>
    {session.status === "connected" ? <button className="secondary-action-button" onClick={() => { setError(null); session.disconnect(); }}>{vi ? "Ngắt kết nối" : "Disconnect"}</button> : <form onSubmit={async event => {
      event.preventDefault(); if (session.status === "connecting") return;
      const candidate = input.current?.value ?? ""; if (input.current) input.current.value = "";
      setError(null);
      try { await session.connect(candidate); } catch (reason) { setError(reason instanceof PipelineApiError ? pipelineErrorMessage(reason.status, locale) : (vi ? "Không thể kết nối. Hãy thử lại." : "Could not connect. Try again.")); }
    }}><label>{vi ? "Token workspace cục bộ" : "Local workspace token"}<input ref={input} type="password" autoComplete="off" spellCheck={false} required disabled={session.status === "connecting"} /></label><button className="primary-action-button" disabled={session.status === "connecting"}>{session.status === "connecting" ? (vi ? "Đang xác minh…" : "Verifying…") : (vi ? "Kết nối" : "Connect")}</button></form>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
export function ReadState({ loading, error, disconnected }: { loading: boolean; error?: unknown; disconnected?: boolean }) {
  const { locale } = useLocale(), vi = locale === "vi";
  if (disconnected) return <div className="operations-state" role="status"><h2>{vi ? "Dữ liệu riêng tư chưa khả dụng" : "Private data is not connected"}</h2><p>{vi ? "Kết nối workspace cục bộ để đọc dữ liệu. Đây không phải dữ liệu trống." : "Connect to the local workspace to read this data. No population has been observed."}</p><Link to="/settings">{vi ? "Mở cài đặt" : "Open Settings"}</Link></div>;
  if (error) return <p className="operations-state" role="alert">{operationalErrorMessage(error, vi)}</p>;
  if (loading) return <p className="operations-state" role="status">{vi ? "Đang đọc dữ liệu server…" : "Reading server data…"}</p>;
  return null;
}
export function durationText(value: number | null, vi = false) { return value === null ? (vi ? "Không có đo lường" : "Not measured") : `${value.toLocaleString(vi ? "vi-VN" : "en-US", { maximumFractionDigits: 3 })} ms`; }
export function outcomeLabel(value: string, vi: boolean) {
  if (!vi) return value.replaceAll("_", " ");
  return ({ succeeded: "Thành công", rejected: "Bị từ chối", failed: "Thất bại", cancelled: "Đã hủy", interrupted: "Gián đoạn", info: "Thông tin", warning: "Cảnh báo", error: "Lỗi", query: "Truy vấn", search: "Tìm kiếm", retrieval: "Truy xuất", pipeline: "Pipeline", evaluation: "Đánh giá", model_test: "Kiểm tra mô hình" } as Record<string, string>)[value] ?? value;
}
