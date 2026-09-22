import { useEffect, useRef, useState } from "react";
import {
  Database,
  FileStack,
  FileText,
  RefreshCw,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { getDocuments, getSystemInfo } from "../lib/api";
import type { SystemInfoResponse } from "../types";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";

interface PipelineConsoleProps {
  healthData: {
    pipeline_ready?: boolean;
    corpus?: { searchable_company_count?: number; indexed_chunk_count?: number };
  } | null;
}

interface PipelineSnapshot {
  documents: number | null;
  companies: number | null;
  chunks: number | null;
  defaultPreset: string | null;
  apiVersion: string | null;
  buildRevision: string | null;
  buildVersion: string | null;
  ready: boolean | null;
}

function numberText(value: number | null, vi: boolean): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString(vi ? "vi-VN" : "en-US")
    : (vi ? "Chưa có dữ liệu" : "Not reported");
}

function textValue(value: string | null | undefined, vi: boolean): string {
  return value?.trim() ? value : (vi ? "Chưa có dữ liệu" : "Not reported");
}

function readinessText(value: boolean | null, vi: boolean): string {
  if (value === true) return vi ? "Sẵn sàng" : "Ready";
  if (value === false) return vi ? "Chưa sẵn sàng" : "Not ready";
  return vi ? "Chưa có dữ liệu" : "Not reported";
}

function buildValue(info: SystemInfoResponse | null, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = info?.build[key];
    if (value?.trim()) return value;
  }
  return null;
}

export function PipelineConsole({ healthData }: PipelineConsoleProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [snapshot, setSnapshot] = useState<PipelineSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const load = () => {
    const id = ++requestId.current;
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    void Promise.all([
      getDocuments({ ticker: null, section: null, search: "", page: 1, page_size: 1 }, controller.signal).catch(() => null),
      getSystemInfo(controller.signal).catch(() => null),
    ]).then(([catalog, info]) => {
      if (id !== requestId.current) return;
      if (!catalog && !info) {
        setSnapshot(null);
        setError(vi ? "Không thể tải snapshot serving từ backend." : "Could not load the serving snapshot from the backend.");
        setIsLoading(false);
        return;
      }
      const corpusRecord = (info?.corpus ?? {}) as Record<string, unknown>;
      setSnapshot({
        documents: catalog?.total ?? null,
        companies: typeof healthData?.corpus?.searchable_company_count === "number"
          ? healthData.corpus.searchable_company_count
          : typeof corpusRecord.searchable_company_count === "number" ? corpusRecord.searchable_company_count : null,
        chunks: typeof healthData?.corpus?.indexed_chunk_count === "number"
          ? healthData.corpus.indexed_chunk_count
          : typeof corpusRecord.indexed_chunk_count === "number" ? corpusRecord.indexed_chunk_count : null,
        defaultPreset: info?.retrieval.default ?? null,
        apiVersion: info?.api_version ?? null,
        buildRevision: buildValue(info, "GIT_REVISION", "git_revision", "revision"),
        buildVersion: buildValue(info, "BUILD_VERSION", "build_version", "version"),
        ready: typeof healthData?.pipeline_ready === "boolean" ? healthData.pipeline_ready : null,
      });
      setIsLoading(false);
    });
    return () => controller.abort();
  };

  useEffect(() => {
    const cleanup = load();
    return typeof cleanup === "function" ? cleanup : undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vi, healthData?.pipeline_ready, healthData?.corpus?.searchable_company_count, healthData?.corpus?.indexed_chunk_count]);

  useEffect(() => () => {
    requestId.current += 1;
  }, []);

  const documents = snapshot?.documents ?? null;
  const companies = snapshot?.companies ?? null;
  const chunks = snapshot?.chunks ?? null;
  const ready = snapshot?.ready ?? (healthData?.pipeline_ready ?? null);

  return (
    <section className="workspace-page workspace-page--wide console-view-enter" aria-labelledby="pipeline-title">
      <div className="console-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><Workflow aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="pipeline-title" className="console-page-header__title">Pipeline</h1>
            <p className="console-page-header__subtitle">
              {vi
                ? "Snapshot chỉ đọc của corpus đang phục vụ truy vấn; không giả lập lịch sử build hay trạng thái từng stage."
                : "A read-only snapshot of the corpus serving queries; build history and per-stage status are not inferred."}
            </p>
          </div>
        </div>
        <div className="console-page-header__actions">
          <span className="console-chip"><ShieldCheck aria-hidden="true" />{readinessText(ready, vi)}</span>
          <button type="button" className="console-btn" onClick={load} disabled={isLoading}>
            <RefreshCw className={isLoading ? "animate-spin" : ""} aria-hidden="true" />
            {vi ? "Làm mới" : "Refresh"}
          </button>
        </div>
      </div>

      <div className="console-layout console-layout--pipeline">
        <div className="console-layout__main">
          {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}
          {isLoading && !snapshot && <div className="console-loading" role="status"><span className="console-loading__spinner" aria-hidden="true" />{vi ? "Đang tải snapshot…" : "Loading snapshot…"}</div>}

          <div className="console-stats">
            <div className="console-stat">
              <div className="console-stat__icon"><FileText aria-hidden="true" /></div>
              <div className="min-w-0"><div className="console-stat__value">{numberText(documents, vi)}</div><div className="console-stat__label">{vi ? "Tổng catalog" : "Catalog documents"}</div><div className="console-stat__hint">{vi ? "GET /documents total" : "GET /documents total"}</div></div>
            </div>
            <div className="console-stat">
              <div className="console-stat__icon"><Database aria-hidden="true" /></div>
              <div className="min-w-0"><div className="console-stat__value">{numberText(companies, vi)}</div><div className="console-stat__label">{vi ? "Công ty searchable" : "Searchable companies"}</div><div className="console-stat__hint">{vi ? "/health hoặc /system/info" : "/health or /system/info"}</div></div>
            </div>
            <div className="console-stat">
              <div className="console-stat__icon"><FileStack aria-hidden="true" /></div>
              <div className="min-w-0"><div className="console-stat__value">{numberText(chunks, vi)}</div><div className="console-stat__label">{vi ? "Indexed chunks" : "Indexed chunks"}</div><div className="console-stat__hint">{vi ? "Chỉ số corpus được báo cáo" : "Reported corpus index"}</div></div>
            </div>
            <div className="console-stat">
              <div className="console-stat__icon console-stat__icon--success"><ShieldCheck aria-hidden="true" /></div>
              <div className="min-w-0"><div className="console-stat__value text-base">{readinessText(ready, vi)}</div><div className="console-stat__label">{vi ? "Readiness" : "Readiness"}</div><div className="console-stat__hint">{vi ? "Trạng thái health hiện tại" : "Current health state"}</div></div>
            </div>
          </div>

          <div className="console-card">
            <div className="console-card__header">
              <div className="min-w-0">
                <h2 className="console-card__title">{vi ? "Serving corpus snapshot" : "Serving corpus snapshot"}</h2>
                <p className="console-card__subtitle">{vi ? "Các trường được lấy từ catalog và health/system info." : "Fields sourced from the catalog and health/system info."}</p>
              </div>
              <Database className="h-4 w-4 text-[var(--accent-text)]" aria-hidden="true" />
            </div>
            <div className="console-card__body">
              <div className="console-table-wrap">
                <table className="console-table">
                  <thead><tr><th scope="col">{vi ? "Trường" : "Field"}</th><th scope="col">{vi ? "Giá trị" : "Value"}</th><th scope="col">{vi ? "Nguồn" : "Source"}</th></tr></thead>
                  <tbody>
                    <tr><td className="console-table__primary">{vi ? "Tổng catalog" : "Catalog total"}</td><td>{numberText(documents, vi)}</td><td className="console-table__secondary font-mono text-xs">GET /documents</td></tr>
                    <tr><td className="console-table__primary">{vi ? "Searchable companies" : "Searchable companies"}</td><td>{numberText(companies, vi)}</td><td className="console-table__secondary font-mono text-xs">GET /health</td></tr>
                    <tr><td className="console-table__primary">{vi ? "Indexed chunks" : "Indexed chunks"}</td><td>{numberText(chunks, vi)}</td><td className="console-table__secondary font-mono text-xs">GET /health</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="console-card">
            <div className="console-card__body flex items-start gap-3 text-sm text-[var(--text-muted)]">
              <ShieldCheck className="mt-0.5 h-4 w-4 flex-shrink-0 text-[var(--accent-text)]" aria-hidden="true" />
              <p className="m-0 leading-relaxed">
                {vi
                  ? "Đây là snapshot serving hiện tại. UI không hiển thị generation ID, build history, throughput, thời lượng stage hoặc nút chạy pipeline khi backend chưa cung cấp các trường đó."
                  : "This is the current serving snapshot. Generation IDs, build history, throughput, stage timings, and pipeline run controls stay absent because the backend does not provide them."}
              </p>
            </div>
          </div>
        </div>

        <aside className="console-layout__aside" aria-label={vi ? "Chi tiết serving contract" : "Serving contract details"}>
          <div className="console-card">
            <div className="console-card__header">
              <div className="min-w-0">
                <h2 className="console-card__title">{vi ? "Serving contract" : "Serving contract"}</h2>
                <p className="console-card__subtitle">{vi ? "Metadata allowlist từ /system/info." : "Allowlisted metadata from /system/info."}</p>
              </div>
              <Workflow className="h-4 w-4 text-[var(--accent-text)]" aria-hidden="true" />
            </div>
            <dl className="console-card__body console-meta-grid">
              <div><dt>{vi ? "Retrieval preset" : "Retrieval preset"}</dt><dd className="font-mono text-xs">{textValue(snapshot?.defaultPreset, vi)}</dd></div>
              <div><dt>API version</dt><dd className="font-mono text-xs">{textValue(snapshot?.apiVersion, vi)}</dd></div>
              <div><dt>{vi ? "Build revision" : "Build revision"}</dt><dd className="break-all font-mono text-xs">{textValue(snapshot?.buildRevision, vi)}</dd></div>
              <div><dt>{vi ? "Build version" : "Build version"}</dt><dd className="font-mono text-xs">{textValue(snapshot?.buildVersion, vi)}</dd></div>
              <div><dt>Readiness</dt><dd>{readinessText(ready, vi)}</dd></div>
            </dl>
          </div>
        </aside>
      </div>
    </section>
  );
}
