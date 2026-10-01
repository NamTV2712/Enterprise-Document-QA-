import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Plus, Search, ShieldAlert } from "lucide-react";

import { addCollectionItem, createCollection, listCollections } from "../../lib/api";
import type { CollectionRecord, Source } from "../../types";
import {
  citationForSource,
  describeCollectionFailure,
  evidenceReferenceFromSource,
  excerptForSource,
  isWorkspaceAvailabilityFailure,
  listUnavailableFailure,
  memberCountLabel,
  snapshotFromSource,
} from "../../lib/collectionModel";
import type { CollectionFailure } from "../../lib/collectionModel";
import { ModalDialog } from "../ui/ModalDialog";

interface CollectionTargetDialogProps {
  open: boolean;
  vi: boolean;
  /** The retrieved source a page asked to save; never a fabricated one. */
  source: Source | null;
  onClose: () => void;
  onSaved: (collectionName: string) => void;
  onFailure: (message: string) => void;
}

/**
 * "Save evidence" / "Add to Collection" from Documents, Search, Retrieval and
 * Reranker lands here: the user names a real target, and the member is written
 * as a typed DATA-003 `evidence` item carrying the source's own identities.
 * Nothing is written until the user picks a target, and the on-device library
 * remains untouched, so there is never a silent dual write.
 */
export function CollectionTargetDialog({
  open,
  vi,
  source,
  onClose,
  onSaved,
  onFailure,
}: CollectionTargetDialogProps) {
  const [collections, setCollections] = useState<CollectionRecord[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState<CollectionFailure | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const epoch = useRef(0);
  const controller = useRef<AbortController | null>(null);

  const load = useCallback(
    async (needle: string) => {
      const current = ++epoch.current;
      controller.current?.abort();
      const abort = new AbortController();
      controller.current = abort;
      setLoading(true);
      try {
        const response = await listCollections(
          { search: needle || undefined, sort: "updated_at", direction: "desc", page: 1, page_size: 50 },
          abort.signal,
        );
        if (epoch.current !== current) return;
        setCollections(response.items);
        setFailure(null);
      } catch (error) {
        if (epoch.current !== current) return;
        if ((error as { name?: string })?.name === "AbortError") return;
        setCollections([]);
        setFailure((error as { status?: number })?.status === 404
          ? listUnavailableFailure(vi)
          : describeCollectionFailure(error, vi));
      } finally {
        if (epoch.current === current) setLoading(false);
      }
    },
    [vi],
  );

  useEffect(() => {
    if (!open) return;
    setSearch("");
    setSelectedId(null);
    setNewName("");
    setFailure(null);
    void load("");
  }, [load, open]);

  useEffect(
    () => () => {
      controller.current?.abort();
    },
    [],
  );

  const memberRequest = useCallback(() => {
    if (!source) return null;
    const reference = evidenceReferenceFromSource(source);
    const snapshot = snapshotFromSource(source);
    return {
      item_kind: "evidence" as const,
      citation: citationForSource(source),
      excerpt: excerptForSource(source),
      reference,
      ...(snapshot ? { snapshot } : {}),
    };
  }, [source]);

  const handleAddToExisting = async () => {
    const target = collections.find((entry) => entry.collection_id === selectedId);
    const request = memberRequest();
    if (!target || !request) return;
    setSubmitting(true);
    try {
      await addCollectionItem(target.collection_id, request);
      onSaved(target.name);
      onClose();
    } catch (error) {
      const described = describeCollectionFailure(error, vi);
      setFailure(described);
      onFailure(`${described.title}. ${described.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateAndAdd = async () => {
    const request = memberRequest();
    if (!request || newName.trim().length === 0) return;
    setSubmitting(true);
    try {
      const created = await createCollection({ name: newName.trim() });
      await addCollectionItem(created.collection_id, request);
      onSaved(created.name);
      onClose();
    } catch (error) {
      const described = describeCollectionFailure(error, vi);
      setFailure(described);
      onFailure(`${described.title}. ${described.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const unavailable = failure && isWorkspaceAvailabilityFailure(failure) ? failure : null;
  const listProblem = failure && !unavailable ? failure : null;

  return (
    <ModalDialog
      open={open}
      onClose={onClose}
      labelledBy="collection-target-title"
      describedBy="collection-target-hint"
      initialFocusRef={searchRef}
      overlayClassName="items-start pt-[10vh]"
      className="collections-dialog w-full max-w-xl overflow-hidden rounded-2xl border border-[var(--border-subtle)] surface-raised shadow-2xl"
    >
      <div className="collections-dialog__header">
        <div>
          <h2 id="collection-target-title" className="collections-dialog__title">
            {vi ? "Lưu bằng chứng vào bộ sưu tập" : "Save evidence to a collection"}
          </h2>
          <p id="collection-target-hint" className="collections-dialog__hint">
            {source
              ? vi
                ? `Mục sẽ được thêm với định danh nguồn thật: ${citationForSource(source) || "không có trích dẫn"}`
                : `The member is added with the source's real identity: ${citationForSource(source) || "no citation recorded"}`
              : ""}
          </p>
        </div>
      </div>

      {unavailable ? (
        <div className="collections-dialog__body">
          <div className="collections-unavailable collections-unavailable--compact" role="status">
            <ShieldAlert aria-hidden="true" />
            <h3>{unavailable.title}</h3>
            <p>{unavailable.message}</p>
            <p className="collections-unavailable__hint">
              {vi
                ? "Bằng chứng vẫn nằm trong thư viện trên thiết bị; workspace cục bộ không nhận thêm mục trong ngữ cảnh này."
                : "The evidence stays in the on-device library; the local workspace does not accept members in this context."}
            </p>
          </div>
          <div className="collections-dialog__actions">
            <button type="button" className="console-btn" onClick={onClose}>
              {vi ? "Đóng" : "Close"}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="collections-dialog__search console-input-row">
            <Search aria-hidden="true" />
            <input
              ref={searchRef}
              className="console-input"
              type="search"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                void load(event.target.value);
              }}
              placeholder={vi ? "Tìm bộ sưu tập…" : "Search collections…"}
              aria-label={vi ? "Tìm bộ sưu tập" : "Search collections"}
            />
          </div>

          {listProblem && (
            <div className="workspace-alert workspace-alert--error" role="alert">
              <strong>{listProblem.title}</strong>
              <p>{listProblem.message}</p>
            </div>
          )}

          <div className="collections-dialog__body">
            {loading && (
              <p className="collection-contents__status" role="status">
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                {vi ? "Đang đọc bộ sưu tập…" : "Reading collections…"}
              </p>
            )}
            {!loading && collections.length === 0 && !listProblem && (
              <p className="collections-dialog__empty">
                {search
                  ? vi ? "Không có bộ sưu tập nào khớp tìm kiếm." : "No collection matches this search."
                  : vi ? "Chưa có bộ sưu tập nào. Tạo một bộ sưu tập mới bên dưới." : "No collections yet. Create one below."}
              </p>
            )}
            {collections.length > 0 && (
              <ul className="collections-dialog__list" aria-label={vi ? "Bộ sưu tập" : "Collections"}>
                {collections.map((collection) => (
                  <li key={collection.collection_id}>
                    <label className="collections-dialog__row collections-dialog__row--radio">
                      <input
                        type="radio"
                        name="collection-target"
                        checked={selectedId === collection.collection_id}
                        onChange={() => setSelectedId(collection.collection_id)}
                        aria-label={collection.name}
                      />
                      <span className="collections-dialog__row-body">
                        <span className="collections-dialog__row-title">{collection.name}</span>
                        <span className="collections-dialog__row-meta">
                          {memberCountLabel(collection.item_count, vi)}
                          {collection.tags.length > 0 ? ` · ${collection.tags.slice(0, 3).join(", ")}` : ""}
                        </span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="collections-dialog__footer collections-dialog__footer--stack">
            <div className="collections-dialog__create">
              <label className="collection-settings__label" htmlFor="collection-target-new">
                {vi ? "Hoặc tạo bộ sưu tập mới" : "Or create a new collection"}
              </label>
              <div className="collections-dialog__create-row">
                <input
                  id="collection-target-new"
                  className="console-input console-input--plain"
                  value={newName}
                  maxLength={200}
                  onChange={(event) => setNewName(event.target.value)}
                  placeholder={vi ? "Tên bộ sưu tập" : "Collection name"}
                />
                <button
                  type="button"
                  className="console-btn"
                  onClick={() => void handleCreateAndAdd()}
                  disabled={submitting || newName.trim().length === 0}
                >
                  <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                  {vi ? "Tạo và thêm" : "Create and add"}
                </button>
              </div>
            </div>
            <div className="collections-dialog__actions">
              <button type="button" className="console-btn" onClick={onClose} disabled={submitting}>
                {vi ? "Huỷ" : "Cancel"}
              </button>
              <button
                type="button"
                className="console-btn console-btn--primary"
                onClick={() => void handleAddToExisting()}
                disabled={submitting || !selectedId}
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                    {vi ? "Đang lưu…" : "Saving…"}
                  </>
                ) : (
                  vi ? "Lưu vào bộ sưu tập" : "Save to collection"
                )}
              </button>
            </div>
          </div>
        </>
      )}
    </ModalDialog>
  );
}
