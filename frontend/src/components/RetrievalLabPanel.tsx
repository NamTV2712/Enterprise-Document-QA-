import React, { useEffect, useMemo, useRef, useState } from "react";
import { Activity, ArrowRight, Download, GitCompare, Search, ShieldAlert, ShieldCheck } from "lucide-react";
import { inspectRetrieval } from "../lib/api";
import { RetrievalPreset, RetrievalTrace, Source } from "../types";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";
import { NumberRangeField } from "./NumberRangeField";
import { SelectField } from "./ui/SelectField";
import { getWorkspaceNavItem } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";

interface RetrievalLabPanelProps {
  tickers: string[];
  sections: string[];
  selectedTicker: string | null;
  selectedSection: string | null;
  isBackendConnected: boolean | null;
  onUseQuestion: (question: string, scope?: { ticker: string | null; section: string | null }) => void;
  onOpenSource?: (source: Source) => void;
  onSaveEvidence?: (source: Source) => void;
}

interface InspectionSnapshot {
  question: string;
  ticker: string | null;
  section: string | null;
  topK: number;
  candidatePool: number;
  preset: RetrievalPreset;
  comparePreset: RetrievalPreset | null;
}

const WORKSPACE_META = getWorkspaceNavItem("retrieval");

const PRESETS: Array<{ value: RetrievalPreset; label: string; vi: string }> = [
  { value: "bm25", label: "BM25", vi: "BM25" },
  { value: "dense", label: "Dense vector", vi: "Vector dense" },
  { value: "hybrid", label: "Hybrid RRF", vi: "Hybrid RRF" },
  { value: "hybrid_rerank", label: "Hybrid + reranker", vi: "Hybrid + reranker" },
];

const DEFAULT_QUESTION = "What was Apple's total revenue in 2024?";

function score(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : value.toFixed(4);
}

export function RetrievalLabPanel({
  tickers,
  sections,
  selectedTicker,
  selectedSection,
  isBackendConnected,
  onUseQuestion,
  onOpenSource,
  onSaveEvidence,
}: RetrievalLabPanelProps) {
  const { locale, t } = useLocale();
  const vi = locale === "vi";
  const ToolIcon = getSemanticIcon(WORKSPACE_META.icon);
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [ticker, setTicker] = useState(selectedTicker ?? "");
  const [section, setSection] = useState(selectedSection ?? "");
  const [preset, setPreset] = useState<RetrievalPreset>("hybrid_rerank");
  const [topK, setTopK] = useState(5);
  const [candidatePool, setCandidatePool] = useState(10);
  const [trace, setTrace] = useState<RetrievalTrace | null>(null);
  const [comparisonTrace, setComparisonTrace] = useState<RetrievalTrace | null>(null);
  const [compareEnabled, setCompareEnabled] = useState(false);
  const [comparePreset, setComparePreset] = useState<RetrievalPreset>("bm25");
  const [interpretation, setInterpretation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [submittedSnapshot, setSubmittedSnapshot] = useState<InspectionSnapshot | null>(null);
  const [isInvalidated, setIsInvalidated] = useState(false);
  const [labMode, setLabMode] = useState<"analyst" | "advanced">("analyst");
  const inspectionAbortRef = useRef<AbortController | null>(null);
  const inspectionRequestId = useRef(0);
  const currentConfigurationKeyRef = useRef("");

  const configurationKey = JSON.stringify({
    question: question.trim(),
    ticker,
    section,
    topK,
    candidatePool,
    preset,
    compareEnabled,
    comparePreset,
  });
  currentConfigurationKeyRef.current = configurationKey;

  useEffect(() => {
    setTicker(selectedTicker ?? "");
  }, [selectedTicker]);

  useEffect(() => {
    setSection(selectedSection ?? "");
  }, [selectedSection]);

  useEffect(() => {
    const hadSubmittedState = Boolean(trace || comparisonTrace || interpretation || submittedSnapshot || isLoading);
    inspectionRequestId.current += 1;
    inspectionAbortRef.current?.abort();
    inspectionAbortRef.current = null;
    setTrace(null);
    setComparisonTrace(null);
    setInterpretation(null);
    setSubmittedSnapshot(null);
    setError(null);
    setIsLoading(false);
    if (hadSubmittedState) setIsInvalidated(true);
  }, [configurationKey]);

  useEffect(() => () => {
    inspectionRequestId.current += 1;
    inspectionAbortRef.current?.abort();
    inspectionAbortRef.current = null;
  }, []);

  const presetLabel = useMemo(
    () => PRESETS.find((item) => item.value === preset)?.[vi ? "vi" : "label"] ?? preset,
    [preset, vi],
  );
  const presetOptions = useMemo(
    () => PRESETS.map((item) => ({ value: item.value, label: vi ? item.vi : item.label })),
    [vi],
  );
  const tickerOptions = useMemo(
    () => [{ value: "", label: vi ? "Tất cả" : "All" }, ...tickers.map((item) => ({ value: item, label: item }))],
    [tickers, vi],
  );
  const sectionOptions = useMemo(
    () => [{ value: "", label: vi ? "Tất cả" : "All" }, ...sections.map((item) => ({ value: item, label: item }))],
    [sections, vi],
  );
  const displayCandidates = useMemo(() => trace ? [...trace.candidates].sort((left, right) => {
    if (left.selected !== right.selected) return left.selected ? -1 : 1;
    return (left.final_rank ?? Number.MAX_SAFE_INTEGER) - (right.final_rank ?? Number.MAX_SAFE_INTEGER) ||
      (left.fusion_rank ?? Number.MAX_SAFE_INTEGER) - (right.fusion_rank ?? Number.MAX_SAFE_INTEGER);
  }) : [], [trace]);
  const comparisonSummary = useMemo(() => {
    if (!trace || !comparisonTrace) return null;
    const selected = new Set(trace.selected_chunk_ids);
    const compared = new Set(comparisonTrace.selected_chunk_ids);
    const overlap = [...selected].filter((chunkId) => compared.has(chunkId));
    const primaryRanks = new Map(trace.candidates.map((candidate) => [candidate.chunk_id, candidate.final_rank]));
    const comparedRanks = new Map(comparisonTrace.candidates.map((candidate) => [candidate.chunk_id, candidate.final_rank]));
    const rankMovements = overlap
      .map((chunkId) => ({ chunkId, movement: (comparedRanks.get(chunkId) ?? 0) - (primaryRanks.get(chunkId) ?? 0) }))
      .filter((item) => item.movement !== 0);
    return {
      overlap: overlap.length,
      primaryOnly: [...selected].filter((chunkId) => !compared.has(chunkId)).length,
      comparisonOnly: [...compared].filter((chunkId) => !selected.has(chunkId)).length,
      rankMovements,
    };
  }, [comparisonTrace, trace]);

  const runInspection = async () => {
    if (question.trim().length < 5 || isLoading) return;
    inspectionAbortRef.current?.abort();
    const controller = new AbortController();
    inspectionAbortRef.current = controller;
    const requestId = ++inspectionRequestId.current;
    const requestSnapshot: InspectionSnapshot = {
      question: question.trim(),
      ticker: ticker || null,
      section: section || null,
      topK,
      candidatePool: Math.max(candidatePool, topK),
      preset,
      comparePreset: compareEnabled && comparePreset !== preset ? comparePreset : null,
    };
    const requestConfigurationKey = configurationKey;
    setIsLoading(true);
    setError(null);
    setIsInvalidated(false);
    setSubmittedSnapshot(requestSnapshot);
    setTrace(null);
    setComparisonTrace(null);
    setInterpretation(null);
    try {
      const response = await inspectRetrieval({
        question: requestSnapshot.question,
        ticker: requestSnapshot.ticker,
        section: requestSnapshot.section,
        top_k: requestSnapshot.topK,
        candidate_pool: requestSnapshot.candidatePool,
        preset: requestSnapshot.preset,
      }, controller.signal);
      if (requestId !== inspectionRequestId.current || currentConfigurationKeyRef.current !== requestConfigurationKey) return;
      setTrace(response.trace);
      setComparisonTrace(null);
      setInterpretation(response.query_interpretation.retrieval_question);
      if (requestSnapshot.comparePreset) {
        const comparison = await inspectRetrieval({
          question: requestSnapshot.question,
          ticker: requestSnapshot.ticker,
          section: requestSnapshot.section,
          top_k: requestSnapshot.topK,
          candidate_pool: requestSnapshot.candidatePool,
          preset: requestSnapshot.comparePreset,
        }, controller.signal);
        if (requestId !== inspectionRequestId.current || currentConfigurationKeyRef.current !== requestConfigurationKey) return;
        setComparisonTrace(comparison.trace);
      }
    } catch (inspectionError) {
      if (requestId !== inspectionRequestId.current || currentConfigurationKeyRef.current !== requestConfigurationKey || (inspectionError instanceof DOMException && inspectionError.name === "AbortError")) return;
      setError(describeRequestError(inspectionError, vi ? "Không thể kiểm tra retrieval." : "Retrieval inspection failed.", vi ? "vi" : "en").message);
      setTrace(null);
      setComparisonTrace(null);
      setInterpretation(null);
    } finally {
      if (requestId === inspectionRequestId.current && currentConfigurationKeyRef.current === requestConfigurationKey) {
        setIsLoading(false);
        if (inspectionAbortRef.current === controller) inspectionAbortRef.current = null;
      }
    }
  };

  const downloadTrace = (format: "json" | "csv") => {
    if (!trace) return;
    const traces = comparisonTrace ? [trace, comparisonTrace] : [trace];
    const escapeCsv = (value: string | number | boolean | null | undefined) => {
      const text = value === null || value === undefined ? "" : String(value);
      return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
    };
    const content = format === "json"
      ? JSON.stringify({
        query: trace.query,
        configuration: {
          ticker: trace.filters.ticker,
          section: trace.filters.section,
          top_k: trace.top_k,
          candidate_pool: trace.candidate_pool,
          preset: trace.preset,
          comparison_preset: comparisonTrace?.preset ?? null,
        },
        traces,
      }, null, 2)
      : ["query,ticker,section,top_k,candidate_pool,preset,chunk_id,final_rank,fusion_rank,selected,bm25_score,dense_score,rrf_score,cross_encoder_score", ...traces.flatMap((item) => item.candidates.map((candidate) => [item.query, item.filters.ticker, item.filters.section, item.top_k, item.candidate_pool, item.preset, candidate.chunk_id, candidate.final_rank ?? "", candidate.fusion_rank ?? "", candidate.selected, candidate.bm25_score ?? "", candidate.dense_score ?? "", candidate.rrf_score ?? "", candidate.cross_encoder_score ?? ""].map(escapeCsv).join(",")))].join("\n");
    const url = URL.createObjectURL(new Blob([content], { type: format === "json" ? "application/json" : "text/csv" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `retrieval-trace.${format}`; anchor.click(); URL.revokeObjectURL(url);
  };

  return (
    <section className="workspace-page workspace-page--wide retrieval-lab space-y-5" aria-labelledby="retrieval-lab-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-semibold text-cyan-700 dark:text-cyan-300">
            <ToolIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {t(WORKSPACE_META.labelKey)}
          </div>
          <h1 id="retrieval-lab-title" className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            {vi ? "Retrieval Lab" : "Retrieval Lab"}
          </h1>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[var(--text-muted)]">
            {t(WORKSPACE_META.descriptionKey)} {vi ? "Không gọi LLM." : "This page does not call an LLM."}
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-3 py-2 text-xs text-[var(--text-muted)]">
          {isBackendConnected === false
            ? <ShieldAlert className="h-4 w-4 text-rose-600 dark:text-rose-300" aria-hidden="true" />
            : <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />}
          {isBackendConnected === false
            ? vi ? "Backend offline" : "Backend offline"
            : vi ? "Provider-free" : "Provider-free"}
        </div>
      </div>

      <div className="retrieval-mode-switcher" role="tablist" aria-label={vi ? "Chế độ Retrieval Lab" : "Retrieval Lab mode"}>
        <button type="button" role="tab" aria-selected={labMode === "analyst"} onClick={() => setLabMode("analyst")} className={labMode === "analyst" ? "is-active" : ""}>{vi ? "Analyst" : "Analyst mode"}</button>
        <button type="button" role="tab" aria-selected={labMode === "advanced"} onClick={() => setLabMode("advanced")} className={labMode === "advanced" ? "is-active" : ""}>{vi ? "Nâng cao" : "Advanced mode"}</button>
        <p>{labMode === "analyst"
          ? (vi ? "Luồng gọn: chạy, đọc nguồn đã chọn hoặc đưa câu hỏi sang Research." : "Focused flow: run, inspect selected evidence, or take the question to Research.")
          : (vi ? "Hiển thị toàn bộ preset, điểm stage, thứ hạng và export của trace đã gửi." : "Shows all presets, stage scores, ranks, and exports for the submitted trace.")}</p>
      </div>

      <div className="grid gap-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4 shadow-sm lg:grid-cols-[minmax(0,1fr)_220px]">
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            {vi ? "Câu hỏi retrieval" : "Retrieval question"}
          </span>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
            className="min-h-24 w-full resize-y rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
            aria-label={vi ? "Câu hỏi retrieval" : "Retrieval question"}
          />
        </label>
        <div className="flex flex-col justify-end gap-2">
          <button
            type="button"
            onClick={() => void runInspection()}
            disabled={isLoading || question.trim().length < 5 || isBackendConnected === false}
            className="primary-action-button inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Search className="h-4 w-4" aria-hidden="true" />
            {isLoading ? (vi ? "Đang chạy…" : "Running…") : (vi ? "Chạy retrieval" : "Run retrieval")}
          </button>
          <button
            type="button"
            onClick={() => onUseQuestion(question, { ticker: ticker || null, section: section || null })}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-[var(--border-strong)] px-4 py-2 text-sm font-semibold text-[var(--text-primary)] hover:surface-muted-hover"
          >
            {vi ? "Đưa sang Research" : "Use in Research"}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="retrieval-settings-grid rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4">
        <div className="retrieval-strategy-field">
          <SelectField label={vi ? "Preset · chiến lược đề xuất" : "Preset"} value={preset} options={presetOptions} onValueChange={(value) => setPreset(value as RetrievalPreset)} />
          <p><strong>{vi ? "Chiến lược đề xuất:" : "Recommended strategy:"}</strong> {vi ? "Hybrid + reranker kết hợp BM25, semantic và reranking theo logic hiện có." : "Hybrid + reranker combines BM25, semantic retrieval, and the existing reranking logic."}</p>
        </div>
        <SelectField label={vi ? "Công ty" : "Company"} value={ticker} options={tickerOptions} onValueChange={setTicker} />
        <SelectField label={vi ? "Mục" : "Section"} value={section} options={sectionOptions} onValueChange={setSection} />
        <NumberRangeField
          id="retrieval-top-k"
          label="Top K"
          value={topK}
          min={1}
          max={10}
          onChange={setTopK}
          hint={vi ? "Kết quả cuối cùng" : "Final results"}
        />
        {labMode === "advanced" && <NumberRangeField
          id="retrieval-candidate-pool"
          label={vi ? "Candidate pool" : "Candidate pool"}
          value={candidatePool}
          min={10}
          max={50}
          step={5}
          onChange={setCandidatePool}
          hint={vi ? "Ứng viên trước khi xếp hạng cuối" : "Candidates before final ranking"}
        />}
        <label className="flex min-h-10 items-center gap-2 text-xs font-semibold text-[var(--text-muted)]">
          <input type="checkbox" checked={compareEnabled} onChange={(event) => setCompareEnabled(event.target.checked)} />
          <span>{vi ? "So sánh preset" : "Compare preset"}</span>
        </label>
        {compareEnabled && <SelectField label={vi ? "Preset thứ hai" : "Second preset"} value={comparePreset} options={presetOptions} onValueChange={(value) => setComparePreset(value as RetrievalPreset)} />}
      </div>

      {error && <div className="rounded-xl border border-rose-300/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-700 dark:text-rose-300" role="alert">{error}</div>}
      {isInvalidated && <div className="rounded-xl border border-amber-300/60 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200" role="status" aria-live="polite">{vi ? "Cấu hình đã thay đổi; hãy chạy lại retrieval để cập nhật trace và export." : "The configuration changed. Run retrieval again to refresh the trace and exports."}</div>}
      {isLoading && <div className="rounded-xl border border-cyan-300/60 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-800 dark:text-cyan-200" role="status" aria-live="polite">{vi ? "Đang chạy retrieval cho cấu hình đã gửi." : "Running retrieval for the submitted configuration."}</div>}
      {interpretation && (
        <div className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-3 text-sm text-[var(--text-primary)]">
          <span className="font-semibold">{vi ? "Câu dùng để retrieval:" : "Retrieval query:"}</span> <code className="font-mono">{interpretation}</code>
        </div>
      )}

      {trace ? (
        <>
          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[var(--text-primary)]" data-testid="submitted-retrieval-configuration">
            <span className="font-semibold">{vi ? "Cấu hình đã gửi:" : "Submitted configuration:"}</span>{" "}
            <code className="font-mono">{trace.query}</code>{" · "}
            <span>{trace.filters.ticker ?? (vi ? "Tất cả công ty" : "All companies")} · {trace.filters.section ?? (vi ? "Tất cả mục" : "All sections")} · top K {trace.top_k} · pool {trace.candidate_pool} · {trace.preset}</span>
          </div>
          {labMode === "analyst" && <div className="retrieval-analyst-summary" data-testid="retrieval-analyst-summary">
            <div><span>{vi ? "Kết quả đã chọn" : "Selected results"}</span><strong>{trace.selected_count ?? trace.selected_chunk_ids.length}</strong></div>
            <div><span>{vi ? "Ứng viên đã kiểm tra" : "Candidates inspected"}</span><strong>{trace.candidate_count ?? trace.candidates.length}</strong></div>
            <div><span>{vi ? "Thời lượng server" : "Server duration"}</span><strong>{trace.elapsed_ms.toFixed(1)} ms</strong></div>
          </div>}
          {labMode === "advanced" && <div className="retrieval-settings-grid">
            {trace.stages.map((stage) => (
              <div key={stage.name} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-3">
                <div className="text-xs font-semibold text-[var(--text-muted)]">{stage.name}</div>
                <div className="mt-1 text-lg font-bold text-[var(--text-primary)]">{stage.skipped ? "—" : `${stage.elapsed_ms.toFixed(1)} ms`}</div>
              </div>
            ))}
          </div>}
          <div className="overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)]">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]"><Activity className="h-4 w-4 text-cyan-600 dark:text-cyan-300" />{presetLabel}</div>
              <div className="flex flex-wrap items-center gap-2"><span className="text-xs text-[var(--text-muted)]">{trace.candidate_count ?? trace.candidates.length} candidates · {trace.selected_count ?? trace.selected_chunk_ids.length} selected · {trace.elapsed_ms.toFixed(1)} ms</span><button type="button" onClick={() => downloadTrace("json")} className="inline-flex items-center gap-1 rounded border border-[var(--border-subtle)] px-2 py-1 text-[10px] font-semibold text-[var(--text-primary)]"><Download className="h-3 w-3" />JSON</button><button type="button" onClick={() => downloadTrace("csv")} className="inline-flex items-center gap-1 rounded border border-[var(--border-subtle)] px-2 py-1 text-[10px] font-semibold text-[var(--text-primary)]"><Download className="h-3 w-3" />CSV</button></div>
            </div>
            <div className="overflow-x-auto">
              <table className={`${labMode === "advanced" ? "min-w-[900px]" : "min-w-[620px]"} w-full text-left text-xs`}>
                <thead className="bg-[var(--surface-muted)] text-[var(--text-muted)]">
                  <tr>{(labMode === "advanced" ? ["Final", "Source", "BM25", "Dense", "RRF", "Reranker", "Preview"] : ["Final", "Source", "Preview"]).map((heading) => <th key={heading} className="px-3 py-2 font-semibold">{heading}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {displayCandidates.map((candidate) => (
                    <tr key={candidate.chunk_id} className={candidate.selected ? "bg-cyan-500/10" : ""}>
                      <td className="px-3 py-3 font-bold text-[var(--text-primary)]">{candidate.final_rank ?? "—"}</td>
                      <td className="px-3 py-3"><div className="font-semibold text-[var(--text-primary)]">{candidate.chunk_id}</div><div className="text-[var(--text-muted)]">{candidate.citation}</div><div className="mt-1 flex flex-wrap gap-2">{onOpenSource && <button type="button" className="text-left text-[11px] font-semibold text-cyan-700 underline dark:text-cyan-300" onClick={() => onOpenSource({ citation: candidate.citation, text_preview: candidate.text_preview, chunk_id: candidate.chunk_id, document_id: candidate.document_id, ticker: candidate.ticker, section: candidate.section, filing_date: candidate.filing_date })}>{vi ? "Mở indexed" : "Open indexed"}</button>}{onOpenSource && candidate.document_id && <button type="button" className="text-left text-[11px] font-semibold text-cyan-700 underline dark:text-cyan-300" onClick={() => onOpenSource({ citation: candidate.citation, text_preview: "", document_id: candidate.document_id, ticker: candidate.ticker, section: candidate.section, filing_date: candidate.filing_date })}>{vi ? "Mở workspace" : "Open document"}</button>}{onSaveEvidence && <button type="button" className="text-left text-[11px] font-semibold text-cyan-700 underline dark:text-cyan-300" onClick={() => onSaveEvidence({ citation: candidate.citation, text_preview: candidate.text_preview, chunk_id: candidate.chunk_id, document_id: candidate.document_id, ticker: candidate.ticker, section: candidate.section, filing_date: candidate.filing_date })}>{vi ? "Lưu evidence" : "Save evidence"}</button>}</div></td>
                      {labMode === "advanced" && <><td className="px-3 py-3 font-mono">{score(candidate.bm25_score)} <span className="text-[var(--text-muted)]">#{candidate.bm25_rank ?? "—"}</span></td>
                      <td className="px-3 py-3 font-mono">{score(candidate.dense_score)} <span className="text-[var(--text-muted)]">#{candidate.dense_rank ?? "—"}</span></td>
                      <td className="px-3 py-3 font-mono">{score(candidate.rrf_score)}</td>
                      <td className="px-3 py-3 font-mono">{score(candidate.cross_encoder_score)}</td></>}
                      <td className="max-w-sm px-3 py-3 text-[var(--text-muted)]">{candidate.text_preview}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          {comparisonTrace && <div className="mt-3 rounded-2xl border border-violet-400/30 bg-violet-500/10 p-4"><div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]"><GitCompare className="h-4 w-4 text-violet-600 dark:text-violet-300" />{vi ? `So sánh với ${comparisonTrace.preset}` : `Compared with ${comparisonTrace.preset}`}</div>{comparisonSummary && <div className="mt-3 grid gap-2 sm:grid-cols-3"><div className="rounded-lg bg-[var(--surface-raised)] p-2 text-xs"><div className="text-[var(--text-muted)]">{vi ? "Nguồn trùng" : "Selected overlap"}</div><div className="mt-1 font-semibold text-[var(--text-primary)]">{comparisonSummary.overlap}</div></div><div className="rounded-lg bg-[var(--surface-raised)] p-2 text-xs"><div className="text-[var(--text-muted)]">{vi ? "Chỉ trace chính" : "Only in primary"}</div><div className="mt-1 font-semibold text-[var(--text-primary)]">{comparisonSummary.primaryOnly}</div></div><div className="rounded-lg bg-[var(--surface-raised)] p-2 text-xs"><div className="text-[var(--text-muted)]">{vi ? "Chỉ trace đối chiếu" : "Only in comparison"}</div><div className="mt-1 font-semibold text-[var(--text-primary)]">{comparisonSummary.comparisonOnly}</div></div></div>}<div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{comparisonTrace.stages.map((stage) => <div key={stage.name} className="rounded-lg bg-[var(--surface-raised)] p-2 text-xs"><div className="text-[var(--text-muted)]">{stage.name}</div><div className="mt-1 font-semibold text-[var(--text-primary)]">{stage.skipped ? "—" : `${stage.elapsed_ms.toFixed(1)} ms`}</div></div>)}</div><p className="mt-3 text-xs text-[var(--text-muted)]">{vi ? "Các trace dùng cùng câu hỏi và filter; score của các stage khác thang đo nên không được so sánh trực tiếp. Thời lượng là diagnostic duration, không phải benchmark production." : "Both traces use the same question and filters; stage scores have different scales. Durations are diagnostic measurements, not production latency benchmarks."}</p></div>}
        </>
      ) : (
        <div className="rounded-2xl border border-dashed border-[var(--border-strong)] px-5 py-12 text-center text-sm text-[var(--text-muted)]">
          {vi ? "Chạy một câu hỏi để xem thứ hạng và điểm của từng stage." : "Run a question to inspect each retrieval stage and rank movement."}
        </div>
      )}
    </section>
  );
}
