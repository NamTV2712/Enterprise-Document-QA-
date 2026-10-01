import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  CircleSlash2,
  Cpu,
  Database,
  LoaderCircle,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";

import { ApiError, getModels, testModelRuntimeIdentity } from "../lib/api";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";
import type {
  ModelAvailabilityStatus,
  ModelRegistryEntry,
  ModelRole,
  ModelTestResponse,
} from "../types";

type RoleFilter = "all" | ModelRole;

const ROLE_ORDER: ModelRole[] = ["generator", "embedding", "reranker"];

const ROLE_ICON = {
  generator: MessageSquare,
  embedding: Database,
  reranker: Activity,
} as const;

function roleLabel(role: ModelRole, vi: boolean): string {
  if (role === "generator") return vi ? "Mô hình sinh" : "Generator";
  if (role === "embedding") return vi ? "Mô hình embedding" : "Embedding";
  return vi ? "Mô hình reranker" : "Reranker";
}

function reported(value: string | null | undefined, vi: boolean): string {
  return value?.trim() ? value : vi ? "Không được ghi nhận" : "Not recorded";
}

function availabilityLabel(status: ModelAvailabilityStatus, vi: boolean): string {
  if (status === "available") return vi ? "Khả dụng" : "Available";
  if (status === "unavailable") return vi ? "Không khả dụng" : "Unavailable";
  return vi ? "Chưa xác định" : "Unknown";
}

function ModelStatePill({ status, vi }: { status: ModelAvailabilityStatus; vi: boolean }) {
  const Icon = status === "available" ? CheckCircle2 : status === "unavailable" ? CircleSlash2 : TriangleAlert;
  return (
    <span className={`registry-state registry-state--${status}`}>
      <Icon aria-hidden="true" />
      {availabilityLabel(status, vi)}
    </span>
  );
}

function modelTestFailure(error: unknown, vi: boolean): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return vi ? "Cần quyền truy cập workspace cục bộ để chạy kiểm tra này." : "Local workspace access is required to run this check.";
    if (error.status === 403) return vi ? "Kiểm tra thực thi bị tắt hoặc yêu cầu không đến từ workspace cục bộ." : "Execution checks are disabled or this request is outside the local workspace.";
    if (error.status === 404) return vi ? "Kiểm tra này không khả dụng trong chế độ triển khai hiện tại." : "This check is unavailable in the current deployment mode.";
    if (error.status === 422) return vi ? "Backend đã từ chối loại kiểm tra này." : "The backend rejected this test type.";
  }
  return describeRequestError(
    error,
    vi ? "Không thể chạy kiểm tra danh tính runtime." : "Could not run the runtime identity check.",
    vi ? "vi" : "en",
  ).message;
}

export function ModelsConsole() {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [items, setItems] = useState<ModelRegistryEntry[]>([]);
  const [selectedId, setSelectedId] = useState<ModelRole | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [testPending, setTestPending] = useState(false);
  const [testResult, setTestResult] = useState<ModelTestResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const listLifetime = useRef(0);
  const testLifetime = useRef(0);
  const testController = useRef<AbortController | null>(null);

  useEffect(() => {
    const lifetime = ++listLifetime.current;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void getModels(roleFilter === "all" ? null : roleFilter, controller.signal)
      .then((response) => {
        if (controller.signal.aborted || lifetime !== listLifetime.current) return;
        const ordered = [...response.items].sort((left, right) => ROLE_ORDER.indexOf(left.role) - ROLE_ORDER.indexOf(right.role));
        setItems(ordered);
        setSelectedId((current) => ordered.some((item) => item.id === current) ? current : ordered[0]?.id ?? null);
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted || lifetime !== listLifetime.current) return;
        setItems([]);
        setSelectedId(null);
        setError(describeRequestError(reason, vi ? "Không thể tải registry mô hình." : "Could not load the model registry.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (!controller.signal.aborted && lifetime === listLifetime.current) setLoading(false);
      });
    return () => controller.abort();
  }, [refreshVersion, roleFilter, vi]);

  useEffect(() => () => {
    listLifetime.current += 1;
    testLifetime.current += 1;
    testController.current?.abort();
  }, []);

  const selected = useMemo(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  );

  const selectModel = useCallback((modelId: ModelRole) => {
    testController.current?.abort();
    testLifetime.current += 1;
    setSelectedId(modelId);
    setTestPending(false);
    setTestResult(null);
    setTestError(null);
  }, []);

  const runIdentityTest = useCallback(() => {
    if (!selected || testPending || !selected.test_capabilities.includes("runtime_identity")) return;
    const modelId = selected.id;
    const lifetime = ++testLifetime.current;
    const controller = new AbortController();
    testController.current?.abort();
    testController.current = controller;
    setTestPending(true);
    setTestResult(null);
    setTestError(null);
    void testModelRuntimeIdentity(modelId, controller.signal)
      .then((response) => {
        if (controller.signal.aborted || lifetime !== testLifetime.current || response.model_id !== modelId) return;
        setTestResult(response);
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted || lifetime !== testLifetime.current) return;
        setTestError(modelTestFailure(reason, vi));
      })
      .finally(() => {
        if (!controller.signal.aborted && lifetime === testLifetime.current) setTestPending(false);
      });
  }, [selected, testPending, vi]);

  const configuredCount = items.filter((item) => item.configuration_status === "configured").length;
  const loadedCount = items.filter((item) => item.load_status === "loaded").length;
  const unknownCount = items.filter((item) => item.availability_status === "unknown").length;

  return (
    <section className="workspace-page workspace-page--wide registry-workspace console-view-enter" aria-labelledby="models-title">
      <header className="console-page-header registry-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><Cpu aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="models-title" className="console-page-header__title">{vi ? "Mô hình" : "Models"}</h1>
            <p className="console-page-header__subtitle">
              {vi ? "Danh tính cấu hình và runtime được backend ghi nhận — không suy đoán sức khoẻ provider." : "Backend-reported configuration and runtime identity—without guessing provider health."}
            </p>
          </div>
        </div>
        <div className="console-page-header__actions">
          <span className="console-chip"><ShieldCheck aria-hidden="true" />{vi ? "Duyệt không gọi provider" : "Provider-free browsing"}</span>
          <button type="button" className="console-btn" onClick={() => setRefreshVersion((value) => value + 1)} disabled={loading}>
            <RefreshCw className={loading ? "animate-spin" : ""} aria-hidden="true" />
            {vi ? "Làm mới" : "Refresh"}
          </button>
        </div>
      </header>

      <div className="registry-summary" aria-label={vi ? "Tóm tắt registry mô hình" : "Model registry summary"}>
        <div><strong>{items.length}</strong><span>{vi ? "vai trò hiển thị" : "roles shown"}</span></div>
        <div><strong>{configuredCount}</strong><span>{vi ? "đã cấu hình" : "configured"}</span></div>
        <div><strong>{loadedCount}</strong><span>{vi ? "đã tải" : "loaded"}</span></div>
        <div><strong>{unknownCount}</strong><span>{vi ? "khả dụng chưa rõ" : "availability unknown"}</span></div>
      </div>

      <div className="registry-filter-bar" role="tablist" aria-label={vi ? "Lọc theo vai trò mô hình" : "Filter by model role"}>
        {(["all", ...ROLE_ORDER] as RoleFilter[]).map((role) => (
          <button key={role} type="button" role="tab" aria-selected={roleFilter === role} className={`registry-filter ${roleFilter === role ? "is-active" : ""}`} onClick={() => setRoleFilter(role)}>
            {role === "all" ? (vi ? "Tất cả vai trò" : "All roles") : roleLabel(role, vi)}
          </button>
        ))}
      </div>

      {error && (
        <div className="workspace-alert workspace-alert--error registry-alert" role="alert">
          <span>{error}</span>
          <button type="button" className="console-btn" onClick={() => setRefreshVersion((value) => value + 1)}><RotateCcw aria-hidden="true" />{vi ? "Thử lại" : "Retry"}</button>
        </div>
      )}

      <div className="registry-layout">
        <section className="console-card registry-list" aria-labelledby="model-registry-heading" aria-busy={loading}>
          <div className="console-card__header">
            <div>
              <h2 id="model-registry-heading" className="console-card__title">{vi ? "Registry runtime" : "Runtime registry"}</h2>
              <p className="console-card__subtitle">{vi ? "Chọn một model để xem các trạng thái riêng biệt." : "Select a model to inspect each state independently."}</p>
            </div>
            {loading && <span className="console-loading" role="status"><span className="console-loading__spinner" />{vi ? "Đang tải…" : "Loading…"}</span>}
          </div>

          {!loading && !error && items.length === 0 ? (
            <div className="console-empty" role="status"><CircleSlash2 aria-hidden="true" /><strong>{vi ? "Không có model nào" : "No models reported"}</strong><p>{vi ? "Registry đã tải thành công nhưng không trả về entry nào cho bộ lọc này." : "The registry loaded successfully but returned no entries for this filter."}</p></div>
          ) : (
            <>
              <div className="registry-table-wrap">
                <table className="registry-table">
                  <thead><tr><th>{vi ? "Vai trò" : "Role"}</th><th>{vi ? "Danh tính cấu hình" : "Configured identity"}</th><th>{vi ? "Tải" : "Load"}</th><th>{vi ? "Khả dụng" : "Availability"}</th><th><span className="sr-only">{vi ? "Chi tiết" : "Details"}</span></th></tr></thead>
                  <tbody>
                    {items.map((item) => {
                      const Icon = ROLE_ICON[item.role];
                      return (
                        <tr key={item.id} className={selectedId === item.id ? "is-selected" : ""} aria-selected={selectedId === item.id}>
                          <td><span className="registry-role"><span className="registry-role__icon"><Icon aria-hidden="true" /></span><span><strong>{roleLabel(item.role, vi)}</strong><small>{item.provider === "groq" ? "Groq" : "Hugging Face"}</small></span></span></td>
                          <td><strong className="registry-identity">{reported(item.configured_model_id, vi)}</strong><small className="registry-secondary">{reported(item.configured_revision, vi)}</small></td>
                          <td><span className={`registry-state registry-state--${item.load_status}`}>{item.load_status === "loaded" ? (vi ? "Đã tải" : "Loaded") : item.load_status === "not_loaded" ? (vi ? "Chưa tải" : "Not loaded") : (vi ? "Chưa rõ" : "Unknown")}</span></td>
                          <td><ModelStatePill status={item.availability_status} vi={vi} /></td>
                          <td><button type="button" className="registry-row-action" aria-label={`${vi ? "Kiểm tra" : "Inspect"} ${roleLabel(item.role, vi)}`} onClick={() => selectModel(item.id)}><ArrowRight aria-hidden="true" /></button></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="registry-mobile-list">
                {items.map((item) => {
                  const Icon = ROLE_ICON[item.role];
                  return (
                    <button key={item.id} type="button" className={`registry-mobile-card ${selectedId === item.id ? "is-selected" : ""}`} aria-pressed={selectedId === item.id} onClick={() => selectModel(item.id)}>
                      <span className="registry-role"><span className="registry-role__icon"><Icon aria-hidden="true" /></span><span><strong>{roleLabel(item.role, vi)}</strong><small>{reported(item.configured_model_id, vi)}</small></span></span>
                      <ModelStatePill status={item.availability_status} vi={vi} />
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </section>

        <aside className="console-card registry-detail" aria-label={selected ? `${roleLabel(selected.role, vi)} ${vi ? "chi tiết" : "details"}` : (vi ? "Chi tiết model" : "Model details")}>
          {!selected ? (
            <div className="console-empty"><Cpu aria-hidden="true" /><strong>{vi ? "Chọn một model" : "Select a model"}</strong><p>{vi ? "Chi tiết cấu hình và runtime sẽ xuất hiện ở đây." : "Configuration and runtime details will appear here."}</p></div>
          ) : (
            <>
              <div className="console-card__header registry-detail__header">
                <div><p className="registry-eyebrow">{roleLabel(selected.role, vi)}</p><h2 className="console-card__title registry-detail__identity">{reported(selected.configured_model_id, vi)}</h2></div>
                <ModelStatePill status={selected.availability_status} vi={vi} />
              </div>
              <div className="console-card__body registry-detail__body">
                {selected.availability_reason && <p className="registry-explanation"><TriangleAlert aria-hidden="true" />{selected.availability_reason}</p>}
                <dl className="registry-facts">
                  <div><dt>{vi ? "Trạng thái cấu hình" : "Configuration"}</dt><dd>{selected.configuration_status === "configured" ? (vi ? "Đã cấu hình" : "Configured") : (vi ? "Chưa cấu hình" : "Not configured")}</dd></div>
                  <div><dt>{vi ? "Trạng thái tải" : "Load state"}</dt><dd>{selected.load_status === "loaded" ? (vi ? "Đã tải" : "Loaded") : selected.load_status === "not_loaded" ? (vi ? "Chưa tải" : "Not loaded") : (vi ? "Chưa xác định" : "Unknown")}</dd></div>
                  <div><dt>{vi ? "Danh tính runtime" : "Runtime identity"}</dt><dd className="registry-identity">{reported(selected.runtime_model_id, vi)}</dd></div>
                  <div><dt>{vi ? "Revision cấu hình" : "Configured revision"}</dt><dd className="registry-identity">{reported(selected.configured_revision, vi)}</dd></div>
                  <div><dt>{vi ? "Revision runtime" : "Runtime revision"}</dt><dd className="registry-identity">{reported(selected.runtime_revision, vi)}</dd></div>
                  <div><dt>{vi ? "Credential provider" : "Provider credential"}</dt><dd>{selected.credential_status === "configured" ? (vi ? "Đã cấu hình" : "Configured") : selected.credential_status === "not_configured" ? (vi ? "Chưa cấu hình" : "Not configured") : (vi ? "Không yêu cầu" : "Not required")}</dd></div>
                </dl>

                <div className="registry-test">
                  <div><h3>{vi ? "Kiểm tra danh tính runtime" : "Runtime identity check"}</h3><p>{vi ? "So sánh metadata đã tải; không gọi provider và không chạy inference." : "Compares loaded metadata; it does not call the provider or run inference."}</p></div>
                  <button type="button" className="console-btn console-btn--accent" onClick={runIdentityTest} disabled={testPending || !selected.test_capabilities.includes("runtime_identity")}>
                    {testPending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Activity aria-hidden="true" />}
                    {testPending ? (vi ? "Đang kiểm tra…" : "Checking…") : (vi ? "Chạy kiểm tra" : "Run identity check")}
                  </button>
                </div>

                {testError && <div className="workspace-alert workspace-alert--error registry-test-result" role="alert">{testError}</div>}
                {testResult && (
                  <div className={`registry-test-result registry-test-result--${testResult.result}`} role="status" aria-live="polite">
                    <div className="registry-test-result__head"><strong>{testResult.result === "passed" ? (vi ? "Đã qua" : "Passed") : testResult.result === "failed" ? (vi ? "Không khớp" : "Failed") : (vi ? "Không thể xác định" : "Unavailable")}</strong><span>{vi ? "Provider đã gọi:" : "Provider executed:"} {testResult.provider_executed ? (vi ? "Có" : "Yes") : (vi ? "Không" : "No")}</span></div>
                    <ul>{testResult.checks.map((check) => <li key={check.id}><span>{check.id.replaceAll("_", " ")}</span><strong>{check.status}</strong>{check.reason && <small>{check.reason}</small>}</li>)}</ul>
                  </div>
                )}
              </div>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
