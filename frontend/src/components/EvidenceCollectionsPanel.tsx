import { ExternalLink, FolderOpen, Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  EvidenceItem,
  createEvidenceCollection,
  getEvidenceStorageStatus,
  listEvidenceCollections,
  updateEvidenceNote,
} from "../lib/evidenceCollections";
import { formatCompanyLabel, SECTION_METADATA } from "../lib/displayMetadata";
import { normalizeLocaleSearch, useLocale } from "../lib/i18n";

export type CurrentSourceCheckResult = {
  status: "current" | "stale" | "missing" | "unavailable" | "unknown";
  message?: string;
};

interface EvidenceCollectionsPanelProps {
  searchQuery?: string;
  onOpenEvidence?: (item: EvidenceItem) => void;
  onOpenCurrentSource?: (item: EvidenceItem) => Promise<CurrentSourceCheckResult>;
}

function normalizeExcerpt(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function evidenceMatchesSearch(item: EvidenceItem, query: string): boolean {
  if (!query) return true;
  return normalizeLocaleSearch([
    item.citation,
    item.excerpt,
    item.ticker,
    item.section,
    item.filingDate,
    item.reportDate,
    item.accessionNumber,
    item.documentId,
    item.chunkId,
  ].filter(Boolean).join(" ")).includes(query);
}

function stateLabel(item: EvidenceItem, locale: "en" | "vi", currentState?: CurrentSourceCheckResult["status"]): string {
  const state = currentState ?? item.snapshotState;
  if (state === "current") return locale === "vi" ? "Corpus hiện tại · exact" : "Current corpus · exact";
  if (state === "stale") return locale === "vi" ? "Bản chụp cũ · vẫn đọc được" : "Stale snapshot · still readable";
  if (state === "missing") return locale === "vi" ? "Không còn trong corpus · bản chụp vẫn giữ" : "Missing from corpus · snapshot retained";
  if (state === "unavailable") return locale === "vi" ? "Chưa kiểm tra được corpus" : "Current corpus unavailable";
  if (state === "unknown") return locale === "vi" ? "Chưa xác định trạng thái hiện tại" : "Current state unknown";
  return locale === "vi" ? "Bản chụp đã lưu" : "Saved snapshot";
}

function provenanceRows(item: EvidenceItem, locale: "en" | "vi"): Array<{ label: string; value: string }> {
  const rows: Array<{ label: string; value: string }> = [];
  const add = (label: string, value: string | undefined) => {
    if (value) rows.push({ label, value });
  };
  add(locale === "vi" ? "Ngày nộp" : "Filing date", item.filingDate);
  add(locale === "vi" ? "Ngày báo cáo" : "Report date", item.reportDate);
  add("Accession", item.accessionNumber);
  add(locale === "vi" ? "Document ID" : "Document ID", item.documentId);
  add(locale === "vi" ? "Source document" : "Source document", item.sourceDocumentId);
  add("Chunk ID", item.chunkId);
  add(locale === "vi" ? "Biểu diễn" : "Representation", item.representation);
  add(locale === "vi" ? "Revision document" : "Document revision", item.documentRevision);
  add(locale === "vi" ? "Revision source set" : "Source-set revision", item.sourceSetRevision);
  add(locale === "vi" ? "Độ phủ" : "Coverage", item.coverageStatus);
  add(locale === "vi" ? "Vị trí" : "Location", item.locationStatus);
  add(locale === "vi" ? "Lý do vị trí" : "Location reason", item.locationReason);
  add(locale === "vi" ? "Cuộc trò chuyện nguồn" : "Origin conversation", item.sourceConversationId);
  add(locale === "vi" ? "Tin nhắn nguồn" : "Origin message", item.sourceMessageId);
  add(locale === "vi" ? "Hash văn bản" : "Chunk text hash", item.chunkTextHash);
  add(locale === "vi" ? "Trạng thái snapshot" : "Snapshot state", item.snapshotState);
  if (item.savedAt) add(locale === "vi" ? "Thời điểm lưu" : "Captured", new Date(item.savedAt).toLocaleString(locale === "vi" ? "vi-VN" : "en-US"));
  add(locale === "vi" ? "Source URL" : "Source URL", item.sourceUrl);
  add(locale === "vi" ? "SEC index URL" : "SEC index URL", item.secIndexUrl);
  return rows;
}

export function EvidenceCollectionsPanel({ searchQuery = "", onOpenEvidence, onOpenCurrentSource }: EvidenceCollectionsPanelProps) {
  const { locale } = useLocale();
  const [collections, setCollections] = useState(listEvidenceCollections);
  const [storageStatus, setStorageStatus] = useState(getEvidenceStorageStatus);
  const [collectionName, setCollectionName] = useState("");
  const [openCollectionId, setOpenCollectionId] = useState<string | null>(null);
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [currentStates, setCurrentStates] = useState<Record<string, CurrentSourceCheckResult>>({});
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const normalizedSearch = normalizeLocaleSearch(searchQuery);

  const refresh = () => {
    setCollections(listEvidenceCollections());
    setStorageStatus(getEvidenceStorageStatus());
  };

  useEffect(() => {
    window.addEventListener("sec-qa-evidence-updated", refresh);
    refresh();
    return () => window.removeEventListener("sec-qa-evidence-updated", refresh);
  }, []);

  const handleCreate = () => {
    if (!collectionName.trim()) return;
    try {
      createEvidenceCollection(collectionName);
      setCollectionName("");
      setError(null);
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : (locale === "vi" ? "Không thể tạo bộ sưu tập." : "Could not create collection."));
      setStorageStatus(getEvidenceStorageStatus());
    }
  };

  const handleNoteSave = (collectionId: string, item: EvidenceItem, note: string) => {
    try {
      updateEvidenceNote(collectionId, item.id, note);
      setError(null);
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : (locale === "vi" ? "Không thể lưu ghi chú evidence." : "Could not save the evidence note."));
      setStorageStatus(getEvidenceStorageStatus());
    }
  };

  const handleOpenCurrent = async (item: EvidenceItem) => {
    if (!onOpenCurrentSource || !item.chunkId) return;
    setCheckingId(item.id);
    setError(null);
    try {
      const result = await onOpenCurrentSource(item);
      setCurrentStates((current) => ({ ...current, [item.id]: result }));
      if (result.message) setError(result.message);
    } catch (reason) {
      const result: CurrentSourceCheckResult = { status: "unavailable", message: reason instanceof Error ? reason.message : undefined };
      setCurrentStates((current) => ({ ...current, [item.id]: result }));
      setError(result.message ?? (locale === "vi" ? "Không thể kiểm tra corpus hiện tại." : "Could not check the current corpus."));
    } finally {
      setCheckingId(null);
    }
  };

  const totalItems = collections.reduce((total, collection) => total + collection.items.length, 0);
  const filteredCollections = useMemo(() => collections.map((collection) => ({
    collection,
    items: collection.items.filter((item) => evidenceMatchesSearch(item, normalizedSearch)),
  })), [collections, normalizedSearch]);
  const hasAnyCollections = collections.length > 0;
  const hasAnyFilteredItems = filteredCollections.some(({ items }) => items.length > 0);

  return (
    <section className="library-section library-collections" aria-labelledby="library-evidence-heading">
      <div className="library-section__heading">
        <div>
          <p className="library-section__eyebrow"><FolderOpen className="h-3.5 w-3.5" />{locale === "vi" ? "Bằng chứng lịch sử" : "Historical evidence"}</p>
          <h3 id="library-evidence-heading">{locale === "vi" ? "Bộ sưu tập evidence" : "Evidence Collections"}</h3>
          <p>{locale === "vi" ? "Bản chụp cục bộ giữ nguyên nguồn tại thời điểm lưu; không tự thay bằng corpus mới." : "Local snapshots preserve the source at save time; they are never silently replaced by a newer corpus."}</p>
        </div>
        <span className="library-section__count">{totalItems} {locale === "vi" ? "mục" : "items"}</span>
      </div>
      <div className="library-collection-create">
        <input value={collectionName} onChange={(event) => setCollectionName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") handleCreate(); }} placeholder={locale === "vi" ? "Tên bộ sưu tập mới" : "New collection name"} aria-label={locale === "vi" ? "Tên bộ sưu tập mới" : "New collection name"} />
        <button type="button" onClick={handleCreate} aria-label={locale === "vi" ? "Tạo bộ sưu tập" : "Create collection"} disabled={storageStatus.readOnly}><Plus className="h-4 w-4" />{locale === "vi" ? "Tạo" : "Create"}</button>
      </div>
      {storageStatus.readOnly && storageStatus.reason && <p className="library-backup-status" role="status">{storageStatus.reason}</p>}
      {error && <p className="library-backup-status" role="alert">{error}</p>}
      {!hasAnyCollections ? (
        <div className="library-empty library-empty--compact">
          <FolderOpen className="h-7 w-7" aria-hidden="true" />
          <p><strong>{locale === "vi" ? "Chưa có bộ sưu tập evidence." : "No evidence collections yet."}</strong><span>{locale === "vi" ? "Lưu evidence từ câu trả lời hoặc Retrieval Lab để tạo snapshot đầu tiên." : "Save evidence from an answer or Retrieval Lab to create your first historical snapshot."}</span></p>
        </div>
      ) : (
        <>
          <div className="library-collection-chips" role="list" aria-label={locale === "vi" ? "Các bộ sưu tập evidence" : "Evidence collections"}>
            {collections.map((collection) => <div role="listitem" key={collection.id}><button type="button" className={`library-collection-chip ${openCollectionId === collection.id ? "is-selected" : ""}`} aria-pressed={openCollectionId === collection.id} onClick={() => setOpenCollectionId((current) => current === collection.id ? null : collection.id)}>{collection.name} · {collection.items.length}</button></div>)}
          </div>
          {normalizedSearch && !hasAnyFilteredItems && <div className="library-empty library-empty--compact"><SearchIconPlaceholder /><p><strong>{locale === "vi" ? "Không có evidence phù hợp." : "No evidence matches this filter."}</strong><span>{locale === "vi" ? "Xóa tìm kiếm để xem lại các snapshot đã lưu." : "Clear the search to see saved snapshots again."}</span></p></div>}
          {openCollectionId && (() => {
            const entry = filteredCollections.find(({ collection }) => collection.id === openCollectionId);
            if (!entry) return null;
            const { collection, items } = entry;
            return (
              <div className="library-evidence-items" aria-label={`${collection.name} evidence`}>
                <p className="library-evidence-items__heading">{locale === "vi" ? "Evidence đã lưu · bản chụp tại thời điểm lưu" : "Saved evidence · snapshot at capture time"}</p>
                 {items.length === 0 ? <p className="library-evidence-items__empty">{normalizedSearch ? (locale === "vi" ? "Không có mục phù hợp trong bộ sưu tập này." : "No items in this collection match the filter.") : (locale === "vi" ? "Chưa có evidence." : "No evidence saved yet.")}</p> : items.map((item) => {
                   const currentState = currentStates[item.id]?.status;
                   const sourceAvailable = Boolean(onOpenCurrentSource && item.chunkId);
                   const details = provenanceRows(item, locale);
                   return (
                    <div key={item.id} className="library-evidence-item">
                      <button type="button" className="library-evidence-item__open" onClick={() => onOpenEvidence?.(item)} disabled={!onOpenEvidence}>
                        <span className="library-evidence-item__citation">{item.citation}</span>
                        <span className="library-evidence-item__excerpt">{normalizeExcerpt(item.excerpt).slice(0, 220)}</span>
                        <span className="library-evidence-item__meta">{item.ticker ? formatCompanyLabel(item.ticker) : (locale === "vi" ? "Công ty chưa xác minh" : "Company not verified")}{item.section ? ` · ${SECTION_METADATA[item.section]?.shortLabel ?? item.section}` : ""}{item.filingDate ? ` · ${item.filingDate}` : ""}</span>
                        <span className="library-evidence-item__meta">{locale === "vi" ? "Đã lưu trên thiết bị · Bản chụp lịch sử" : "Saved on this device · Historical snapshot"} · {stateLabel(item, locale, currentState)}</span>
                      </button>
                      {details.length > 0 && (
                        <details className="library-evidence-item__provenance">
                          <summary>{locale === "vi" ? "Chi tiết provenance" : "Provenance details"}</summary>
                          <dl className="library-evidence-item__details-grid">
                            {details.map(({ label, value }) => <div className="library-evidence-item__details-row" key={`${label}-${value}`}><dt>{label}</dt><dd>{value}</dd></div>)}
                          </dl>
                        </details>
                      )}
                      <div className="library-evidence-item__actions">
                        {sourceAvailable && <button type="button" className="library-evidence-action" onClick={() => void handleOpenCurrent(item)} disabled={checkingId === item.id} aria-label={locale === "vi" ? "Mở nguồn hiện tại exact" : "Open exact current source"}>{checkingId === item.id ? (locale === "vi" ? "Đang kiểm tra…" : "Checking…") : <><ExternalLink className="h-3.5 w-3.5" />{locale === "vi" ? "Mở corpus hiện tại" : "Open current source"}</>}</button>}
                        <span className="library-evidence-action__hint">{sourceAvailable ? (locale === "vi" ? "Chỉ mở khi chunk ID và hash exact khớp." : "Opens only when exact chunk identity and hash match.") : (locale === "vi" ? "Không có định danh exact để mở corpus hiện tại." : "No exact identity is available for a current-source handoff.")}</span>
                      </div>
                      <details className="library-evidence-item__note">
                        <summary>{item.note ? (locale === "vi" ? "Sửa ghi chú" : "Edit note") : (locale === "vi" ? "Thêm ghi chú" : "Add note")}</summary>
                        <textarea value={noteDrafts[item.id] ?? item.note ?? ""} onChange={(event) => setNoteDrafts((current) => ({ ...current, [item.id]: event.target.value.slice(0, 10_000) }))} maxLength={10_000} rows={2} aria-label={locale === "vi" ? `Ghi chú evidence ${item.citation}` : `Note for evidence ${item.citation}`} placeholder={locale === "vi" ? "Ghi chú cho snapshot này…" : "Add a note to this saved snapshot…"} />
                        <button type="button" onClick={() => handleNoteSave(collection.id, item, noteDrafts[item.id] ?? item.note ?? "")}>{locale === "vi" ? "Lưu ghi chú" : "Save note"}</button>
                      </details>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </>
      )}
    </section>
  );
}

function SearchIconPlaceholder() {
  return <span className="library-empty__icon" aria-hidden="true">⌕</span>;
}
