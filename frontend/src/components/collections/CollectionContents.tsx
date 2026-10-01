import { FileSearch, FolderOpen, Loader2 } from "lucide-react";

import type { CollectionItemKind, CollectionItemRecord } from "../../types";
import {
  COLLECTION_ITEM_KINDS,
  collectionItemKindLabel,
  formatAbsoluteDate,
  itemProvenanceLine,
  itemCeilingNote,
} from "../../lib/collectionModel";
import type { CollectionFailure } from "../../lib/collectionModel";
import { CollectionActionMenu } from "./CollectionActionMenu";
import { CollectionTypeBadge } from "./CollectionTypeBadge";

interface CollectionContentsProps {
  vi: boolean;
  items: CollectionItemRecord[];
  total: number;
  loading: boolean;
  failure: CollectionFailure | null;
  kindFilter: CollectionItemKind | null;
  onKindFilterChange: (kind: CollectionItemKind | null) => void;
  onAddDocuments: () => void;
  onOpenItem: (item: CollectionItemRecord) => void;
  onRemoveItem: (item: CollectionItemRecord) => void;
  pendingItemId: string | null;
  focusIdFor: (itemId: string) => string;
}

/**
 * The rail's Contents tab: the typed members DATA-003 returns, each opened
 * through its own canonical identity. A member that cannot be opened says so
 * instead of pretending.
 */
export function CollectionContents({
  vi,
  items,
  total,
  loading,
  failure,
  kindFilter,
  onKindFilterChange,
  onAddDocuments,
  onOpenItem,
  onRemoveItem,
  pendingItemId,
  focusIdFor,
}: CollectionContentsProps) {
  const ceilingNote = itemCeilingNote(items.length, total, vi);

  return (
    <div className="collection-contents">
      <div className="collection-contents__heading">
        <h4 className="collection-contents__title">{vi ? `Mục (${total})` : `Items (${total})`}</h4>
        <button type="button" className="console-btn" onClick={onAddDocuments}>
          {vi ? "+ Thêm tài liệu" : "+ Add Documents"}
        </button>
      </div>

      <div className="collection-contents__filters" role="group" aria-label={vi ? "Lọc theo loại mục" : "Filter by member kind"}>
        <button
          type="button"
          className="console-chip console-chip--toggle"
          aria-pressed={kindFilter === null}
          onClick={() => onKindFilterChange(null)}
        >
          {vi ? "Tất cả" : "All"}
        </button>
        {COLLECTION_ITEM_KINDS.map((kind) => (
          <button
            key={kind}
            type="button"
            className="console-chip console-chip--toggle"
            aria-pressed={kindFilter === kind}
            onClick={() => onKindFilterChange(kindFilter === kind ? null : kind)}
          >
            {collectionItemKindLabel(kind, vi)}
          </button>
        ))}
      </div>

      {loading && (
        <p className="collection-contents__status" role="status">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          {vi ? "Đang đọc các mục…" : "Reading items…"}
        </p>
      )}

      {failure && !loading && (
        <div className="workspace-alert workspace-alert--error" role="alert">
          <strong>{failure.title}</strong>
          <p>{failure.message}</p>
        </div>
      )}

      {!loading && !failure && items.length === 0 && (
        <div className="console-empty">
          <FolderOpen aria-hidden="true" />
          <strong>{vi ? "Chưa có mục nào" : "No items yet"}</strong>
          <p>
            {kindFilter
              ? vi ? "Không có mục nào thuộc loại này trong bộ sưu tập." : "This collection holds no member of that kind."
              : vi ? "Thêm tài liệu từ corpus hoặc lưu bằng chứng từ Search/Retrieval." : "Add corpus documents, or save evidence from Search/Retrieval."}
          </p>
        </div>
      )}

      {items.length > 0 && (
        <ul className="collection-items" aria-label={vi ? "Các mục của bộ sưu tập" : "Collection items"}>
          {items.map((item) => {
            const provenance = itemProvenanceLine(item, vi);
            // Never restate the citation as its own provenance line.
            const showProvenance = provenance.length > 0 && !item.citation.includes(provenance);
            const created = formatAbsoluteDate(item.created_at, vi);
            const removing = pendingItemId === item.item_id;
            return (
              <li key={item.item_id} className="collection-items__row">
                <CollectionTypeBadge kind={item.item_kind} vi={vi} tone={item.item_kind === "document" ? "document" : "neutral"} />
                <button
                  type="button"
                  id={focusIdFor(item.item_id)}
                  className="collection-items__open"
                  onClick={() => onOpenItem(item)}
                >
                  <span className="collection-items__citation">{item.citation || item.item_id}</span>
                  {showProvenance && <span className="collection-items__provenance">{provenance}</span>}
                  {item.excerpt.trim().length > 0 && (
                    <span className="collection-items__excerpt">{item.excerpt}</span>
                  )}
                </button>
                {created && <span className="collection-items__date">{created}</span>}
                <CollectionActionMenu
                  label={vi ? `Hành động cho ${item.citation || item.item_id}` : `Actions for ${item.citation || item.item_id}`}
                  items={[
                    { key: "open", label: vi ? "Mở nguồn" : "Open source", onSelect: () => onOpenItem(item) },
                    {
                      key: "remove",
                      label: removing ? (vi ? "Đang xoá…" : "Removing…") : (vi ? "Xoá khỏi bộ sưu tập" : "Remove from collection"),
                      onSelect: () => onRemoveItem(item),
                      danger: true,
                      disabled: removing,
                    },
                  ]}
                />
              </li>
            );
          })}
        </ul>
      )}

      {ceilingNote && <p className="collection-contents__note">{ceilingNote}</p>}
      {!ceilingNote && total > 0 && (
        <p className="collection-contents__note">
          <FileSearch className="h-3.5 w-3.5" aria-hidden="true" />
          {vi
            ? "Mở một mục để đọc nguồn gốc; mục được mở bằng định danh đã lưu, không chạy lại truy xuất."
            : "Open a member to read its origin; members open by their stored identity, without re-running retrieval."}
        </p>
      )}
    </div>
  );
}
