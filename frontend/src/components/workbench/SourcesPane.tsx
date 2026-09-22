import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  FileText,
  Search,
} from "lucide-react";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import type { Source } from "../../types";
import {
  listEvidenceCollections,
  saveEvidence,
  snapshotProvenanceFromSource,
} from "../../lib/evidenceCollections";
import { normalizeLocaleSearch, useLocale } from "../../lib/i18n";
import { getSectionDisplay } from "../../lib/sourcePresentation";
import { getSourceKey } from "../../lib/sourceIdentity";
import type { SourceFilter } from "../../lib/workbench";
import {
  useOptionalWorkbenchContext,
} from "./WorkbenchContext";
import {
  SourceCard,
  type SourceCardOrigin,
} from "./SourceCard";

export interface SourcesPaneProps {
  sources: Source[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  unavailable?: boolean;
  unavailableReason?: string;
  messageId?: string;
  conversationId?: string;
  origin?: SourceCardOrigin;
  presentation?: "pane" | "disclosure";
  /** Optional source indexes that are known to be cited by the answer. */
  citedIndexes?: readonly number[];
  focusSourceIndex?: number | null;
  onFocusHandled?: () => void;
  onOpenDocument?: (source: Source, index: number) => void;
  onSaveSource?: (source: Source, index: number) => void | Promise<void>;
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
  className?: string;
}

interface SavedEvidenceMatch {
  citation: string;
  excerpt: string;
  chunkId?: string;
}

function sourceMatchesSavedEvidence(source: Source, item: SavedEvidenceMatch): boolean {
  const excerpt = source.text || source.text_preview;
  if (source.citation !== item.citation || excerpt !== item.excerpt) return false;
  return !source.chunk_id || !item.chunkId || source.chunk_id === item.chunkId;
}

function readSavedSourceKeys(sources: Source[]): Set<string> {
  const savedItems = listEvidenceCollections().flatMap((collection) => collection.items);
  return new Set(
    sources
      .filter((source) =>
        Boolean(source.stored_snapshot) ||
        savedItems.some((item) => sourceMatchesSavedEvidence(source, {
          citation: item.citation,
          excerpt: item.excerpt,
          chunkId: item.chunkId,
        })),
      )
      .map(getSourceKey),
  );
}

function safeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}

function defaultFilterLabel(filter: SourceFilter, vi: boolean): string {
  if (filter === "all") return vi ? "Tất cả" : "All";
  if (filter === "cited") return vi ? "Được trích" : "Cited";
  return vi ? "Đã lưu" : "Saved";
}

/**
 * First-class source/evidence stack. It owns source-list filtering, focus,
 * and scrolling only. Detail fetches and reader lifecycle remain in the
 * existing ContextPanel/reader owner.
 */
export function SourcesPane({
  sources,
  selectedIndex,
  onSelectIndex,
  unavailable = false,
  unavailableReason,
  messageId,
  conversationId,
  origin = "answer",
  presentation = "pane",
  citedIndexes,
  focusSourceIndex = null,
  onFocusHandled,
  onOpenDocument,
  onSaveSource,
  collapsed: controlledCollapsed,
  onCollapsedChange,
  className,
}: SourcesPaneProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const workbench = useOptionalWorkbenchContext();
  const [standaloneFilter, setStandaloneFilter] = useState<SourceFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [savedSourceKeys, setSavedSourceKeys] = useState<Set<string>>(() => readSavedSourceKeys(sources));
  const [standaloneCollapsed, setStandaloneCollapsed] = useState(presentation === "disclosure");
  const [saveError, setSaveError] = useState<string | null>(null);

  const sourceFilter = origin === "answer"
    ? workbench?.controller.state.sourceFilter ?? standaloneFilter
    : "all";
  const setSourceFilter = workbench?.controller.setSourceFilter ?? setStandaloneFilter;
  const collapsed = controlledCollapsed
    ?? (presentation === "disclosure" ? standaloneCollapsed : workbench?.preferences.sourcesCollapsed ?? standaloneCollapsed);
  const setCollapsed = onCollapsedChange
    ?? (presentation === "disclosure" ? setStandaloneCollapsed : workbench?.preferences.setSourcesCollapsed)
    ?? setStandaloneCollapsed;
  const paneId = "sources-pane-" + safeId(messageId || "workspace");
  const headingId = paneId + "-title";
  const sourceElementPrefix = presentation === "disclosure" && messageId
    ? safeId(messageId)
    : paneId;
  const sourceListLabel = vi ? "Danh sách nguồn bằng chứng" : "Source evidence list";

  const refreshSavedSources = useCallback(() => {
    try {
      setSavedSourceKeys(readSavedSourceKeys(sources));
    } catch {
      // Malformed/read-only collection state is handled by the existing
      // evidence persistence owner; the source list remains usable.
      setSavedSourceKeys(new Set());
    }
  }, [sources]);

  useEffect(() => {
    refreshSavedSources();
    const onEvidenceUpdated = () => refreshSavedSources();
    window.addEventListener("sec-qa-evidence-updated", onEvidenceUpdated);
    window.addEventListener("storage", onEvidenceUpdated);
    return () => {
      window.removeEventListener("sec-qa-evidence-updated", onEvidenceUpdated);
      window.removeEventListener("storage", onEvidenceUpdated);
    };
  }, [refreshSavedSources]);

  const savedIndexes = useMemo(
    () => new Set(sources.map((source, index) => savedSourceKeys.has(getSourceKey(source)) ? index : -1).filter((index) => index >= 0)),
    [savedSourceKeys, sources],
  );
  const isCited = useCallback((index: number) => {
    if (citedIndexes) return citedIndexes.includes(index);
    return origin === "answer";
  }, [citedIndexes, origin]);
  const visibleIndexes = useMemo(() => {
    const needle = normalizeLocaleSearch(searchQuery.trim());
    return sources
      .map((source, index) => ({ source, index }))
      .filter(({ source, index }) => {
        const matchesCategory = sourceFilter === "all"
          || (sourceFilter === "cited" && isCited(index))
          || (sourceFilter === "saved" && savedIndexes.has(index));
        if (!matchesCategory) return false;
        if (!needle) return true;
        return normalizeLocaleSearch([
          source.citation,
          source.text || source.text_preview,
          source.section || "",
          source.filing_type || "",
          source.filing_date || "",
        ].join(" ")).includes(needle);
      })
      .map(({ index }) => index);
  }, [isCited, savedIndexes, searchQuery, sourceFilter, sources]);

  const sections = useMemo(() => {
    const seen = new Set<string>();
    return sources.reduce<string[]>((result, source) => {
      const label = getSectionDisplay(source.citation, source.section).section;
      if (!seen.has(label)) {
        seen.add(label);
        result.push(label);
      }
      return result;
    }, []);
  }, [sources]);

  const filterOptions = useMemo(() => {
    if (origin !== "answer") return [] as SourceFilter[];
    const options: SourceFilter[] = ["all", "cited"];
    if (savedIndexes.size > 0) options.push("saved");
    return options;
  }, [origin, savedIndexes.size]);

  useEffect(() => {
    if (sourceFilter === "saved" && savedIndexes.size === 0) setSourceFilter("all");
  }, [savedIndexes.size, setSourceFilter, sourceFilter]);

  useEffect(() => {
    if (focusSourceIndex === null || focusSourceIndex < 0 || focusSourceIndex >= sources.length) return;
    if (!visibleIndexes.includes(focusSourceIndex)) {
      setSearchQuery("");
      if (origin === "answer" && sourceFilter !== "all") setSourceFilter("all");
      return;
    }
    setCollapsed(false);
    const frame = window.requestAnimationFrame(() => {
      const target = document.getElementById(sourceElementPrefix + "-source-" + focusSourceIndex);
      target?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      target?.focus({ preventScroll: true });
      onFocusHandled?.();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [
    focusSourceIndex,
    onFocusHandled,
    origin,
    paneId,
    sourceElementPrefix,
    setCollapsed,
    setSourceFilter,
    sourceFilter,
    sources.length,
    visibleIndexes,
  ]);

  const handleSelect = (index: number) => {
    onSelectIndex(index);
  };

  const handleListKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (visibleIndexes.length === 0) return;
    const currentPosition = Math.max(0, visibleIndexes.indexOf(selectedIndex));
    let nextPosition: number | null = null;
    if (event.key === "ArrowDown" || event.key === "ArrowRight") {
      nextPosition = Math.min(visibleIndexes.length - 1, currentPosition + 1);
    } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
      nextPosition = Math.max(0, currentPosition - 1);
    } else if (event.key === "Home") {
      nextPosition = 0;
    } else if (event.key === "End") {
      nextPosition = visibleIndexes.length - 1;
    } else if (event.key === "Enter") {
      onSelectIndex(visibleIndexes[currentPosition]);
      return;
    }
    if (nextPosition === null) return;
    event.preventDefault();
    onSelectIndex(visibleIndexes[nextPosition]);
  };

  const handleSave = useCallback(async (source: Source, index: number) => {
    setSaveError(null);
    try {
      if (onSaveSource) {
        await onSaveSource(source, index);
      } else {
        saveEvidence(source, {
          conversationId,
          messageId,
          provenance: snapshotProvenanceFromSource(source),
        });
      }
      setSavedSourceKeys((current) => new Set(current).add(getSourceKey(source)));
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : (vi ? "Không thể lưu evidence." : "Could not save evidence.");
      setSaveError(message);
      throw reason;
    }
  }, [conversationId, messageId, onSaveSource, vi]);

  const panelClassName = [
    "sources-pane",
    "context-sources",
    presentation === "disclosure" ? "sources-pane--disclosure" : "",
    collapsed ? "is-collapsed" : "",
    className || "",
  ].filter(Boolean).join(" ");

  return (
    <section
      className={panelClassName}
      data-workbench-region="sources"
      data-source-origin={origin}
      data-sources-collapsed={collapsed ? "true" : "false"}
      aria-labelledby={headingId}
    >
      <header className="sources-pane__header context-panel-heading">
        {presentation === "disclosure" ? (
          <button
            type="button"
            className="sources-toggle sources-pane__disclosure-toggle"
            aria-expanded={!collapsed}
            aria-controls={paneId + "-body"}
            aria-label={(collapsed ? (vi ? "Hiện " : "Show ") : (vi ? "Ẩn " : "Hide ")) + sources.length + (vi ? " đoạn evidence được truy xuất" : " retrieved filing evidence excerpts")}
            onClick={() => setCollapsed(!collapsed)}
          >
            <span className="sources-pane__disclosure-title">
              <FileText className="h-4 w-4" aria-hidden="true" />
              <span>
                <span id={headingId} className="sources-pane__disclosure-heading">
                  {vi ? "Bằng chứng filing được truy xuất" : "Retrieved filing evidence"} · {sources.length} {vi ? "đoạn trích" : "excerpts"}
                </span>
                <span className="sources-pane__disclosure-description">
                  {collapsed
                    ? (vi ? "Mở nội dung nguồn và chi tiết xếp hạng" : "Open source text and ranking details")
                    : (vi ? "Ẩn nội dung nguồn" : "Hide source text")}
                </span>
              </span>
            </span>
            <span className="sources-pane__disclosure-action">
              {collapsed ? (vi ? "Xem" : "View") : (vi ? "Ẩn" : "Hide")}
              {collapsed ? <ChevronDown className="h-4 w-4" aria-hidden="true" /> : <ChevronUp className="h-4 w-4" aria-hidden="true" />}
            </span>
          </button>
        ) : (
          <>
            <div className="sources-pane__title-group min-w-0">
              <div className="flex items-center gap-2">
                <h2 id={headingId} className="text-sm font-semibold text-[var(--text-primary)]">
                  {vi ? "Nguồn truy xuất" : "Retrieved sources"}
                </h2>
                <span
                  className="px-1.5 py-0.5 rounded text-xs font-mono font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/25"
                  aria-label={sources.length + " " + (vi ? "nguồn được truy xuất" : "retrieved sources")}
                >
                  {sources.length}
                </span>
              </div>
              <p className="context-panel-heading__description sr-only">
                {vi
                  ? "Các đoạn được giữ theo thứ tự citation. Điểm là chi tiết xếp hạng nâng cao."
                  : "Excerpts stay in citation order. Scores are advanced ranking details."}
              </p>
            </div>
            <div className="sources-pane__header-actions flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                className="sources-pane__collapse sr-only"
                aria-expanded={!collapsed}
                aria-controls={paneId + "-body"}
                aria-label={collapsed ? (vi ? "Mở rộng bảng nguồn" : "Expand sources pane") : (vi ? "Thu gọn bảng nguồn" : "Collapse sources pane")}
                onClick={() => setCollapsed(!collapsed)}
              >
                {collapsed ? <ChevronDown className="h-4 w-4" aria-hidden="true" /> : <ChevronUp className="h-4 w-4" aria-hidden="true" />}
              </button>
            </div>
          </>
        )}
      </header>

      {!collapsed && (
        <div id={paneId + "-body"} className="sources-pane__body">
          <div className="sources-pane__controls">
            {filterOptions.length > 0 && (
              <div className="sources-pane__filters" role="group" aria-label={vi ? "Bộ lọc nguồn" : "Source filters"}>
                {filterOptions.map((filter) => (
                  <button
                    type="button"
                    key={filter}
                    className={"sources-pane__filter" + (sourceFilter === filter ? " is-selected" : "")}
                    aria-pressed={sourceFilter === filter}
                    onClick={() => setSourceFilter(filter)}
                  >
                    {defaultFilterLabel(filter, vi)}
                    {filter === "saved" && <span aria-hidden="true"> · {savedIndexes.size}</span>}
                  </button>
                ))}
              </div>
            )}

            <label className="context-indexed-search sources-pane__search" data-composite-field>
              <Search className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">{vi ? "Tìm trong nguồn" : "Search sources"}</span>
              <input
                data-composite-input
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder={vi ? "Lọc citation và excerpt…" : "Filter citations and excerpts…"}
                aria-label={vi ? "Tìm trong nguồn" : "Search sources"}
              />
            </label>

            {sections.length > 1 && (
              <nav className="context-section-nav sources-pane__sections" aria-label={vi ? "Mục nguồn" : "Source sections"}>
                {sections.map((section) => (
                  <button
                    type="button"
                    key={section}
                    onClick={() => {
                      const index = sources.findIndex((source) => getSectionDisplay(source.citation, source.section).section === section);
                      if (index >= 0) handleSelect(index);
                    }}
                  >
                    {section}
                  </button>
                ))}
              </nav>
            )}
          </div>

          {unavailable && (
            <div className="context-unavailable sources-pane__unavailable" role="status">
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
              {unavailableReason || (vi ? "Nguồn đã chọn không còn khả dụng trong phiên bản này." : "The selected source is unavailable in this answer variant.")}
            </div>
          )}
          {saveError && (
            <div className="sources-pane__save-error" role="alert">
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
              <span>{saveError}</span>
            </div>
          )}

          <div
            className="context-source-list sources-pane__list"
            role="list"
            aria-label={sourceListLabel}
            tabIndex={0}
            onKeyDown={handleListKeyDown}
          >
            {visibleIndexes.map((index) => {
              const source = sources[index];
              const cardUnavailable = unavailable && selectedIndex === index;
              return (
                <div role="listitem" key={getSourceKey(source) + "-" + index}>
                  <SourceCard
                    source={source}
                    index={index}
                    selected={index === selectedIndex}
                    citationLinked={origin === "answer" && isCited(index)}
                    saved={savedIndexes.has(index)}
                    unavailable={cardUnavailable}
                    unavailableReason={cardUnavailable ? unavailableReason : undefined}
                    onSelect={() => handleSelect(index)}
                    onOpenDocument={onOpenDocument ? () => onOpenDocument(source, index) : () => handleSelect(index)}
                    onSave={() => handleSave(source, index)}
                    sourceElementId={sourceElementPrefix + "-source-" + index}
                    idPrefix={paneId}
                  />
                </div>
              );
            })}
            {visibleIndexes.length === 0 && (
              <p className="evidence-rail-empty sources-pane__empty">
                {sourceFilter === "saved"
                  ? (vi ? "Chưa có evidence được lưu trong danh sách này." : "No saved evidence is present in this list.")
                  : (vi ? "Không có evidence phù hợp." : "No matching evidence.")}
              </p>
            )}
          </div>

        </div>
      )}
    </section>
  );
}

export default SourcesPane;
