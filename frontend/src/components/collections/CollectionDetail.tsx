import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, Clock, FileText, FolderOpen, Info, Loader2, ShieldCheck, StickyNote, X } from "lucide-react";

import {
  addCollectionNote,
  deleteCollection,
  deleteCollectionItem,
  deleteCollectionNote,
  exportCollection,
  listCollectionActivity,
  listCollectionItems,
  listCollectionNotes,
  updateCollection,
  updateCollectionNote,
} from "../../lib/api";
import type {
  CollectionItemKind,
  CollectionItemRecord,
  CollectionNoteRecord,
  CollectionRecord,
  CollectionUpdateRequest,
} from "../../types";
import {
  describeCollectionFailure,
  exportFileName,
  memberCountLabel,
  privacySummary,
  formatRelativeTime,
} from "../../lib/collectionModel";
import type { CollectionFailure } from "../../lib/collectionModel";
import { CollectionActionMenu } from "./CollectionActionMenu";
import { CollectionActivity } from "./CollectionActivity";
import { CollectionContents } from "./CollectionContents";
import { CollectionNotes } from "./CollectionNotes";
import { CollectionSettings } from "./CollectionSettings";

type DetailTab = "contents" | "notes" | "activity" | "settings";

interface CollectionDetailProps {
  vi: boolean;
  collection: CollectionRecord | null;
  loading: boolean;
  failure: CollectionFailure | null;
  now: number;
  onClose: () => void;
  onReload: () => void;
  onChanged: (collection: CollectionRecord) => void;
  onDeleted: (collectionId: string) => void;
  onOpenItem: (item: CollectionItemRecord) => void;
  onAddDocuments: () => void;
  onRename: () => void;
  onExportRequested: (message: string | null) => void;
  returnFocusIdFor: (itemId: string) => string;
}

/**
 * The reference's contextual rail for one collection: its real metadata, its
 * typed members, its notes, its recorded activity and its editable settings.
 *
 * Every write is explicit, carries the revision the page last read, and turns
 * a refusal into the state it actually is (conflict, gone, refused, missing)
 * instead of a generic failure.
 */
export function CollectionDetail({
  vi,
  collection,
  loading,
  failure,
  now,
  onClose,
  onReload,
  onChanged,
  onDeleted,
  onOpenItem,
  onAddDocuments,
  onRename,
  onExportRequested,
  returnFocusIdFor,
}: CollectionDetailProps) {
  const [tab, setTab] = useState<DetailTab>("contents");
  const [kindFilter, setKindFilter] = useState<CollectionItemKind | null>(null);

  const [items, setItems] = useState<CollectionItemRecord[]>([]);
  const [itemsTotal, setItemsTotal] = useState(0);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [itemsFailure, setItemsFailure] = useState<CollectionFailure | null>(null);

  const [notes, setNotes] = useState<CollectionNoteRecord[]>([]);
  const [notesTotal, setNotesTotal] = useState(0);
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesFailure, setNotesFailure] = useState<CollectionFailure | null>(null);
  const [noteDraft, setNoteDraft] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [pendingNoteId, setPendingNoteId] = useState<string | null>(null);

  const [events, setEvents] = useState<Awaited<ReturnType<typeof listCollectionActivity>>["items"]>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsFailure, setEventsFailure] = useState<CollectionFailure | null>(null);

  const [pendingItemId, setPendingItemId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [writeFailure, setWriteFailure] = useState<CollectionFailure | null>(null);
  const [writeNotice, setWriteNotice] = useState<string | null>(null);

  const collectionId = collection?.collection_id ?? null;
  const revision = collection?.revision ?? null;

  // One guard per resource: a response for an older selection or an older
  // revision can never paint over the current one.
  const itemsEpoch = useRef(0);
  const notesEpoch = useRef(0);
  const eventsEpoch = useRef(0);
  const itemsController = useRef<AbortController | null>(null);
  const notesController = useRef<AbortController | null>(null);
  const eventsController = useRef<AbortController | null>(null);

  const loadItems = useCallback(async () => {
    if (!collectionId) return;
    const epoch = ++itemsEpoch.current;
    itemsController.current?.abort();
    const controller = new AbortController();
    itemsController.current = controller;
    setItemsLoading(true);
    setItemsFailure(null);
    try {
      const response = await listCollectionItems(
        collectionId,
        { kind: kindFilter ?? undefined, page: 1, page_size: 100 },
        controller.signal,
      );
      if (itemsEpoch.current !== epoch) return;
      setItems(response.items);
      setItemsTotal(response.total);
    } catch (error) {
      if (itemsEpoch.current !== epoch) return;
      if ((error as { name?: string })?.name === "AbortError") return;
      setItems([]);
      setItemsTotal(0);
      setItemsFailure(describeCollectionFailure(error, vi));
    } finally {
      if (itemsEpoch.current === epoch) setItemsLoading(false);
    }
  }, [collectionId, kindFilter, vi]);

  const loadNotes = useCallback(async () => {
    if (!collectionId) return;
    const epoch = ++notesEpoch.current;
    notesController.current?.abort();
    const controller = new AbortController();
    notesController.current = controller;
    setNotesLoading(true);
    setNotesFailure(null);
    try {
      const response = await listCollectionNotes(collectionId, { page: 1, page_size: 100 }, controller.signal);
      if (notesEpoch.current !== epoch) return;
      setNotes(response.items);
      setNotesTotal(response.total);
    } catch (error) {
      if (notesEpoch.current !== epoch) return;
      if ((error as { name?: string })?.name === "AbortError") return;
      setNotes([]);
      setNotesTotal(0);
      setNotesFailure(describeCollectionFailure(error, vi));
    } finally {
      if (notesEpoch.current === epoch) setNotesLoading(false);
    }
  }, [collectionId, vi]);

  const loadActivity = useCallback(async () => {
    if (!collectionId) return;
    const epoch = ++eventsEpoch.current;
    eventsController.current?.abort();
    const controller = new AbortController();
    eventsController.current = controller;
    setEventsLoading(true);
    setEventsFailure(null);
    try {
      const response = await listCollectionActivity(collectionId, { page: 1, page_size: 100 }, controller.signal);
      if (eventsEpoch.current !== epoch) return;
      setEvents(response.items);
      setEventsTotal(response.total);
    } catch (error) {
      if (eventsEpoch.current !== epoch) return;
      if ((error as { name?: string })?.name === "AbortError") return;
      setEvents([]);
      setEventsTotal(0);
      setEventsFailure(describeCollectionFailure(error, vi));
    } finally {
      if (eventsEpoch.current === epoch) setEventsLoading(false);
    }
  }, [collectionId, vi]);

  // A new collection or a committed revision invalidates every tab's data.
  useEffect(() => {
    setTab("contents");
    setKindFilter(null);
    setWriteFailure(null);
    setWriteNotice(null);
    setNoteDraft("");
    setEditingNoteId(null);
  }, [collectionId]);

  useEffect(() => {
    // Data is read per tab, so a reading tab is never fetched needlessly.
    if (!collectionId) return;
    if (tab === "contents") void loadItems();
    if (tab === "notes") void loadNotes();
    if (tab === "activity") void loadActivity();
  }, [collectionId, revision, tab, loadItems, loadNotes, loadActivity]);

  useEffect(
    () => () => {
      itemsController.current?.abort();
      notesController.current?.abort();
      eventsController.current?.abort();
    },
    [],
  );

  const handleRemoveItem = useCallback(
    async (item: CollectionItemRecord) => {
      if (!collectionId) return;
      setPendingItemId(item.item_id);
      setWriteFailure(null);
      try {
        await deleteCollectionItem(collectionId, item.item_id, item.revision);
        setWriteNotice(vi ? "Đã xoá mục khỏi bộ sưu tập." : "Removed the member from the collection.");
        await loadItems();
        onReload();
      } catch (error) {
        setWriteFailure(describeCollectionFailure(error, vi));
      } finally {
        setPendingItemId(null);
      }
    },
    [collectionId, loadItems, onReload, vi],
  );

  const handleAddNote = useCallback(async () => {
    if (!collectionId || noteDraft.trim().length === 0) return;
    setNoteSaving(true);
    setWriteFailure(null);
    try {
      await addCollectionNote(collectionId, { text: noteDraft });
      setNoteDraft("");
      setWriteNotice(vi ? "Đã lưu ghi chú." : "Note saved.");
      await loadNotes();
      onReload();
    } catch (error) {
      setWriteFailure(describeCollectionFailure(error, vi));
    } finally {
      setNoteSaving(false);
    }
  }, [collectionId, loadNotes, noteDraft, onReload, vi]);

  const handleUpdateNote = useCallback(
    async (note: CollectionNoteRecord) => {
      if (!collectionId) return;
      setPendingNoteId(note.note_id);
      setWriteFailure(null);
      try {
        await updateCollectionNote(collectionId, note.note_id, { revision: note.revision, text: editingText });
        setEditingNoteId(null);
        setWriteNotice(vi ? "Đã cập nhật ghi chú." : "Note updated.");
        await loadNotes();
        onReload();
      } catch (error) {
        setWriteFailure(describeCollectionFailure(error, vi));
      } finally {
        setPendingNoteId(null);
      }
    },
    [collectionId, editingText, loadNotes, onReload, vi],
  );

  const handleDeleteNote = useCallback(
    async (note: CollectionNoteRecord) => {
      if (!collectionId) return;
      setPendingNoteId(note.note_id);
      setWriteFailure(null);
      try {
        await deleteCollectionNote(collectionId, note.note_id, note.revision);
        setWriteNotice(vi ? "Đã xoá ghi chú." : "Note deleted.");
        await loadNotes();
        onReload();
      } catch (error) {
        setWriteFailure(describeCollectionFailure(error, vi));
      } finally {
        setPendingNoteId(null);
      }
    },
    [collectionId, loadNotes, onReload, vi],
  );

  const handleSaveSettings = useCallback(
    async (patch: Omit<CollectionUpdateRequest, "revision">) => {
      if (!collection) return;
      setSaving(true);
      setWriteFailure(null);
      try {
        const updated = await updateCollection(collection.collection_id, { ...patch, revision: collection.revision });
        onChanged(updated);
        setWriteNotice(vi ? "Đã lưu thiết lập bộ sưu tập." : "Collection settings saved.");
      } catch (error) {
        setWriteFailure(describeCollectionFailure(error, vi));
      } finally {
        setSaving(false);
      }
    },
    [collection, onChanged, vi],
  );

  const handleToggleFavorite = useCallback(async () => {
    if (!collection) return;
    setWriteFailure(null);
    try {
      const updated = await updateCollection(collection.collection_id, {
        revision: collection.revision,
        favorite: !collection.favorite,
      });
      onChanged(updated);
    } catch (error) {
      setWriteFailure(describeCollectionFailure(error, vi));
    }
  }, [collection, onChanged, vi]);

  const handleDeleteCollection = useCallback(async () => {
    if (!collection) return;
    setDeleting(true);
    setWriteFailure(null);
    try {
      await deleteCollection(collection.collection_id, collection.revision);
      onDeleted(collection.collection_id);
    } catch (error) {
      const described = describeCollectionFailure(error, vi);
      setWriteFailure(described);
      // A tombstone that is already gone is not a failure of this action.
      if (described.kind === "gone") onDeleted(collection.collection_id);
    } finally {
      setDeleting(false);
    }
  }, [collection, onDeleted, vi]);

  const handleExport = useCallback(
    async (format: "json" | "markdown") => {
      if (!collection) return;
      onExportRequested(null);
      try {
        const result = await exportCollection(collection.collection_id, format);
        const content = result.format === "markdown" ? result.content : JSON.stringify(result.document, null, 2);
        const blob = new Blob([content], { type: result.format === "markdown" ? "text/markdown" : "application/json" });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = exportFileName(collection, result.format);
        anchor.click();
        URL.revokeObjectURL(url);
        onExportRequested(vi ? `Đã xuất ${collection.name}.` : `Exported ${collection.name}.`);
      } catch (error) {
        const described = describeCollectionFailure(error, vi);
        setWriteFailure(described);
        onExportRequested(described.message);
      }
    },
    [collection, onExportRequested, vi],
  );

  const privacy = useMemo(() => (collection ? privacySummary(collection.private, vi) : null), [collection, vi]);
  const updatedLabel = useMemo(
    () => (collection ? formatRelativeTime(collection.updated_at, vi, now) : null),
    [collection, now, vi],
  );

  if (!collection) {
    return (
      <aside className="collection-rail" aria-label={vi ? "Chi tiết bộ sưu tập" : "Collection details"}>
        <div className="collection-rail__card">
          {loading ? (
            <p className="collection-contents__status" role="status">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              {vi ? "Đang đọc bộ sưu tập…" : "Reading the collection…"}
            </p>
          ) : failure ? (
            <div className="workspace-alert workspace-alert--error" role="alert">
              <strong>{failure.title}</strong>
              <p>{failure.message}</p>
              <button type="button" className="console-btn" onClick={onReload}>
                {vi ? "Thử lại" : "Try again"}
              </button>
            </div>
          ) : (
            <div className="console-empty">
              <FolderOpen aria-hidden="true" />
              <strong>{vi ? "Chọn một bộ sưu tập" : "Select a collection"}</strong>
              <p>
                {vi
                  ? "Mở một bộ sưu tập để xem mục, ghi chú, hoạt động và thiết lập thật của nó."
                  : "Open a collection to read its members, notes, recorded activity and settings."}
              </p>
            </div>
          )}
        </div>
      </aside>
    );
  }

  const tabs: Array<{ id: DetailTab; label: string }> = [
    { id: "contents", label: vi ? "Nội dung" : "Contents" },
    { id: "notes", label: vi ? "Ghi chú" : "Notes" },
    { id: "activity", label: vi ? "Hoạt động" : "Activity" },
    { id: "settings", label: vi ? "Thiết lập" : "Settings" },
  ];

  return (
    <aside className="collection-rail" aria-label={vi ? `Chi tiết ${collection.name}` : `${collection.name} details`}>
      <div className="collection-rail__card">
        <div className="collection-rail__header">
          <span className="collection-rail__tile" aria-hidden="true">
            <FolderOpen />
          </span>
          <div className="collection-rail__heading">
            <h3 className="collection-rail__title">
              {collection.name}
              <button
                type="button"
                className="collection-card__star"
                aria-label={collection.favorite
                  ? (vi ? "Bỏ yêu thích" : "Remove from favorites")
                  : (vi ? "Đánh dấu yêu thích" : "Mark as favorite")}
                aria-pressed={collection.favorite}
                onClick={() => void handleToggleFavorite()}
              >
                <span className={`collection-rail__star ${collection.favorite ? "is-on" : ""}`} aria-hidden="true">★</span>
              </button>
            </h3>
            {collection.description.trim().length > 0 && (
              <p className="collection-rail__description">{collection.description}</p>
            )}
          </div>
          <div className="collection-rail__header-actions">
            <CollectionActionMenu
              label={vi ? "Hành động bộ sưu tập" : "Collection actions"}
              items={[
                { key: "rename", label: vi ? "Đổi tên" : "Rename", onSelect: onRename },
                { key: "export-json", label: vi ? "Xuất JSON" : "Export JSON", onSelect: () => void handleExport("json") },
                { key: "export-markdown", label: vi ? "Xuất Markdown" : "Export Markdown", onSelect: () => void handleExport("markdown") },
                {
                  key: "delete",
                  label: vi ? "Xoá bộ sưu tập" : "Delete collection",
                  onSelect: () => void handleDeleteCollection(),
                  danger: true,
                },
              ]}
            />
            <button
              type="button"
              className="collection-rail__close"
              aria-label={vi ? "Đóng chi tiết bộ sưu tập" : "Close collection details"}
              onClick={onClose}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        <dl className="collection-rail__stats">
          <div className="collection-rail__stat">
            <dt>
              <FileText className="collection-rail__stat-icon" aria-hidden="true" />
              {vi ? "Số mục" : "Items"}
            </dt>
            <dd>{memberCountLabel(collection.item_count, vi)}</dd>
          </div>
          <div className="collection-rail__stat">
            <dt>
              <Clock className="collection-rail__stat-icon" aria-hidden="true" />
              {vi ? "Cập nhật" : "Updated"}
            </dt>
            <dd>{updatedLabel ?? (vi ? "chưa ghi nhận" : "not reported")}</dd>
          </div>
          <div className="collection-rail__stat">
            <dt>
              <ShieldCheck className="collection-rail__stat-icon" aria-hidden="true" />
              {privacy?.label ?? ""}
            </dt>
            <dd>{privacy?.detail ?? ""}</dd>
          </div>
        </dl>

        <div className="console-underline-tabs collection-rail__tabs" role="tablist" aria-label={vi ? "Khu vực chi tiết" : "Detail areas"}>
          {tabs.map((entry) => (
            <button
              key={entry.id}
              type="button"
              role="tab"
              id={`collection-tab-${entry.id}`}
              aria-selected={tab === entry.id}
              aria-controls={`collection-panel-${entry.id}`}
              className={`console-underline-tab ${tab === entry.id ? "is-active" : ""}`}
              onClick={() => setTab(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </div>

        {writeNotice && (
          <p className="collection-rail__notice" role="status">
            <Info className="h-3.5 w-3.5" aria-hidden="true" />
            {writeNotice}
          </p>
        )}
        {writeFailure && tab !== "settings" && (
          <div className={`workspace-alert ${writeFailure.kind === "conflict" ? "collection-alert--conflict" : "workspace-alert--error"}`} role="alert">
            <strong>{writeFailure.title}</strong>
            <p>{writeFailure.message}</p>
            {writeFailure.kind === "conflict" && (
              <button
                type="button"
                className="console-btn"
                onClick={() => {
                  setWriteFailure(null);
                  onReload();
                }}
              >
                {vi ? "Tải lại bộ sưu tập" : "Reload collection"}
              </button>
            )}
          </div>
        )}

        <div
          className="collection-rail__panel"
          role="tabpanel"
          id={`collection-panel-${tab}`}
          aria-labelledby={`collection-tab-${tab}`}
        >
          {tab === "contents" && (
            <CollectionContents
              vi={vi}
              items={items}
              total={itemsTotal}
              loading={itemsLoading}
              failure={itemsFailure}
              kindFilter={kindFilter}
              onKindFilterChange={setKindFilter}
              onAddDocuments={onAddDocuments}
              onOpenItem={onOpenItem}
              onRemoveItem={(item) => void handleRemoveItem(item)}
              pendingItemId={pendingItemId}
              focusIdFor={returnFocusIdFor}
            />
          )}
          {tab === "notes" && (
            <CollectionNotes
              vi={vi}
              notes={notes}
              total={notesTotal}
              loading={notesLoading}
              failure={notesFailure}
              draft={noteDraft}
              onDraftChange={setNoteDraft}
              onSubmit={() => void handleAddNote()}
              submitting={noteSaving}
              editingNoteId={editingNoteId}
              editingText={editingText}
              onEditStart={(note) => {
                setEditingNoteId(note.note_id);
                setEditingText(note.text);
              }}
              onEditChange={setEditingText}
              onEditCancel={() => setEditingNoteId(null)}
              onEditSubmit={() => {
                const note = notes.find((entry) => entry.note_id === editingNoteId);
                if (note) void handleUpdateNote(note);
              }}
              onDelete={(note) => void handleDeleteNote(note)}
              pendingNoteId={pendingNoteId}
            />
          )}
          {tab === "activity" && (
            <CollectionActivity
              vi={vi}
              events={events}
              total={eventsTotal}
              loading={eventsLoading}
              failure={eventsFailure}
              now={now}
            />
          )}
          {tab === "settings" && (
            <CollectionSettings
              key={`${collection.collection_id}:${collection.revision}`}
              vi={vi}
              collection={collection}
              saving={saving}
              deleting={deleting}
              failure={writeFailure}
              staleRevision={writeFailure?.kind === "conflict"}
              onReload={() => {
                setWriteFailure(null);
                onReload();
              }}
              onSave={(patch) => void handleSaveSettings(patch)}
              onDelete={() => void handleDeleteCollection()}
            />
          )}
        </div>

        <p className="collection-rail__footnote">
          <Activity className="h-3 w-3" aria-hidden="true" />
          {vi
            ? `Bản sửa đổi ${collection.revision} · hoạt động và ghi chú do workspace ghi lại`
            : `Revision ${collection.revision} · activity and notes recorded by the workspace`}
          <StickyNote className="h-3 w-3" aria-hidden="true" />
        </p>
      </div>
    </aside>
  );
}
