import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bookmark, FolderOpen, Loader2, MessageSquare, ShieldAlert } from "lucide-react";

import {
  createCollection,
  deleteCollection,
  exportCollection,
  getCollection,
  listCollections,
  updateCollection,
} from "../../lib/api";
import type {
  CollectionItemRecord,
  CollectionRecord,
  CollectionSortDirection,
  CollectionSortField,
  DocumentWorkspaceTarget,
  Source,
} from "../../types";
import {
  describeCollectionFailure,
  exportFileName,
  isWorkspaceAvailabilityFailure,
  itemOpenTarget,
  listUnavailableFailure,
} from "../../lib/collectionModel";
import type { CollectionFailure } from "../../lib/collectionModel";
import { useLocale } from "../../lib/i18n";
import { AddItemsDialog } from "./AddItemsDialog";
import { CollectionCard } from "./CollectionCard";
import { CollectionDetail } from "./CollectionDetail";
import { CollectionDeleteDialog } from "./CollectionDeleteDialog";
import { CollectionFormDialog } from "./CollectionFormDialog";
import { CollectionsToolbar } from "./CollectionsToolbar";
import { ExportDialog } from "./ExportDialog";

/** The page's tab row: two real collection views plus the preserved library. */
export type CollectionsTab = "all" | "favorites" | "conversations";

/** Stable return-focus identity for a member opened from the rail. */
export function collectionItemFocusId(itemId: string): string {
  return `collection-member-${itemId.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

interface CollectionsWorkspaceProps {
  /** The selected collection comes from the route, so back/forward work. */
  selectedCollectionId: string | null;
  onSelectCollection: (collectionId: string | null) => void;
  onOpenDocument: (target: DocumentWorkspaceTarget) => void;
  onOpenEvidence: (source: Source, returnFocusId: string) => void;
  onOpenMessage: (conversationId: string, messageId: string | null) => void;
  /** The existing conversation library, preserved on its own tab. */
  librarySlot: React.ReactNode;
  /** "conversations" opens the preserved library directly. */
  initialTab?: "collections" | "conversations";
  focusConversationSearch?: boolean;
  onConversationSearchFocused?: () => void;
}

const PAGE_SIZE = 25;

/**
 * The Collections workspace: the reference's list/rail composition over the
 * DATA-003 typed collection repository.
 *
 * Reads are the only thing that happens implicitly — opening the page,
 * searching, sorting, switching tabs and selecting a collection never write.
 * Every write is an explicit user action that carries the revision the page
 * last read, and a refusal is shown as the state it is.
 */
export function CollectionsWorkspace({
  selectedCollectionId,
  onSelectCollection,
  onOpenDocument,
  onOpenEvidence,
  onOpenMessage,
  librarySlot,
  initialTab = "collections",
  focusConversationSearch = false,
  onConversationSearchFocused,
}: CollectionsWorkspaceProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";

  const [tab, setTab] = useState<CollectionsTab>(initialTab === "conversations" ? "conversations" : "all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<CollectionSortField>("updated_at");
  const [direction, setDirection] = useState<CollectionSortDirection>("desc");
  const [view, setView] = useState<"grid" | "list">("list");
  const [page, setPage] = useState(1);

  const [collections, setCollections] = useState<CollectionRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [favoriteTotal, setFavoriteTotal] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [listFailure, setListFailure] = useState<CollectionFailure | null>(null);

  const [selected, setSelected] = useState<CollectionRecord | null>(null);
  const [selectionLoading, setSelectionLoading] = useState(false);
  const [selectionFailure, setSelectionFailure] = useState<CollectionFailure | null>(null);

  const [notice, setNotice] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "rename">("create");
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [addItemsFor, setAddItemsFor] = useState<CollectionRecord | null>(null);
  const [exportFor, setExportFor] = useState<CollectionRecord | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CollectionRecord | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [formCollection, setFormCollection] = useState<CollectionRecord | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const listEpoch = useRef(0);
  const listController = useRef<AbortController | null>(null);
  const selectionEpoch = useRef(0);
  const selectionController = useRef<AbortController | null>(null);
  const deleteInFlight = useRef(false);

  const favoritesOnly = tab === "favorites";

  const loadCollections = useCallback(async () => {
    const epoch = ++listEpoch.current;
    listController.current?.abort();
    const controller = new AbortController();
    listController.current = controller;
    setListLoading(true);
    try {
      const [active, favorites, all] = await Promise.all([
        listCollections(
          {
            search: search || undefined,
            favorite: favoritesOnly ? true : undefined,
            sort,
            direction,
            page,
            page_size: PAGE_SIZE,
          },
          controller.signal,
        ),
        listCollections({ search: search || undefined, favorite: true, page: 1, page_size: 1 }, controller.signal),
        favoritesOnly
          ? listCollections({ search: search || undefined, page: 1, page_size: 1 }, controller.signal)
          : Promise.resolve(null),
      ]);
      if (listEpoch.current !== epoch) return;
      setCollections(active.items);
      setTotal(active.total);
      setFavoriteTotal(favorites.total);
      if (all) setTotal(all.total);
      setListFailure(null);
    } catch (error) {
      if (listEpoch.current !== epoch) return;
      if ((error as { name?: string })?.name === "AbortError") return;
      const described = describeCollectionFailure(error, vi);
      setCollections([]);
      setTotal(0);
      setFavoriteTotal(0);
      // A 404 on the list route is the workspace boundary hiding the whole
      // capability in this deployment mode; it is not an empty workspace.
      setListFailure(described.status === 404 ? listUnavailableFailure(vi) : described);
    } finally {
      if (listEpoch.current === epoch) setListLoading(false);
    }
  }, [direction, favoritesOnly, page, search, sort, vi]);

  useEffect(() => {
    void loadCollections();
  }, [loadCollections]);

  // The selection can come from a deep link that is not on the current page, so
  // it is read directly and guarded against the page's own list responses.
  const loadSelection = useCallback(async () => {
    if (!selectedCollectionId) {
      setSelected(null);
      setSelectionFailure(null);
      return;
    }
    const inPage = collections.find((entry) => entry.collection_id === selectedCollectionId);
    if (inPage) {
      setSelected(inPage);
      setSelectionFailure(null);
      return;
    }
    const epoch = ++selectionEpoch.current;
    selectionController.current?.abort();
    const controller = new AbortController();
    selectionController.current = controller;
    setSelectionLoading(true);
    try {
      const record = await getCollection(selectedCollectionId, controller.signal);
      if (selectionEpoch.current !== epoch) return;
      setSelected(record);
      setSelectionFailure(null);
    } catch (error) {
      if (selectionEpoch.current !== epoch) return;
      if ((error as { name?: string })?.name === "AbortError") return;
      setSelected(null);
      setSelectionFailure(describeCollectionFailure(error, vi));
    } finally {
      if (selectionEpoch.current === epoch) setSelectionLoading(false);
    }
  }, [collections, selectedCollectionId, vi]);

  useEffect(() => {
    void loadSelection();
  }, [loadSelection]);

  useEffect(() => {
    setPage(1);
  }, [search, sort, direction, tab]);

  useEffect(() => {
    if (focusConversationSearch) setTab("conversations");
  }, [focusConversationSearch]);

  useEffect(() => {
    if (!focusConversationSearch || tab !== "conversations") return;
    const frame = window.requestAnimationFrame(() => {
      const input = document.getElementById("library-search-input");
      if (!input) return;
      input.focus({ preventScroll: true });
      onConversationSearchFocused?.();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [focusConversationSearch, onConversationSearchFocused, tab]);

  useEffect(() => {
    // Relative times stay honest across a long-lived page without re-fetching.
    const timer = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(
    () => () => {
      listController.current?.abort();
      selectionController.current?.abort();
    },
    [],
  );

  const refreshAfterWrite = useCallback(async () => {
    await loadCollections();
  }, [loadCollections]);

  const handleToggleFavorite = useCallback(
    async (collection: CollectionRecord) => {
      setNotice(null);
      try {
        const updated = await updateCollection(collection.collection_id, {
          revision: collection.revision,
          favorite: !collection.favorite,
        });
        setSelected((current) => (current?.collection_id === updated.collection_id ? updated : current));
        await refreshAfterWrite();
      } catch (error) {
        const described = describeCollectionFailure(error, vi);
        setNotice(`${described.title}: ${described.message}`);
      }
    },
    [refreshAfterWrite, vi],
  );

  const handleCreate = useCallback(
    async (values: { name: string; description?: string; tags?: string[] }) => {
      setFormSubmitting(true);
      setFormError(null);
      try {
        const created = await createCollection(values);
        setFormOpen(false);
        setNotice(vi ? `Đã tạo “${created.name}”.` : `Created “${created.name}”.`);
        await loadCollections();
        onSelectCollection(created.collection_id);
      } catch (error) {
        const described = describeCollectionFailure(error, vi);
        setFormError(described.message);
      } finally {
        setFormSubmitting(false);
      }
    },
    [loadCollections, onSelectCollection, vi],
  );

  const handleRename = useCallback(
    async (values: { name: string }) => {
      const target = formCollection;
      if (!target) return;
      setFormSubmitting(true);
      setFormError(null);
      try {
        const updated = await updateCollection(target.collection_id, { revision: target.revision, name: values.name });
        setFormOpen(false);
        setSelected((current) => (current?.collection_id === updated.collection_id ? updated : current));
        setNotice(vi ? "Đã lưu tên mới." : "Name saved.");
        await loadCollections();
      } catch (error) {
        const described = describeCollectionFailure(error, vi);
        setFormError(described.kind === "conflict" ? `${described.title}. ${described.message}` : described.message);
      } finally {
        setFormSubmitting(false);
      }
    },
    [formCollection, loadCollections, vi],
  );

  const openCreate = useCallback(() => {
    setFormMode("create");
    setFormCollection(null);
    setFormError(null);
    setFormOpen(true);
  }, []);

  const openRename = useCallback((collection: CollectionRecord) => {
    setFormMode("rename");
    setFormCollection(collection);
    setFormError(null);
    setFormOpen(true);
  }, []);

  const requestDelete = useCallback((collection: CollectionRecord) => {
    setDeleteError(null);
    setDeleteTarget(collection);
  }, []);

  const handleDeleteConfirmed = useCallback(
    async () => {
      const collection = deleteTarget;
      if (!collection || deleteInFlight.current) return;
      deleteInFlight.current = true;
      setDeleteSubmitting(true);
      setNotice(null);
      try {
        await deleteCollection(collection.collection_id, collection.revision);
        setDeleteTarget(null);
        setNotice(vi ? `Đã xoá “${collection.name}”.` : `Deleted “${collection.name}”.`);
        if (selectedCollectionId === collection.collection_id) {
          setSelected(null);
          onSelectCollection(null);
        }
        await loadCollections();
      } catch (error) {
        const described = describeCollectionFailure(error, vi);
        if (described.kind === "gone") {
          setDeleteTarget(null);
          setNotice(vi ? "Bộ sưu tập đã bị xoá trước đó." : "The collection was already deleted.");
          if (selectedCollectionId === collection.collection_id) {
            setSelected(null);
            onSelectCollection(null);
          }
          await loadCollections();
          return;
        }
        setDeleteError(`${described.title}: ${described.message}`);
      } finally {
        deleteInFlight.current = false;
        setDeleteSubmitting(false);
      }
    },
    [deleteTarget, loadCollections, onSelectCollection, selectedCollectionId, vi],
  );

  const handleExport = useCallback(
    async (collection: CollectionRecord, format: "json" | "markdown") => {
      setExporting(true);
      setExportError(null);
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
        setExportFor(null);
        setNotice(vi ? `Đã xuất “${collection.name}”.` : `Exported “${collection.name}”.`);
      } catch (error) {
        const described = describeCollectionFailure(error, vi);
        setExportError(described.message);
      } finally {
        setExporting(false);
      }
    },
    [vi],
  );

  const handleOpenItem = useCallback(
    (item: CollectionItemRecord) => {
      setNotice(null);
      const focusId = collectionItemFocusId(item.item_id);
      const target = itemOpenTarget(item, vi);
      if (target.kind === "document") {
        onOpenDocument({
          kind: "catalog",
          documentId: target.documentId,
          title: target.title,
          ticker: target.ticker,
          filingDate: target.filingDate,
          reportDate: target.reportDate,
          accessionNumber: target.accessionNumber,
          returnView: "library",
          returnFocusId: focusId,
        });
        return;
      }
      if (target.kind === "evidence") {
        onOpenEvidence(target.source, focusId);
        return;
      }
      if (target.kind === "answer") {
        if (!target.conversationId) {
          setNotice(vi ? "Mục câu trả lời này không có hội thoại gốc để mở." : "This answer member has no originating conversation to open.");
          return;
        }
        onOpenMessage(target.conversationId, target.messageId);
        return;
      }
      setNotice(target.reason);
    },
    [onOpenDocument, onOpenEvidence, onOpenMessage, vi],
  );

  const availabilityFailure = listFailure && isWorkspaceAvailabilityFailure(listFailure) ? listFailure : null;
  const listError = listFailure && !availabilityFailure ? listFailure : null;

  const collectionCount = useMemo(() => total, [total]);

  return (
    <section className="workspace-page workspace-page--standard console-view-enter collections-page" aria-labelledby="collections-title">
      <div className="console-page-header collections-page__header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><Bookmark aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="collections-title" className="console-page-header__title">{vi ? "Bộ sưu tập" : "Collections"}</h1>
            <p className="console-page-header__subtitle">
              {vi
                ? "Tổ chức, lưu và mở lại tài liệu, bằng chứng, câu trả lời và ghi chú trong workspace cục bộ."
                : "Organize, save, and reopen documents, evidence, answers and notes in the local workspace."}
            </p>
          </div>
        </div>
        {tab !== "conversations" && !availabilityFailure && (
          <CollectionsToolbar
            vi={vi}
            search={search}
            onSearchChange={setSearch}
            sort={sort}
            direction={direction}
            onSortChange={(value) => {
              const [field, dir] = value.split(":");
              setSort(field as CollectionSortField);
              setDirection((dir as CollectionSortDirection) ?? "desc");
            }}
            view={view}
            onViewChange={setView}
            onCreate={openCreate}
          />
        )}
      </div>

      <div className="console-underline-tabs collections-tabs" role="tablist" aria-label={vi ? "Khu vực thư viện" : "Library areas"}>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "all"}
          className={`console-underline-tab ${tab === "all" ? "is-active" : ""}`}
          onClick={() => setTab("all")}
        >
          {vi ? "Bộ sưu tập" : "All Collections"}
          <span className="console-tab__count">{collectionCount}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "favorites"}
          className={`console-underline-tab ${tab === "favorites" ? "is-active" : ""}`}
          onClick={() => setTab("favorites")}
        >
          {vi ? "Yêu thích" : "Favorites"}
          <span className="console-tab__count">{favoriteTotal}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "conversations"}
          className={`console-underline-tab ${tab === "conversations" ? "is-active" : ""}`}
          onClick={() => setTab("conversations")}
        >
          <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
          {vi ? "Cuộc trò chuyện" : "Conversations"}
        </button>
      </div>

      {notice && (
        <p className="collections-page__notice" role="status">{notice}</p>
      )}

      {tab === "conversations" ? (
        <div className="library-workspace-surface">{librarySlot}</div>
      ) : availabilityFailure ? (
        <div className="collections-unavailable" role="status">
          <ShieldAlert aria-hidden="true" />
          <h2>{availabilityFailure.title}</h2>
          <p>{availabilityFailure.message}</p>
          <p className="collections-unavailable__hint">
            {vi
              ? "Không có danh sách rỗng giả: workspace không trả về bộ sưu tập trong ngữ cảnh này."
              : "No empty list is shown: the workspace does not serve collections in this context."}
          </p>
        </div>
      ) : (
        <div className="collections-layout">
          <div className="collections-layout__main">
            {listError && (
              <div className="workspace-alert workspace-alert--error" role="alert">
                <strong>{listError.title}</strong>
                <p>{listError.message}</p>
                <button type="button" className="console-btn" onClick={() => void loadCollections()}>
                  {vi ? "Thử lại" : "Try again"}
                </button>
              </div>
            )}

            {listLoading && collections.length === 0 && (
              <p className="collection-contents__status" role="status">
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                {vi ? "Đang đọc bộ sưu tập…" : "Reading collections…"}
              </p>
            )}

            {!listLoading && !listError && collections.length === 0 && (
              <div className="console-empty collection-empty--page">
                <FolderOpen aria-hidden="true" />
                <strong>
                  {search
                    ? vi ? "Không có bộ sưu tập nào khớp tìm kiếm" : "No collection matches this search"
                    : favoritesOnly
                      ? vi ? "Chưa có bộ sưu tập yêu thích" : "No favorite collection yet"
                      : vi ? "Chưa có bộ sưu tập nào" : "No collections yet"}
                </strong>
                <p>
                  {search || favoritesOnly
                    ? vi ? "Điều chỉnh tìm kiếm hoặc bỏ bộ lọc yêu thích." : "Adjust the search or clear the favorites filter."
                    : vi
                      ? "Tạo bộ sưu tập mới, hoặc lưu bằng chứng từ Search/Retrieval và tài liệu từ Documents."
                      : "Create a collection, or save evidence from Search/Retrieval and documents from Documents."}
                </p>
                <button type="button" className="console-btn console-btn--primary" onClick={openCreate}>
                  {vi ? "Bộ sưu tập mới" : "New Collection"}
                </button>
              </div>
            )}

            {collections.length > 0 && (
              <ul className={`collections-grid ${view === "grid" ? "collections-grid--grid" : "collections-grid--list"}`} aria-label={vi ? "Bộ sưu tập" : "Collections"}>
                {collections.map((collection) => (
                  <li key={collection.collection_id}>
                    <CollectionCard
                      collection={collection}
                      selected={collection.collection_id === selectedCollectionId}
                      vi={vi}
                      now={now}
                      onOpen={() => onSelectCollection(collection.collection_id)}
                      onToggleFavorite={() => void handleToggleFavorite(collection)}
                      onAddDocuments={() => setAddItemsFor(collection)}
                      onExport={() => {
                        setExportError(null);
                        setExportFor(collection);
                      }}
                      onRename={() => openRename(collection)}
                      onDelete={() => requestDelete(collection)}
                    />
                  </li>
                ))}
              </ul>
            )}

            {total > collections.length && (
              <div className="collections-page__more">
                <button type="button" className="console-btn" onClick={() => setPage((current) => current + 1)} disabled={listLoading}>
                  {vi ? `Hiển thị thêm (${collections.length}/${total})` : `Show more (${collections.length}/${total})`}
                </button>
              </div>
            )}
          </div>

          <CollectionDetail
            vi={vi}
            collection={selected}
            loading={selectionLoading}
            failure={selectionFailure}
            now={now}
            onClose={() => onSelectCollection(null)}
            onReload={() => {
              void loadSelection();
              void loadCollections();
            }}
            onChanged={(updated) => {
              setSelected(updated);
              void loadCollections();
            }}
            onDeleteRequested={requestDelete}
            onOpenItem={handleOpenItem}
            onAddDocuments={() => {
              if (selected) setAddItemsFor(selected);
            }}
            onRename={() => {
              if (selected) openRename(selected);
            }}
            onExportRequested={(message) => setNotice(message)}
            returnFocusIdFor={collectionItemFocusId}
          />
        </div>
      )}

      <CollectionFormDialog
        open={formOpen}
        vi={vi}
        mode={formMode}
        collection={formCollection}
        submitting={formSubmitting}
        errorMessage={formError}
        onSubmit={(values) => {
          if (formMode === "create") void handleCreate(values);
          else void handleRename(values as { name: string });
        }}
        onClose={() => setFormOpen(false)}
      />

      {addItemsFor && (
        <AddItemsDialog
          open
          vi={vi}
          collectionId={addItemsFor.collection_id}
          collectionName={addItemsFor.name}
          onClose={() => setAddItemsFor(null)}
          onAdded={(count) => {
            setNotice(
              count === 1
                ? vi ? "Đã thêm 1 tài liệu." : "Added 1 document."
                : vi ? `Đã thêm ${count} tài liệu.` : `Added ${count} documents.`,
            );
            void loadCollections();
            void loadSelection();
          }}
        />
      )}

      <ExportDialog
        open={exportFor !== null}
        vi={vi}
        collection={exportFor}
        exporting={exporting}
        errorMessage={exportError}
        onExport={(format) => {
          if (exportFor) void handleExport(exportFor, format);
        }}
        onClose={() => setExportFor(null)}
      />

      <CollectionDeleteDialog
        vi={vi}
        collection={deleteTarget}
        deleting={deleteSubmitting}
        errorMessage={deleteError}
        onCancel={() => {
          if (deleteInFlight.current) return;
          setDeleteTarget(null);
          setDeleteError(null);
        }}
        onConfirm={() => void handleDeleteConfirmed()}
      />
    </section>
  );
}
