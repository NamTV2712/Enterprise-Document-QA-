import { useEffect, useRef, useState } from "react";
import { ArrowRight, FileSearch, Search, ShieldCheck } from "lucide-react";
import { inspectRetrieval } from "../lib/api";
import type { RetrievalCandidate, RetrievalPreset, RetrievalTrace, Source } from "../types";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";
import { getWorkspaceNavItem } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";

interface SearchWorkspaceProps {
  selectedTicker: string | null;
  selectedSection: string | null;
  isBackendConnected: boolean | null;
  onUseQuestion: (question: string, scope?: { ticker: string | null; section: string | null }) => void;
  onOpenSource?: (source: Source) => void;
}

interface SubmittedScope {
  ticker: string | null;
  section: string | null;
}

const DEFAULT_QUERY = "What are Apple's main business risks?";
const WORKSPACE_META = getWorkspaceNavItem("search");

function score(candidate: RetrievalCandidate, preset: RetrievalPreset): string {
  const value = preset === "bm25"
    ? candidate.bm25_score
    : preset === "dense"
      ? candidate.dense_score
      : preset === "hybrid"
        ? candidate.rrf_score
        : candidate.cross_encoder_score;
  return typeof value === "number" ? value.toFixed(3) : "—";
}

export function SearchWorkspace({ selectedTicker, selectedSection, isBackendConnected, onUseQuestion, onOpenSource }: SearchWorkspaceProps) {
  const { locale, t } = useLocale();
  const vi = locale === "vi";
  const ToolIcon = getSemanticIcon(WORKSPACE_META.icon);
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [trace, setTrace] = useState<RetrievalTrace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [submittedScope, setSubmittedScope] = useState<SubmittedScope | null>(null);
  const requestSequenceRef = useRef(0);
  const requestControllerRef = useRef<AbortController | null>(null);
  const scopeKey = `${selectedTicker ?? ""}\u001f${selectedSection ?? ""}`;
  const currentScopeKeyRef = useRef(scopeKey);
  currentScopeKeyRef.current = scopeKey;

  useEffect(() => {
    requestSequenceRef.current += 1;
    requestControllerRef.current?.abort();
    requestControllerRef.current = null;
    setTrace(null);
    setSubmittedScope(null);
    setError(null);
    setIsLoading(false);
  }, [scopeKey]);

  useEffect(() => () => {
    requestSequenceRef.current += 1;
    requestControllerRef.current?.abort();
    requestControllerRef.current = null;
  }, []);

  const runSearch = async () => {
    const question = query.trim();
    if (question.length < 5 || isLoading || isBackendConnected === false) return;
    const requestId = ++requestSequenceRef.current;
    requestControllerRef.current?.abort();
    const controller = new AbortController();
    requestControllerRef.current = controller;
    const requestScope: SubmittedScope = { ticker: selectedTicker, section: selectedSection };
    const requestScopeKey = `${requestScope.ticker ?? ""}\u001f${requestScope.section ?? ""}`;
    const preservePreviousTrace = Boolean(trace && submittedScope &&
      submittedScope.ticker === requestScope.ticker && submittedScope.section === requestScope.section);
    setIsLoading(true);
    setError(null);
    setSubmittedScope(requestScope);
    if (!preservePreviousTrace) setTrace(null);
    try {
      const response = await inspectRetrieval({
        question,
        ticker: selectedTicker,
        section: selectedSection,
        top_k: 8,
        candidate_pool: 24,
        preset: "hybrid_rerank" as RetrievalPreset,
      }, controller.signal);
      if (requestId !== requestSequenceRef.current || currentScopeKeyRef.current !== requestScopeKey) return;
      setTrace(response.trace);
    } catch (reason) {
      if (requestId !== requestSequenceRef.current || currentScopeKeyRef.current !== requestScopeKey) return;
      if (!preservePreviousTrace) setTrace(null);
      setError(describeRequestError(reason, vi ? "Không thể tìm kiếm." : "Search failed.", vi ? "vi" : "en").message);
    } finally {
      if (requestId === requestSequenceRef.current && currentScopeKeyRef.current === requestScopeKey) {
        setIsLoading(false);
        if (requestControllerRef.current === controller) requestControllerRef.current = null;
      }
    }
  };

  const submittedScopeLabel = submittedScope
    ? `${submittedScope.ticker ?? (vi ? "Tất cả công ty" : "All companies")} · ${submittedScope.section ?? (vi ? "Tất cả mục" : "All sections")}`
    : null;

  return (
    <section className="workspace-page" aria-labelledby="search-workspace-title">
      <div className="workspace-page__intro">
        <div>
          <div className="workspace-eyebrow"><ToolIcon className="h-3.5 w-3.5" />{t(WORKSPACE_META.labelKey)}</div>
          <h1 id="search-workspace-title">{vi ? "Tìm kiếm trong filing" : "Search the filing corpus"}</h1>
          <p>{t(WORKSPACE_META.descriptionKey)}</p>
        </div>
        <div className="workspace-status-chip"><ShieldCheck className="h-4 w-4" />{vi ? "Không gọi LLM" : "No LLM call"}</div>
      </div>

      <div className="workspace-search-bar" data-composite-field>
        <Search className="h-5 w-5" aria-hidden="true" />
        <input data-composite-input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runSearch(); }} placeholder={vi ? "Tìm trong các đoạn filing…" : "Search filing excerpts…"} aria-label={vi ? "Câu hỏi tìm kiếm" : "Search question"} />
        <button type="button" onClick={() => void runSearch()} disabled={isLoading || query.trim().length < 5 || isBackendConnected === false} className="primary-action-button" aria-label={vi ? "Chạy tìm kiếm" : "Run search"}>
          {isLoading ? <span className="workspace-spinner" aria-hidden="true" /> : <Search className="h-4 w-4" />}
          <span className="hidden sm:inline">{isLoading ? (vi ? "Đang tìm…" : "Searching…") : (vi ? "Tìm" : "Search")}</span>
        </button>
      </div>

      <div className="workspace-filter-line">
        <span>{vi ? "Phạm vi" : "Scope"}</span>
        <span className="workspace-token">{selectedTicker ?? (vi ? "Tất cả công ty" : "All companies")}</span>
        <span className="workspace-token">{selectedSection ?? (vi ? "Tất cả mục" : "All sections")}</span>
        <button type="button" onClick={() => onUseQuestion(query, { ticker: selectedTicker, section: selectedSection })} className="workspace-link-button">{vi ? "Dùng trong Research" : "Use in Research"}<ArrowRight className="h-3.5 w-3.5" /></button>
      </div>

      {error && <div className="workspace-alert workspace-alert--error" role="alert">{error}</div>}
      {trace && isLoading && (
        <div className="workspace-alert" role="status" aria-live="polite">
          {vi
            ? "Đang làm mới kết quả cho cùng phạm vi. Đang hiển thị kết quả trước đó cho đến khi có phản hồi mới."
            : "Refreshing results for the submitted scope. Showing the previous results until the new response arrives."}
        </div>
      )}
      {trace ? (
        <div className="search-results-panel" aria-busy={isLoading}>
          <div className="search-results-panel__header"><div><span className="workspace-eyebrow">{vi ? "Kết quả" : "Results"}</span><h2>{trace.candidate_count ?? trace.candidates.length} {vi ? "đoạn đã kiểm tra" : "inspected excerpts"}</h2></div><span className="workspace-result-meta">{trace.preset} · {trace.elapsed_ms.toFixed(0)} ms</span></div>
          {submittedScopeLabel && <p className="workspace-result-meta">{vi ? "Phạm vi đã gửi" : "Submitted scope"}: {submittedScopeLabel}</p>}
          {([true, false] as const).map((selectedGroup) => {
            const items = trace.candidates.filter((candidate) => candidate.selected === selectedGroup);
            if (items.length === 0) return null;
            return <section key={String(selectedGroup)} className="search-result-group" aria-labelledby={`search-result-group-${selectedGroup ? "selected" : "other"}`}>
              <h3 id={`search-result-group-${selectedGroup ? "selected" : "other"}`}>{selectedGroup ? (vi ? "Kết quả được chọn" : "Selected results") : (vi ? "Ứng viên khác đã kiểm tra" : "Other inspected candidates")} <span>({items.length})</span></h3>
              <div className="search-result-list">
                {items.map((candidate) => (
                  <article key={candidate.chunk_id} className={`search-result ${candidate.selected ? "is-selected" : ""}`}>
                    <div className="search-result__rank">{candidate.final_rank ?? "—"}</div>
                    <div className="min-w-0"><div className="search-result__title"><span>{candidate.citation}</span><span className="search-result__score">{selectedGroup ? `${vi ? "Điểm cuối" : "Final score"}: ${score(candidate, trace.preset)}` : (vi ? "Không có hạng cuối" : "No final rank")}</span></div><p>{candidate.text_preview}</p><div className="search-result__meta"><span>{candidate.ticker ?? "SEC"}</span><span>{candidate.section ?? (vi ? "Không rõ mục" : "Unknown section")}</span><span>{vi ? "Hạng fusion" : "Fusion rank"}: {candidate.fusion_rank ?? "—"}</span><code>{candidate.chunk_id}</code></div><details><summary>{vi ? "Điểm các giai đoạn" : "Stage scores"}</summary><div className="search-result__meta"><span>BM25 {candidate.bm25_score ?? "—"} ({candidate.bm25_rank ?? "—"})</span><span>Dense {candidate.dense_score ?? "—"} ({candidate.dense_rank ?? "—"})</span><span>RRF {candidate.rrf_score ?? "—"}</span><span>Reranker {candidate.cross_encoder_score ?? "—"}</span></div></details><div className="flex flex-wrap items-center gap-3">{onOpenSource && <button type="button" className="search-result__open" onClick={() => onOpenSource({ citation: candidate.citation, text_preview: candidate.text_preview, chunk_id: candidate.chunk_id, document_id: candidate.document_id, ticker: candidate.ticker, section: candidate.section, filing_date: candidate.filing_date, score: score(candidate, trace.preset) === "—" ? null : Number(score(candidate, trace.preset)), score_kind: trace.preset === "hybrid_rerank" ? "cross_encoder" : trace.preset === "hybrid" ? "rrf" : "retrieval" })}>{vi ? "Mở đoạn indexed" : "Open indexed excerpt"}</button>}{onOpenSource && candidate.document_id && <button type="button" className="search-result__open" onClick={() => onOpenSource({ citation: candidate.citation, text_preview: "", document_id: candidate.document_id, ticker: candidate.ticker, section: candidate.section, filing_date: candidate.filing_date })}>{vi ? "Mở không gian tài liệu" : "Open document workspace"}</button>}</div></div>
                  </article>
                ))}
              </div>
            </section>;
          })}
        </div>
      ) : (
        <div className="workspace-empty-state"><FileSearch className="h-8 w-8" /><h2>{vi ? "Tìm evidence trước" : "Find evidence first"}</h2><p>{isBackendConnected === false ? (vi ? "Backend đang offline. Retrieval sẽ khả dụng sau khi kết nối lại." : "The backend is offline. Retrieval will be available after reconnecting.") : (vi ? "Nhập câu hỏi để xem các đoạn filing phù hợp và điểm xếp hạng." : "Enter a question to see matching filing excerpts and rank scores.")}</p></div>
      )}
    </section>
  );
}
