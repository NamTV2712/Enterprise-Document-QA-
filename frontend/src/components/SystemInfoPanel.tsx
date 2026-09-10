import { useEffect, useState } from "react";
import { CheckCircle2, Cpu, Database, Info } from "lucide-react";
import { getSystemInfo } from "../lib/api";
import { SystemInfoResponse } from "../types";
import { useLocale } from "../lib/i18n";
import { getWorkspaceNavItem } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";

const WORKSPACE_META = getWorkspaceNavItem("system");

export function SystemInfoPanel() {
  const { locale, t } = useLocale();
  const vi = locale === "vi";
  const ToolIcon = getSemanticIcon(WORKSPACE_META.icon);
  const [info, setInfo] = useState<SystemInfoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getSystemInfo(controller.signal).then(setInfo).catch((reason) => {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "Could not load system information.");
    });
    return () => controller.abort();
  }, []);

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
        <div className="grid gap-4 md:grid-cols-3">
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)]"><Database className="h-4 w-4 text-cyan-600 dark:text-cyan-300" />{vi ? "Corpus" : "Corpus"}</div><div className="mt-3 text-2xl font-bold text-[var(--text-primary)]">{String(corpus.searchable_company_count ?? "—")}</div><div className="text-xs text-[var(--text-muted)]">{vi ? "công ty searchable" : "searchable companies"}</div><div className="mt-3 text-sm text-[var(--text-muted)]">{String(corpus.indexed_chunk_count ?? "—")} {vi ? "chunks" : "indexed chunks"}</div></article>
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)]"><Cpu className="h-4 w-4 text-violet-600 dark:text-violet-300" />{vi ? "Retrieval models" : "Retrieval models"}</div><div className="mt-3 break-all text-sm font-semibold text-[var(--text-primary)]">{info.retrieval.embedding_model ?? "—"}</div><div className="mt-2 break-all text-xs text-[var(--text-muted)]">{info.retrieval.reranker_model ?? "—"}</div></article>
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><div className="flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)]"><CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-300" />{vi ? "Contract" : "Contract"}</div><div className="mt-3 text-sm font-semibold text-[var(--text-primary)]">{vi ? "Provider-free tools" : "Provider-free tools"}</div><div className="mt-2 text-xs leading-relaxed text-[var(--text-muted)]">{vi ? "Retrieval Lab và Document Explorer chỉ đọc metadata đã nạp; không gửi câu hỏi tới LLM." : "Retrieval Lab and Document Explorer read loaded metadata only; they do not send questions to an LLM."}</div></article>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><h2 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)]"><Info className="h-4 w-4" />{vi ? "Presets" : "Presets"}</h2><div className="mt-3 flex flex-wrap gap-2">{info.retrieval.presets.map((preset) => <span key={preset} className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-1 text-xs font-mono text-[var(--text-muted)]">{preset}</span>)}</div></article>
          <article className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4"><h2 className="text-sm font-bold text-[var(--text-primary)]">{vi ? "Build provenance" : "Build provenance"}</h2><dl className="mt-3 space-y-2 text-xs">{buildEntries.length ? buildEntries.map(([key, value]) => <div key={key} className="flex justify-between gap-3"><dt className="text-[var(--text-muted)]">{key}</dt><dd className="max-w-[70%] truncate font-mono text-[var(--text-primary)]" title={value}>{value}</dd></div>) : <div className="text-[var(--text-muted)]">{vi ? "Không có build label." : "No build labels provided."}</div>}</dl></article>
        </div>
      </>}
    </section>
  );
}
