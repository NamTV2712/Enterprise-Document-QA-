import { useEffect, useRef, useState } from "react";
import {
  ArrowUpDown,
  Boxes,
  Cpu,
  Database,
  Layers,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { getSystemInfo } from "../lib/api";
import type { RetrievalPreset, SystemInfoResponse } from "../types";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";

type ModelTab = "embedding" | "generative" | "reranker";

const MODEL_TABS: Array<{ id: ModelTab; label: string; vi: string; icon: typeof Database }> = [
  { id: "embedding", label: "Embedding", vi: "Embedding", icon: Database },
  { id: "generative", label: "Generative", vi: "Sinh", icon: MessageSquare },
  { id: "reranker", label: "Reranker", vi: "Reranker", icon: ArrowUpDown },
];

function reportedText(value: string | null | undefined, vi: boolean): string {
  return value?.trim() ? value : (vi ? "Chưa có dữ liệu" : "Not reported");
}

function modelValue(info: SystemInfoResponse | null, tab: ModelTab): string | null {
  if (!info) return null;
  if (tab === "embedding") return info.retrieval.embedding_model ?? null;
  if (tab === "reranker") return info.retrieval.reranker_model ?? null;
  // The current backend intentionally does not expose a generative model
  // identity through /system/info. Keep this neutral until it does.
  return info.build.llm_model ?? null;
}

function buildValue(info: SystemInfoResponse | null, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = info?.build[key];
    if (value?.trim()) return value;
  }
  return null;
}

function capabilityLabel(value: boolean | undefined, vi: boolean): string {
  if (value === true) return vi ? "Có báo cáo" : "Reported available";
  if (value === false) return vi ? "Được báo cáo là không có" : "Reported unavailable";
  return vi ? "Chưa có dữ liệu" : "Not reported";
}

export function ModelsConsole() {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<ModelTab>("embedding");
  const requestId = useRef(0);

  const load = () => {
    const id = ++requestId.current;
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    void getSystemInfo(controller.signal)
      .then((info) => {
        if (id !== requestId.current) return;
        setSystemInfo(info);
      })
      .catch((reason) => {
        if (id !== requestId.current || (reason instanceof DOMException && reason.name === "AbortError")) return;
        setSystemInfo(null);
        setError(describeRequestError(reason, vi ? "Không thể tải thông tin cấu hình retrieval." : "Could not load retrieval configuration.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (id === requestId.current) setIsLoading(false);
      });
    return () => controller.abort();
  };

  useEffect(() => {
    const cleanup = load();
    return typeof cleanup === "function" ? cleanup : undefined;
    // Locale changes only change the error copy; reloading also refreshes the
    // authoritative snapshot shown by this read-only surface.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vi]);

  useEffect(() => () => {
    requestId.current += 1;
  }, []);

  const embeddingModel = modelValue(systemInfo, "embedding");
  const generativeModel = modelValue(systemInfo, "generative");
  const rerankerModel = modelValue(systemInfo, "reranker");
  const activeTab = MODEL_TABS.find((candidate) => candidate.id === tab) ?? MODEL_TABS[0];
  const ActiveIcon = activeTab.icon;
  const activeModel = modelValue(systemInfo, tab);
  const presets = systemInfo?.retrieval.presets ?? [];
  const defaultPreset = systemInfo?.retrieval.default;
  const buildRevision = buildValue(systemInfo, "GIT_REVISION", "git_revision", "revision");
  const buildVersion = buildValue(systemInfo, "BUILD_VERSION", "build_version", "version");

  const componentRows = [
    { id: "embedding", label: vi ? "Mô hình embedding" : "Embedding model", value: embeddingModel, field: "retrieval.embedding_model", icon: Database },
    { id: "generative", label: vi ? "Mô hình sinh" : "Generative model", value: generativeModel, field: "build.llm_model", icon: MessageSquare },
    { id: "reranker", label: vi ? "Mô hình reranker" : "Reranker model", value: rerankerModel, field: "retrieval.reranker_model", icon: ArrowUpDown },
  ];

  return (
    <section className="workspace-page workspace-page--wide console-view-enter" aria-labelledby="models-title">
      <div className="console-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><Cpu aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="models-title" className="console-page-header__title">{vi ? "Mô hình" : "Models"}</h1>
            <p className="console-page-header__subtitle">
              {vi
                ? "Cấu hình retrieval được backend báo cáo; chỉ đọc và không suy đoán provider hay thông số chưa công bố."
                : "Backend-reported retrieval configuration, read-only and neutral about fields it does not expose."}
            </p>
          </div>
        </div>
        <div className="console-page-header__actions">
          <span className="console-chip"><ShieldCheck aria-hidden="true" />{vi ? "Chỉ đọc" : "Read-only"}</span>
          <button type="button" className="console-btn" onClick={load} disabled={isLoading}>
            <RefreshCw className={isLoading ? "animate-spin" : ""} aria-hidden="true" />
            {vi ? "Làm mới" : "Refresh"}
          </button>
        </div>
      </div>

      {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="console-card">
          <div className="console-card__header">
            <div className="min-w-0">
              <h2 className="console-card__title">{vi ? "Cấu hình retrieval" : "Retrieval configuration"}</h2>
              <p className="console-card__subtitle">{vi ? "Các trường lấy trực tiếp từ /system/info." : "Fields read directly from /system/info."}</p>
            </div>
            <Workflow className="h-4 w-4 text-[var(--accent-text)]" aria-hidden="true" />
          </div>
          <div className="console-card__body space-y-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3">
                <div className="console-field__label">{vi ? "Preset mặc định" : "Default preset"}</div>
                <div className="mt-1 font-mono text-sm font-semibold text-[var(--text-primary)]">{reportedText(defaultPreset, vi)}</div>
              </div>
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3">
                <div className="console-field__label">{vi ? "Preset được báo cáo" : "Reported presets"}</div>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {presets.length > 0 ? presets.map((preset: RetrievalPreset) => <span className="console-chip" key={preset}>{preset}</span>) : <span className="text-sm text-[var(--text-muted)]">{vi ? "Chưa có dữ liệu" : "Not reported"}</span>}
                </div>
              </div>
            </div>
            <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3 text-xs text-[var(--text-muted)]">
              <div className="flex items-start gap-2">
                <Layers className="mt-0.5 h-4 w-4 flex-shrink-0 text-[var(--accent-text)]" aria-hidden="true" />
                <span>{vi ? "Provider, context length, dimensions, cost, latency, routing và A/B state không được endpoint hiện tại báo cáo." : "Provider, context length, dimensions, cost, latency, routing, and A/B state are not reported by the current endpoint."}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="console-card">
          <div className="console-card__header">
            <div className="min-w-0">
              <h2 className="console-card__title">{vi ? "Metadata runtime" : "Runtime metadata"}</h2>
              <p className="console-card__subtitle">{vi ? "Chỉ hiển thị các capability và revision được allowlist." : "Only allowlisted capabilities and revisions are shown."}</p>
            </div>
            <Boxes className="h-4 w-4 text-[var(--accent-text)]" aria-hidden="true" />
          </div>
          <dl className="console-card__body console-meta-grid">
            <div><dt>API version</dt><dd className="font-mono text-xs">{reportedText(systemInfo?.api_version, vi)}</dd></div>
            <div><dt>{vi ? "Build revision" : "Build revision"}</dt><dd className="break-all font-mono text-xs">{reportedText(buildRevision, vi)}</dd></div>
            <div><dt>{vi ? "Build version" : "Build version"}</dt><dd className="font-mono text-xs">{reportedText(buildVersion, vi)}</dd></div>
            <div><dt>{vi ? "Stage events" : "Stage events"}</dt><dd>{capabilityLabel(systemInfo?.capabilities?.stage_events, vi)}</dd></div>
            <div><dt>{vi ? "Indexed viewer" : "Indexed viewer"}</dt><dd>{capabilityLabel(systemInfo?.capabilities?.document_indexed_viewer, vi)}</dd></div>
            <div><dt>{vi ? "Original viewer" : "Original viewer"}</dt><dd>{capabilityLabel(systemInfo?.capabilities?.original_document_viewer?.enabled, vi)}</dd></div>
          </dl>
        </div>
      </div>

      <div className="console-card">
        <div className="console-tabs m-3" role="tablist" aria-label={vi ? "Nhóm thành phần retrieval" : "Retrieval component groups"}>
          {MODEL_TABS.map((candidate) => {
            const Icon = candidate.icon;
            return (
              <button key={candidate.id} type="button" role="tab" aria-selected={tab === candidate.id} className={`console-tab ${tab === candidate.id ? "is-active" : ""}`} onClick={() => setTab(candidate.id)}>
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                {vi ? candidate.vi : candidate.label}
              </button>
            );
          })}
        </div>
        <div className="console-card__body">
          <div className="mb-3 flex items-start gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3">
            <span className="console-stat__icon"><ActiveIcon aria-hidden="true" /></span>
            <div className="min-w-0">
              <div className="console-field__label">{vi ? activeTab.vi : activeTab.label}</div>
              <div className="break-all font-mono text-sm font-semibold text-[var(--text-primary)]">{reportedText(activeModel, vi)}</div>
            </div>
          </div>
          <div className="console-table-wrap">
            <table className="console-table">
              <thead>
                <tr>
                  <th scope="col">{vi ? "Vai trò" : "Role"}</th>
                  <th scope="col">{vi ? "Giá trị được báo cáo" : "Reported value"}</th>
                  <th scope="col">{vi ? "Trường nguồn" : "Source field"}</th>
                </tr>
              </thead>
              <tbody>
                {componentRows.map((row) => {
                  const Icon = row.icon;
                  return (
                    <tr key={row.id} className={row.id === tab ? "is-selected" : undefined} aria-selected={row.id === tab}>
                      <td><span className="flex items-center gap-2.5"><span className="console-stat__icon"><Icon aria-hidden="true" /></span><span className="console-table__primary">{row.label}</span></span></td>
                      <td className="break-all font-mono text-[13px]">{reportedText(row.value, vi)}</td>
                      <td className="console-table__secondary font-mono text-xs">/system/info · {row.field}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        <div className="console-card__footer">
          <span className="text-xs text-[var(--text-muted)]">
            {vi
              ? "Không có trường báo cáo thì giữ nguyên trạng thái chưa có dữ liệu; UI không suy đoán danh tính model."
              : "Missing fields remain unavailable; the UI does not infer model identity from a mockup."}
          </span>
        </div>
      </div>
    </section>
  );
}
