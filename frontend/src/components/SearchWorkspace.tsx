import { useEffect, useState } from "react";
import { ArrowRight, FileSearch, Search, ShieldCheck } from "lucide-react";
import { inspectRetrieval } from "../lib/api";
import type { RetrievalCandidate, RetrievalPreset, RetrievalTrace } from "../types";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";

interface SearchWorkspaceProps {
  selectedTicker: string | null;
  selectedSection: string | null;
  isBackendConnected: boolean | null;
  onUseQuestion: (question: string, scope?: { ticker: string | null; section: string | null }) => void;
}

const DEFAULT_QUERY = "What are Apple's main business risks?";

function score(candidate: RetrievalCandidate): string {
  const value = candidate.cross_encoder_score ?? candidate.rrf_score ?? candidate.dense_score ?? candidate.bm25_score;
  return typeof value === "number" ? value.toFixed(3) : "—";
}

export function SearchWorkspace({ selectedTicker, selectedSection, isBackendConnected, onUseQuestion }: SearchWorkspaceProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [trace, setTrace] = useState<RetrievalTrace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setTrace(null);
  }, [selectedSection, selectedTicker]);

  const runSearch = async () => {
    const question = query.trim();
    if (question.length < 5 || isLoading || isBackendConnected === false) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await inspectRetrieval({
        question,
        ticker: selectedTicker,
        section: selectedSection,
        top_k: 8,
        candidate_pool: 24,
        preset: "hybrid_rerank" as RetrievalPreset,
      });
      setTrace(response.trace);
    } catch (reason) {
      setTrace(null);
      setError(describeRequestError(reason, vi ? "Không thể tìm kiếm." : "Search failed.", vi ? "vi" : "en").message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="workspace-page" aria-labelledby="search-workspace-title">
      <div className="workspace-page__intro">
        <div>
          <div className="workspace-eyebrow"><FileSearch className="h-3.5 w-3.5" />{vi ? "Tìm kiếm evidence" : "Evidence search"}</div>
          <h1 id="search-workspace-title">{vi ? "Tìm kiếm trong filing" : "Search the filing corpus"}</h1>
          <p>{vi ? "Tìm các đoạn nguồn bằng retrieval cục bộ trước khi mở một câu hỏi nghiên cứu đầy đủ." : "Find source excerpts with local retrieval before opening a full research question."}</p>
        </div>
        <div className="workspace-status-chip"><ShieldCheck className="h-4 w-4" />{vi ? "Không gọi LLM" : "No LLM call"}</div>
      </div>

      <div className="workspace-search-bar">
        <Search className="h-5 w-5" aria-hidden="true" />
        <input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void runSearch(); }} placeholder={vi ? "Tìm trong các đoạn filing…" : "Search filing excerpts…"} aria-label={vi ? "Câu hỏi tìm kiếm" : "Search question"} />
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
      {trace ? (
        <div className="search-results-panel">
          <div className="search-results-panel__header"><div><span className="workspace-eyebrow">{vi ? "Kết quả" : "Results"}</span><h2>{trace.candidates.length} {vi ? "đoạn ứng viên" : "candidate excerpts"}</h2></div><span className="workspace-result-meta">{trace.preset} · {trace.elapsed_ms.toFixed(0)} ms</span></div>
          <div className="search-result-list">
            {trace.candidates.map((candidate, index) => (
              <article key={candidate.chunk_id} className={`search-result ${candidate.selected ? "is-selected" : ""}`}>
                <div className="search-result__rank">{candidate.final_rank ?? index + 1}</div>
                <div className="min-w-0"><div className="search-result__title"><span>{candidate.citation}</span><span className="search-result__score">{score(candidate)}</span></div><p>{candidate.text_preview}</p><div className="search-result__meta"><span>{candidate.ticker ?? "SEC"}</span><span>{candidate.section ?? (vi ? "Không rõ mục" : "Unknown section")}</span><code>{candidate.chunk_id}</code></div></div>
              </article>
            ))}
          </div>
        </div>
      ) : (
        <div className="workspace-empty-state"><FileSearch className="h-8 w-8" /><h2>{vi ? "Tìm evidence trước" : "Find evidence first"}</h2><p>{isBackendConnected === false ? (vi ? "Backend đang offline. Retrieval sẽ khả dụng sau khi kết nối lại." : "The backend is offline. Retrieval will be available after reconnecting.") : (vi ? "Nhập câu hỏi để xem các đoạn filing phù hợp và điểm xếp hạng." : "Enter a question to see matching filing excerpts and rank scores.")}</p></div>
      )}
    </section>
  );
}
