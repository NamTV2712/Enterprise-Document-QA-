import React, { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, Download, FlaskConical, GitCompare, Search, ShieldCheck } from "lucide-react";
import { inspectRetrieval } from "../lib/api";
import { RetrievalPreset, RetrievalTrace } from "../types";
import { useLocale } from "../lib/i18n";

interface RetrievalLabPanelProps {
  tickers: string[];
  sections: string[];
  selectedTicker: string | null;
  selectedSection: string | null;
  isBackendConnected: boolean | null;
  onUseQuestion: (question: string) => void;
}

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
}: RetrievalLabPanelProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
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

  useEffect(() => {
    if (selectedTicker) setTicker(selectedTicker);
  }, [selectedTicker]);

  useEffect(() => {
    if (selectedSection) setSection(selectedSection);
  }, [selectedSection]);

  const presetLabel = useMemo(
    () => PRESETS.find((item) => item.value === preset)?.[vi ? "vi" : "label"] ?? preset,
    [preset, vi],
  );

  const runInspection = async () => {
    if (question.trim().length < 5 || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await inspectRetrieval({
        question: question.trim(),
        ticker: ticker || null,
        section: section || null,
        top_k: topK,
        candidate_pool: Math.max(candidatePool, topK),
        preset,
      });
      setTrace(response.trace);
      setComparisonTrace(null);
      setInterpretation(response.query_interpretation.retrieval_question);
      if (compareEnabled && comparePreset !== preset) {
        const comparison = await inspectRetrieval({
          question: question.trim(), ticker: ticker || null, section: section || null,
          top_k: topK, candidate_pool: Math.max(candidatePool, topK), preset: comparePreset,
        });
        setComparisonTrace(comparison.trace);
      }
    } catch (inspectionError) {
      setError(inspectionError instanceof Error ? inspectionError.message : "Retrieval inspection failed.");
      setTrace(null);
    } finally {
      setIsLoading(false);
    }
  };

  const downloadTrace = (format: "json" | "csv") => {
    if (!trace) return;
    const traces = comparisonTrace ? [trace, comparisonTrace] : [trace];
    const content = format === "json"
      ? JSON.stringify({ query: question, traces }, null, 2)
      : ["preset,chunk_id,final_rank,selected,bm25_score,dense_score,rrf_score,cross_encoder_score", ...traces.flatMap((item) => item.candidates.map((candidate) => [item.preset, candidate.chunk_id, candidate.final_rank ?? "", candidate.selected, candidate.bm25_score ?? "", candidate.dense_score ?? "", candidate.rrf_score ?? "", candidate.cross_encoder_score ?? ""].join(",")))].join("\n");
    const url = URL.createObjectURL(new Blob([content], { type: format === "json" ? "application/json" : "text/csv" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `retrieval-trace.${format}`; anchor.click(); URL.revokeObjectURL(url);
  };

  return (
    <section className="mx-auto w-full max-w-6xl space-y-5 px-3 py-5 md:px-6" aria-labelledby="retrieval-lab-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-semibold text-cyan-700 dark:text-cyan-300">
            <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
            {vi ? "Chế độ nghiên cứu retrieval" : "Retrieval research mode"}
          </div>
          <h1 id="retrieval-lab-title" className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            {vi ? "Retrieval Lab" : "Retrieval Lab"}
          </h1>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[var(--text-muted)]">
            {vi
              ? "Chạy tìm kiếm cục bộ và xem BM25, dense, RRF cùng reranker. Trang này không gọi LLM."
              : "Run local retrieval and inspect BM25, dense search, RRF, and reranking. This page does not call an LLM."}
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-3 py-2 text-xs text-[var(--text-muted)]">
          <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />
          {isBackendConnected === false
            ? vi ? "Backend offline" : "Backend offline"
            : vi ? "Provider-free" : "Provider-free"}
        </div>
      </div>

      <div className="grid gap-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4 shadow-sm md:grid-cols-[minmax(0,1fr)_220px]">
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
            onClick={() => onUseQuestion(question)}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-[var(--border-strong)] px-4 py-2 text-sm font-semibold text-[var(--text-primary)] hover:surface-muted-hover"
          >
            {vi ? "Đưa sang Research" : "Use in Research"}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="grid gap-3 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className="space-y-1 text-xs font-semibold text-[var(--text-muted)]">
          <span>{vi ? "Preset" : "Preset"}</span>
          <select value={preset} onChange={(event) => setPreset(event.target.value as RetrievalPreset)} className="control-select w-full">
            {PRESETS.map((item) => <option key={item.value} value={item.value}>{vi ? item.vi : item.label}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-xs font-semibold text-[var(--text-muted)]">
          <span>{vi ? "Công ty" : "Company"}</span>
          <select value={ticker} onChange={(event) => setTicker(event.target.value)} className="control-select w-full">
            <option value="">{vi ? "Tất cả" : "All"}</option>
            {tickers.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-xs font-semibold text-[var(--text-muted)]">
          <span>{vi ? "Mục" : "Section"}</span>
          <select value={section} onChange={(event) => setSection(event.target.value)} className="control-select w-full">
            <option value="">{vi ? "Tất cả" : "All"}</option>
            {sections.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-xs font-semibold text-[var(--text-muted)]">
          <span>Top K</span>
          <select value={topK} onChange={(event) => setTopK(Number(event.target.value))} className="control-select w-full">
            {[3, 5, 10].map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-xs font-semibold text-[var(--text-muted)]">
          <span>{vi ? "Candidate pool" : "Candidate pool"}</span>
          <select value={candidatePool} onChange={(event) => setCandidatePool(Number(event.target.value))} className="control-select w-full">
          {[10, 20, 50].map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        </label>
        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--text-muted)] sm:col-span-2 lg:col-span-1">
          <input type="checkbox" checked={compareEnabled} onChange={(event) => setCompareEnabled(event.target.checked)} />
          <span>{vi ? "So sánh preset" : "Compare preset"}</span>
        </label>
        {compareEnabled && <label className="space-y-1 text-xs font-semibold text-[var(--text-muted)]">
          <span>{vi ? "Preset thứ hai" : "Second preset"}</span>
          <select value={comparePreset} onChange={(event) => setComparePreset(event.target.value as RetrievalPreset)} className="control-select w-full">
            {PRESETS.map((item) => <option key={item.value} value={item.value}>{vi ? item.vi : item.label}</option>)}
          </select>
        </label>}
      </div>

      {error && <div className="rounded-xl border border-rose-300/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-700 dark:text-rose-300" role="alert">{error}</div>}
      {interpretation && (
        <div className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-3 text-sm text-[var(--text-primary)]">
          <span className="font-semibold">{vi ? "Câu dùng để retrieval:" : "Retrieval query:"}</span> <code className="font-mono">{interpretation}</code>
        </div>
      )}

      {trace ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {trace.stages.map((stage) => (
              <div key={stage.name} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-3">
                <div className="text-xs font-semibold text-[var(--text-muted)]">{stage.name}</div>
                <div className="mt-1 text-lg font-bold text-[var(--text-primary)]">{stage.skipped ? "—" : `${stage.elapsed_ms.toFixed(1)} ms`}</div>
              </div>
            ))}
          </div>
          <div className="overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-raised)]">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]"><Activity className="h-4 w-4 text-cyan-600 dark:text-cyan-300" />{presetLabel}</div>
              <div className="flex flex-wrap items-center gap-2"><span className="text-xs text-[var(--text-muted)]">{trace.candidates.length} candidates · {trace.elapsed_ms.toFixed(1)} ms</span><button type="button" onClick={() => downloadTrace("json")} className="inline-flex items-center gap-1 rounded border border-[var(--border-subtle)] px-2 py-1 text-[10px] font-semibold text-[var(--text-primary)]"><Download className="h-3 w-3" />JSON</button><button type="button" onClick={() => downloadTrace("csv")} className="inline-flex items-center gap-1 rounded border border-[var(--border-subtle)] px-2 py-1 text-[10px] font-semibold text-[var(--text-primary)]"><Download className="h-3 w-3" />CSV</button></div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-[900px] w-full text-left text-xs">
                <thead className="bg-[var(--surface-muted)] text-[var(--text-muted)]">
                  <tr>{["Final", "Source", "BM25", "Dense", "RRF", "Reranker", "Preview"].map((heading) => <th key={heading} className="px-3 py-2 font-semibold">{heading}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {trace.candidates.map((candidate) => (
                    <tr key={candidate.chunk_id} className={candidate.selected ? "bg-cyan-500/10" : ""}>
                      <td className="px-3 py-3 font-bold text-[var(--text-primary)]">{candidate.final_rank ?? "—"}</td>
                      <td className="px-3 py-3"><div className="font-semibold text-[var(--text-primary)]">{candidate.chunk_id}</div><div className="text-[var(--text-muted)]">{candidate.citation}</div></td>
                      <td className="px-3 py-3 font-mono">{score(candidate.bm25_score)} <span className="text-[var(--text-muted)]">#{candidate.bm25_rank ?? "—"}</span></td>
                      <td className="px-3 py-3 font-mono">{score(candidate.dense_score)} <span className="text-[var(--text-muted)]">#{candidate.dense_rank ?? "—"}</span></td>
                      <td className="px-3 py-3 font-mono">{score(candidate.rrf_score)}</td>
                      <td className="px-3 py-3 font-mono">{score(candidate.cross_encoder_score)}</td>
                      <td className="max-w-sm px-3 py-3 text-[var(--text-muted)]">{candidate.text_preview}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          {comparisonTrace && <div className="mt-3 rounded-2xl border border-violet-400/30 bg-violet-500/10 p-4"><div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]"><GitCompare className="h-4 w-4 text-violet-600 dark:text-violet-300" />{vi ? `So sánh với ${comparisonTrace.preset}` : `Compared with ${comparisonTrace.preset}`}</div><div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{comparisonTrace.stages.map((stage) => <div key={stage.name} className="rounded-lg bg-[var(--surface-raised)] p-2 text-xs"><div className="text-[var(--text-muted)]">{stage.name}</div><div className="mt-1 font-semibold text-[var(--text-primary)]">{stage.skipped ? "—" : `${stage.elapsed_ms.toFixed(1)} ms`}</div></div>)}</div><p className="mt-3 text-xs text-[var(--text-muted)]">{vi ? "Các trace dùng cùng câu hỏi và filter; score của các stage khác thang đo nên không được so sánh trực tiếp." : "Both traces use the same question and filters; stage scores have different scales and are not directly comparable."}</p></div>}
        </>
      ) : (
        <div className="rounded-2xl border border-dashed border-[var(--border-strong)] px-5 py-12 text-center text-sm text-[var(--text-muted)]">
          {vi ? "Chạy một câu hỏi để xem thứ hạng và điểm của từng stage." : "Run a question to inspect each retrieval stage and rank movement."}
        </div>
      )}
    </section>
  );
}
