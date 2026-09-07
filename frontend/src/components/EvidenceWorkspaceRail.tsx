import { FileText, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Source } from "../types";
import { formatCompanyLabel } from "../lib/displayMetadata";
import { useLocale } from "../lib/i18n";
import { getSectionDisplay } from "./SourcesPanel";

interface EvidenceWorkspaceRailProps {
  sources: Source[];
}

/** Persistent, read-only evidence rail for the three-pane research layout. */
export function EvidenceWorkspaceRail({ sources }: EvidenceWorkspaceRailProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [filter, setFilter] = useState("");
  const visibleSources = useMemo(() => {
    const needle = filter.trim().toLocaleLowerCase();
    if (!needle) return sources.map((source, index) => ({ source, index }));
    return sources
      .map((source, index) => ({ source, index }))
      .filter(({ source }) =>
        `${source.citation} ${source.text || source.text_preview}`.toLocaleLowerCase().includes(needle),
      );
  }, [filter, sources]);
  const selected = sources[selectedIndex] ?? sources[0];
  const selectedMeta = selected ? getSectionDisplay(selected.citation, selected.section) : null;

  return (
    <aside className="evidence-workspace-rail" aria-label={vi ? "Nguồn và evidence" : "Sources and evidence"}>
      <div className="evidence-rail-heading">
        <div>
          <p className="evidence-rail-eyebrow">{vi ? "Evidence" : "Evidence"}</p>
          <h2>{vi ? "Nguồn truy xuất" : "Retrieved sources"}</h2>
        </div>
        <span className="evidence-rail-count">{sources.length}</span>
      </div>
      <label className="evidence-rail-search">
        <Search className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="sr-only">{vi ? "Tìm trong nguồn" : "Search sources"}</span>
        <input
          type="search"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder={vi ? "Lọc evidence…" : "Filter evidence…"}
          aria-label={vi ? "Tìm trong nguồn" : "Search sources"}
        />
      </label>
      <div className="evidence-rail-list">
        {visibleSources.map(({ source, index }) => {
          const meta = getSectionDisplay(source.citation, source.section);
          return (
            <button
              type="button"
              key={`${source.chunk_id ?? source.citation}-${index}`}
              className={`evidence-rail-source ${index === selectedIndex ? "is-selected" : ""}`}
              onClick={() => setSelectedIndex(index)}
              aria-pressed={index === selectedIndex}
            >
              <span className="evidence-rail-rank">{index + 1}</span>
              <span className="min-w-0 text-left">
                <span className="evidence-rail-source-title">{source.ticker ? formatCompanyLabel(source.ticker) : meta.ticker} · {source.citation}</span>
                <span className="evidence-rail-score">{typeof source.score === "number" ? source.score.toFixed(3) : source.score}</span>
                <span className="evidence-rail-source-preview">{source.text_preview}</span>
              </span>
            </button>
          );
        })}
        {visibleSources.length === 0 && <p className="evidence-rail-empty">{vi ? "Không có evidence phù hợp." : "No matching evidence."}</p>}
      </div>
      {selected && selectedMeta && (
        <section className="evidence-reader" aria-labelledby="evidence-reader-title">
          <div className="evidence-reader-header">
            <FileText className="h-4 w-4" aria-hidden="true" />
            <div className="min-w-0">
              <p className="evidence-rail-eyebrow">{vi ? "Reader" : "Reader"}</p>
              <h3 id="evidence-reader-title">{selectedMeta.section}</h3>
            </div>
          </div>
          <p className="evidence-reader-citation">{selected.citation}</p>
          <p className="evidence-reader-text">{selected.text || selected.text_preview}</p>
          <div className="evidence-reader-meta">
            <span>{selected.ticker ? formatCompanyLabel(selected.ticker) : selectedMeta.ticker}</span>
            {selected.filing_date && <span>{selected.filing_date}</span>}
            <span>{vi ? "Điểm" : "Score"} {typeof selected.score === "number" ? selected.score.toFixed(3) : selected.score}</span>
          </div>
        </section>
      )}
    </aside>
  );
}
