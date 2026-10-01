import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useLocale } from "../../lib/i18n";
import { useLocalWorkspaceSession } from "../../lib/localWorkspaceSession";
import { operationalApi } from "../../lib/operationalApi";
import { useOperationalRead } from "../../hooks/useOperationalRead";
import type { ThemePreference } from "../../types";
import type { ConversationStorageMode, WriterStatus } from "../../lib/conversationStore";
import { MAX_BACKUP_BYTES, parseConversationBackupBundle, type ConversationBackupBundle } from "../../lib/conversationExport";
import type { ConversationImportResult } from "../../hooks/useConversationLibrary";
import { LocalConnection, OperationalHeader, ReadState } from "./OperationalShared";

export interface SettingsPageProps {
  theme: ThemePreference; onThemeChange: (theme: ThemePreference) => void;
  storageMode: ConversationStorageMode; storageWarning: string | null; writerStatus: WriterStatus;
  onRequestWriter: () => Promise<WriterStatus>; onExportBackup: () => void;
  onImportBackup: (bundle: ConversationBackupBundle) => Promise<ConversationImportResult>;
}
export function SettingsPage(props: SettingsPageProps) {
  const { locale, setLocale } = useLocale(), vi = locale === "vi", session = useLocalWorkspaceSession();
  const token = session.getToken() ?? "", [refresh, setRefresh] = useState(0);
  const factsLoad = useCallback((signal: AbortSignal) => operationalApi.settingsFacts(signal), []);
  const configLoad = useCallback((signal: AbortSignal) => operationalApi.configuration(token, signal), [token]);
  const providerLoad = useCallback((signal: AbortSignal) => operationalApi.providerStatus(signal), []);
  const provider = useOperationalRead(`provider:${refresh}`, providerLoad, true, false);
  const facts = useOperationalRead(`facts:${refresh}`, factsLoad, true, false), config = useOperationalRead(`config:${refresh}`, configLoad);
  const [pending, setPending] = useState<{ bundle: ConversationBackupBundle; name: string } | null>(null), [notice, setNotice] = useState<string | null>(null), [busy, setBusy] = useState(false);
  const epoch = useRef(0), locked = useRef(false);
  useEffect(() => () => { epoch.current++; }, []);
  async function preview(file?: File) {
    if (!file || locked.current) return;
    const current = ++epoch.current; setNotice(null); setPending(null);
    try { if (file.size > MAX_BACKUP_BYTES) throw new Error(); const bundle = parseConversationBackupBundle(await file.text()); if (epoch.current === current) setPending({ bundle, name: file.name }); }
    catch { if (epoch.current === current) setNotice(vi ? "Backup không hợp lệ hoặc vượt quá 25 MiB." : "The backup is invalid or exceeds 25 MiB."); }
  }
  async function importBackup() {
    if (!pending || locked.current) return;
    locked.current = true; setBusy(true); const current = ++epoch.current;
    try { const result = await props.onImportBackup(pending.bundle); if (epoch.current === current) { setPending(null); setNotice(vi ? `Đã nhập ${result.imported}; đã lưu ${result.persisted}; tạm thời ${result.volatile}; lỗi ${result.failed}; evidence lỗi ${result.evidenceFailed ?? 0}.` : `Imported ${result.imported}; persisted ${result.persisted}; volatile ${result.volatile}; failed ${result.failed}; evidence failures ${result.evidenceFailed ?? 0}.`); } }
    catch { if (epoch.current === current) setNotice(vi ? "Không thể nhập backup. Kiểm tra quyền ghi và thử lại." : "Could not import the backup. Check writer access and try again."); }
    finally { locked.current = false; if (epoch.current === current) setBusy(false); }
  }
  return <section className="workspace-page workspace-page--wide operations-page" aria-label={vi ? "Cài đặt workspace" : "Workspace settings"}>
    <OperationalHeader title={vi ? "Cài đặt" : "Settings"} description={vi ? "Tùy chọn trên trình duyệt, phục hồi dữ liệu và thông tin cấu hình hiện tại." : "Browser preferences, data recovery, and current configuration facts."} refresh={() => setRefresh(n => n + 1)} />
    <LocalConnection />
    <div className="operations-groups"><article className="operations-card"><h2>{vi ? "Hiển thị · lưu trên trình duyệt" : "Presentation · saved in this browser"}</h2><div className="operations-controls"><label>{vi ? "Giao diện" : "Theme"}<select aria-label={vi ? "Giao diện" : "Theme"} value={props.theme} onChange={e => props.onThemeChange(e.target.value as ThemePreference)}><option value="system">{vi ? "Theo hệ thống" : "System"}</option><option value="light">{vi ? "Sáng" : "Light"}</option><option value="dark">{vi ? "Tối" : "Dark"}</option></select></label><label>{vi ? "Ngôn ngữ" : "Language"}<select aria-label={vi ? "Ngôn ngữ" : "Language"} value={locale} onChange={e => setLocale(e.target.value as "en" | "vi")}><option value="en">English</option><option value="vi">Tiếng Việt</option></select></label></div><p>{vi ? "Chỉ thay đổi giao diện; không thay đổi cấu hình server." : "Changes presentation only; does not modify server configuration."}</p></article>
    <article className="operations-card"><h2>{vi ? "Lưu trữ và phục hồi trên trình duyệt" : "Browser storage and recovery"}</h2><dl><div><dt>{vi ? "Chế độ lưu trữ" : "Storage mode"}</dt><dd>{props.storageMode}</dd></div><div><dt>{vi ? "Quyền ghi" : "Writer status"}</dt><dd>{props.writerStatus.owned ? (vi ? "Có quyền ghi" : "Writer owned") : props.writerStatus.readOnly ? (vi ? "Chỉ đọc" : "Read only") : (vi ? "Tạm thời" : "Volatile")}</dd></div></dl>{props.storageWarning && <p role="status">{vi ? "Lưu trữ gặp sự cố. Xuất backup hoặc thử lấy quyền ghi." : "Storage reported a problem. Export a backup or retry writer access."}</p>}<div className="operations-controls"><button className="secondary-action-button" onClick={props.onExportBackup}>{vi ? "Xuất backup" : "Export backup"}</button><button className="secondary-action-button" disabled={busy} onClick={async () => { if (locked.current) return; locked.current = true; setBusy(true); const current = ++epoch.current; try { const status = await props.onRequestWriter(); if (current === epoch.current) setNotice(`${vi ? "Quyền ghi" : "Writer status"}: ${status.owned ? (vi ? "Có quyền ghi" : "Writer owned") : (vi ? "Chỉ đọc" : "Read only")}`); } catch { if (current === epoch.current) setNotice(vi ? "Không thể lấy quyền ghi." : "Could not obtain writer access."); } finally { locked.current = false; if (current === epoch.current) setBusy(false); } }}>{vi ? "Thử lấy quyền ghi" : "Retry writer access"}</button><label>{vi ? "Xem trước backup để nhập" : "Preview a backup to import"}<input type="file" accept=".json,application/json" disabled={busy} onChange={e => { void preview(e.target.files?.[0]); e.target.value = ""; }} /></label></div>{pending && <div className="operations-state"><h3>{vi ? "Xác nhận nhập" : "Confirm import"}</h3><p>{pending.bundle.conversations.length} {vi ? "cuộc trò chuyện" : "conversations"} · {pending.bundle.collections.length} {vi ? "bộ sưu tập evidence" : "evidence collections"}</p><p>{vi ? "Nhập qua quy trình hợp nhất hiện có. Nội dung backup không được hiển thị ở đây." : "Import through the existing merge workflow. Backup content is not displayed here."}</p><button className="primary-action-button" disabled={busy} onClick={() => void importBackup()}>{vi ? "Nhập backup" : "Import backup"}</button><button className="secondary-action-button" disabled={busy} onClick={() => { epoch.current++; setPending(null); }}>{vi ? "Hủy" : "Cancel"}</button></div>}{notice && <p role="status">{notice}</p>}<Link to="/collections?tab=conversations">{vi ? "Mở thư viện trình duyệt" : "Open browser library"}</Link></article>
    <article className="operations-card"><h2>{vi ? "Chính sách lưu giữ · chỉ đọc" : "Retention policy · read only"}</h2><dl><div><dt>Telemetry</dt><dd>{vi ? "30 ngày" : "30 days"}</dd></div><div><dt>{vi ? "Cửa sổ nhật ký" : "Log window"}</dt><dd>{vi ? "7 ngày" : "7 days"}</dd></div></dl><p>{vi ? "Chính sách DATA-005 cố định. API không hỗ trợ chỉnh sửa hay xóa nhật ký." : "Fixed DATA-005 policy. The API does not support retention edits or clearing logs."}</p></article>
    <article className="operations-card"><h2>{vi ? "Trạng thái provider · chỉ đọc" : "Provider status · read only"}</h2><ReadState {...provider} />{provider.data && <dl>{Object.entries(provider.data).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value.replaceAll("_", " ")}</dd></div>)}</dl>}<p>{vi ? "Credential status chỉ báo sự hiện diện; không xác minh sức khỏe provider." : "Credential status reports presence only; it does not probe provider health."}</p></article>
    <article className="operations-card"><h2>{vi ? "Quyền server · chỉ đọc" : "Server capabilities · read only"}</h2><ReadState {...config} />{config.data && <dl><div><dt>{vi ? "Chế độ triển khai" : "Deployment mode"}</dt><dd>{config.data.deployment_mode}</dd></div>{Object.entries(config.data.capabilities).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value ? (vi ? "Bật" : "Enabled") : (vi ? "Tắt" : "Disabled")}</dd></div>)}</dl>}</article>
    <article className="operations-card"><h2>{vi ? "Thông tin hệ thống · chỉ đọc" : "System facts · read only"}</h2><ReadState {...facts} />{facts.data && <dl><div><dt>API version</dt><dd>{facts.data.api_version}</dd></div><div><dt>{vi ? "Retrieval mặc định" : "Default retrieval"}</dt><dd>{facts.data.default_retrieval}</dd></div></dl>}<p>{vi ? "Không hỗ trợ đổi model, provider hay dataset từ Settings." : "Model, provider, and dataset changes are not supported by Settings."}</p><div className="operations-controls"><Link to="/models">{vi ? "Xem trạng thái model/provider" : "View model/provider status"}</Link><Link to="/datasets">{vi ? "Xem dataset" : "View datasets"}</Link><Link to="/settings?panel=architecture">{vi ? "Kiến trúc và trợ giúp" : "Architecture and help"}</Link></div></article></div>
  </section>;
}
