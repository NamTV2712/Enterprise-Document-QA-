import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { EvidenceItem, createEvidenceCollection, getEvidenceStorageStatus, listEvidenceCollections, updateEvidenceNote } from "../lib/evidenceCollections";
import { useLocale } from "../lib/i18n";

interface EvidenceCollectionsPanelProps {
  onOpenEvidence?: (item: EvidenceItem) => void;
}

export function EvidenceCollectionsPanel({ onOpenEvidence }: EvidenceCollectionsPanelProps) {
  const { locale } = useLocale();
  const [collections, setCollections] = useState(listEvidenceCollections);
  const [storageStatus, setStorageStatus] = useState(getEvidenceStorageStatus);
  const [collectionName, setCollectionName] = useState("");
  const [openCollectionId, setOpenCollectionId] = useState<string | null>(null);
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

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

  const totalItems = collections.reduce((total, collection) => total + collection.items.length, 0);
  return (
    <section className="library-collections" aria-label={locale === "vi" ? "Bộ sưu tập evidence" : "Evidence collections"}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">{locale === "vi" ? "Bộ sưu tập evidence" : "Evidence collections"}</span>
        <span className="text-[10px] text-[var(--text-subtle)]">{totalItems} {locale === "vi" ? "mục" : "items"}</span>
      </div>
      <div className="mt-2 flex gap-2">
        <input value={collectionName} onChange={(event) => setCollectionName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") handleCreate(); }} placeholder={locale === "vi" ? "Tên bộ sưu tập mới" : "New collection name"} aria-label={locale === "vi" ? "Tên bộ sưu tập mới" : "New collection name"} className="min-w-0 flex-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] px-2 py-1.5 text-xs text-[var(--text-primary)]" />
        <button type="button" onClick={handleCreate} aria-label={locale === "vi" ? "Tạo bộ sưu tập" : "Create collection"} className="icon-button"><Plus className="h-4 w-4" /></button>
      </div>
      {storageStatus.readOnly && storageStatus.reason && <p className="library-backup-status" role="status">{storageStatus.reason}</p>}
      {error && <p className="library-backup-status" role="alert">{error}</p>}
      {collections.length > 0 && <div className="mt-2 flex flex-wrap gap-1.5">{collections.map((collection) => (
        <button type="button" key={collection.id} className={`library-collection-chip ${openCollectionId === collection.id ? "is-selected" : ""}`} aria-pressed={openCollectionId === collection.id} onClick={() => setOpenCollectionId((current) => current === collection.id ? null : collection.id)}>
          {collection.name} · {collection.items.length}
        </button>
      ))}</div>}
      {openCollectionId && (() => {
        const collection = collections.find((item) => item.id === openCollectionId);
        if (!collection) return null;
        return (
          <div className="library-evidence-items" aria-label={`${collection.name} evidence`}>
            <p className="library-evidence-items__heading">{locale === "vi" ? "Evidence đã lưu" : "Saved evidence"}</p>
            {collection.items.length === 0 ? <p className="library-evidence-items__empty">{locale === "vi" ? "Chưa có evidence." : "No evidence saved yet."}</p> : collection.items.map((item) => (
              <div key={item.id} className="library-evidence-item">
                <button type="button" className="library-evidence-item__open" onClick={() => onOpenEvidence?.(item)} disabled={!onOpenEvidence}>
                  <span className="library-evidence-item__citation">{item.citation}</span>
                  <span className="library-evidence-item__excerpt">{item.excerpt.replace(/\s+/g, " ").slice(0, 180)}</span>
                  <span className="library-evidence-item__meta">{item.ticker ?? ""}{item.section ? ` · ${item.section}` : ""}</span>
                </button>
                <details className="library-evidence-item__note">
                  <summary>{item.note ? (locale === "vi" ? "Sửa ghi chú" : "Edit note") : (locale === "vi" ? "Thêm ghi chú" : "Add note")}</summary>
                  <textarea
                    value={noteDrafts[item.id] ?? item.note ?? ""}
                    onChange={(event) => setNoteDrafts((current) => ({ ...current, [item.id]: event.target.value.slice(0, 10_000) }))}
                    maxLength={10_000}
                    rows={2}
                    aria-label={locale === "vi" ? `Ghi chú evidence ${item.citation}` : `Note for evidence ${item.citation}`}
                    placeholder={locale === "vi" ? "Ghi chú cho snapshot này…" : "Add a note to this saved snapshot…"}
                  />
                  <button type="button" onClick={() => handleNoteSave(collection.id, item, noteDrafts[item.id] ?? item.note ?? "")}>{locale === "vi" ? "Lưu ghi chú" : "Save note"}</button>
                </details>
              </div>
            ))}
          </div>
        );
      })()}
    </section>
  );
}
