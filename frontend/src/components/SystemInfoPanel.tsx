import { useCallback, useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, Clipboard, Cpu, Database, FileText, Info, RefreshCw } from "lucide-react";
import { getSystemInfo } from "../lib/api";
import { SystemInfoResponse } from "../types";
import { useLocale } from "../lib/i18n";
import { getWorkspaceNavItem } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";

const WORKSPACE_META = getWorkspaceNavItem("system");

interface SystemInfoPanelProps {
  onOpenDocuments?: () => void;
  onOpenRetrieval?: () => void;
  onOpenEvaluation?: () => void;
}

export function SystemInfoPanel({ onOpenDocuments, onOpenRetrieval, onOpenEvaluation }: SystemInfoPanelProps) {
  const { locale, t } = useLocale();
  const vi = locale === "vi";
  const ToolIcon = getSemanticIcon(WORKSPACE_META.icon);
  const [info, setInfo] = useState<SystemInfoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    void getSystemInfo(controller.signal).then(setInfo).catch((reason) => {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "Could not load system information.");
    });
    return () => controller.abort();
  }, [refreshNonce]);

  const copySafeSummary = useCallback(async () => {
    if (!info) return;
    const summary = [
      `SEC Research API ${info.api_version}`,
      `Corpus: ${String(info.corpus.searchable_company_count ?? "unknown")} searchable companies; ${String(info.corpus.indexed_chunk_count ?? "unknown")} indexed chunks`,
      `Default retrieval: ${info.retrieval.default}`,
      `Reader: indexed=${info.capabilities?.document_indexed_viewer === true ? "available" : "unknown"}; normalized=${info.capabilities?.original_document_viewer?.enabled === true ? "available" : "unknown"}; PDF=unavailable`,
      "No secrets or filesystem paths are included in this summary.",
    ].join("\n");
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(summary);
      setCopyStatus("copied");
      window.setTimeout(() => setCopyStatus("idle"), 1800);
    } catch {
      setCopyStatus("failed");
      window.setTimeout(() => setCopyStatus("idle"), 2200);
    }
  }, [info]);

  const corpus = info?.corpus ?? {};
  const buildEntries = Object.entries(info?.build ?? {});
  return (
    <section className="mx-auto w-full max-w-6xl space-y-5 px-3 py-5 md:px-6" aria-labelledby="system-info-title">
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-emerald-500/10 p-3 text-emerald-600 dark:text-emerald-300"><ToolIcon className="h-5 w-5" aria-hidden="true" /></div>
        <div><h1 id="system-info-title" className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">{vi ? "System & provenance" : "System & provenance"}</h1><p className="mt-1 max-w-2xl text-sm leading-relaxed text-[var(--text-muted)]">{t(WORKSPACE_META.descriptionKey)} {vi ? "Metadata allowlisted không lộ secret hay filesystem path." : "Allowlisted metadata does not expose secrets or filesystem paths."}</p></div>
      </div>
      {error && <div role="alert" className="rounded-xl border border-rose-300/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-700 dark:text-rose-300">{error}</div>}
      {!info && !error && <div role="status" className="rounded-2xl border border-dashed border-[var(--border-strong)] px-5 py-12 text-center text-sm text-[var(--text-muted)]">{vi ? "Đang tải metadata…" : "Loading metadata…"}</div>}
      {info && <>
        <div className="system-info-actions" aria-label={vi ? "Thao tác hệ thống" : "System actions"}>
          <button type="button" className="primary-action-button" onClick={onOpenDocuments} disabled={!onOpenDocuments}><FileText className="h-4 w-4" aria-hidden="true" />{vi ? "Mở Documents" : "Open Documents"}<ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></button>
          <button type="button" className="secondary-action-button" onClick={() => setRefreshNonce((value) => value + 1)}><RefreshCw className="h-4 w-4" aria-hidden="true" />{vi ? "Làm mới trạng thái" : "Refresh status"}</button>
          <button type="button" className="secondary-action-button" onClick={() => void copySafeSummary()}><Clipboard className="h-4 w-4" aria-hidden="true" />{copyStatus === "copied" ? (vi ? "Đã sao chép" : "Copied") : copyStatus === "failed" ? (vi ? "Không thể sao chép" : "Copy failed") : (vi ? "Sao chép tóm tắt an toàn" : "Copy safe summary")}</button>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)]"><Database className="h-4 w-4 text-cyan-600 dark:text-cyan-300" />{vi ? "Corpus" : "Corpus"}</div><div className="mt-3 text-2xl font-bold text-[var(--text-primary)]">{String(corpus.searchable_company_count ?? "—")}</div><div className="text-xs text-[var(--text-muted)]">{vi ? "công ty searchable" : "searchable companies"}</div><div className="mt-3 text-sm text-[var(--text-muted)]">{String(corpus.indexed_chunk_count ?? "—")} {vi ? "chunks" : "indexed chunks"}</div></article>
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)]"><Cpu className="h-4 w-4 text-violet-600 dark:text-violet-300" />{vi ? "Retrieval models" : "Retrieval models"}</div><div className="mt-3 break-all text-sm font-semibold text-[var(--text-primary)]">{info.retrieval.embedding_model ?? "—"}</div><div className="mt-2 break-all text-xs text-[var(--text-muted)]">{info.retrieval.reranker_model ?? "—"}</div></article>
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)]"><CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-300" />{vi ? "Contract" : "Contract"}</div><div className="mt-3 text-sm font-semibold text-[var(--text-primary)]">{vi ? "Provider-free tools" : "Provider-free tools"}</div><div className="mt-2 text-xs leading-relaxed text-[var(--text-muted)]">{vi ? "Retrieval Lab và Document Explorer chỉ đọc metadata đã nạp; không gửi câu hỏi tới LLM." : "Retrieval Lab and Document Explorer read loaded metadata only; they do not send questions to an LLM."}</div></article>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><h2 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)]"><FileText className="h-4 w-4 text-cyan-600 dark:text-cyan-300" />{vi ? "Reader availability" : "Reader availability"}</h2><dl className="mt-3 space-y-2 text-xs"><div className="flex justify-between gap-3"><dt className="text-[var(--text-muted)]">{vi ? "Indexed excerpt" : "Indexed excerpt"}</dt><dd className="font-semibold text-emerald-600 dark:text-emerald-300">{info.capabilities?.document_indexed_viewer === true ? (vi ? "Có sẵn" : "Available") : (vi ? "Chưa rõ" : "Unknown")}</dd></div><div className="flex justify-between gap-3"><dt className="text-[var(--text-muted)]">{vi ? "Structured / normalized" : "Structured / normalized"}</dt><dd className="font-semibold text-emerald-600 dark:text-emerald-300">{info.capabilities?.original_document_viewer?.enabled === true ? (vi ? "Có sẵn" : "Available") : (vi ? "Chưa rõ" : "Unknown")}</dd></div><div className="flex justify-between gap-3"><dt className="text-[var(--text-muted)]">PDF</dt><dd className="font-semibold text-[var(--text-muted)]">{vi ? "Chưa có nguồn đã xác minh" : "No verified source"}</dd></div></dl><p className="mt-3 text-xs leading-relaxed text-[var(--text-muted)]">{vi ? "Reader hiển thị representation đã xác minh; không bịa page count hoặc PDF khi corpus chưa có PDF." : "The reader uses verified representations; no page count or PDF is invented while the corpus has no PDF."}</p></article>
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><h2 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)]"><Info className="h-4 w-4" />{vi ? "Provenance & next actions" : "Provenance & next actions"}</h2><p className="mt-3 text-xs leading-relaxed text-[var(--text-muted)]">{vi ? "Catalog và source identity do server xác minh; văn bản reader được trình bày từ HTML an toàn. Filesystem path và secret không được đưa vào UI." : "Catalog and source identity are server-verified; reader text is presented from safe HTML representations. Filesystem paths and secrets are not exposed in the UI."}</p><div className="mt-4 flex flex-wrap gap-2">{onOpenRetrieval && <button type="button" className="workspace-link-button" onClick={onOpenRetrieval}>{vi ? "Mở Retrieval Lab" : "Open Retrieval Lab"}<ArrowRight className="h-3.5 w-3.5" /></button>}{onOpenEvaluation && <button type="button" className="workspace-link-button" onClick={onOpenEvaluation}>{vi ? "Mở Evaluation" : "Open Evaluation"}<ArrowRight className="h-3.5 w-3.5" /></button>}</div></article>
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><h2 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)]"><Info className="h-4 w-4" />{vi ? "Presets" : "Presets"}</h2><div className="mt-3 flex flex-wrap gap-2">{info.retrieval.presets.map((preset) => <span key={preset} className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-1 text-xs font-mono text-[var(--text-muted)]">{preset}</span>)}</div></article>
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><h2 className="text-sm font-bold text-[var(--text-primary)]">{vi ? "Build provenance" : "Build provenance"}</h2><dl className="mt-3 space-y-2 text-xs">{buildEntries.length ? buildEntries.map(([key, value]) => <div key={key} className="flex justify-between gap-3"><dt className="text-[var(--text-muted)]">{key}</dt><dd className="max-w-[70%] truncate font-mono text-[var(--text-primary)]" title={value}>{value}</dd></div>) : <div className="text-[var(--text-muted)]">{vi ? "Không có build label." : "No build labels provided."}</div>}</dl></article>
        </div>
      </>}
    </section>
  );
}
