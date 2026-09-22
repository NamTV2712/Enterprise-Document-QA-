import { ArrowRight, Clock, FileText, FolderOpen, Star } from "lucide-react";

import type { CollectionRecord } from "../../types";
import {
  collectionAccent,
  collectionSubtitle,
  memberCountLabel,
  visibleTags,
} from "../../lib/collectionModel";
import { CollectionActionMenu } from "./CollectionActionMenu";

interface CollectionCardProps {
  collection: CollectionRecord;
  selected: boolean;
  vi: boolean;
  /** Shared "now" so every card in one render agrees about relative time. */
  now: number;
  onOpen: () => void;
  onToggleFavorite: () => void;
  onAddDocuments: () => void;
  onExport: () => void;
  onRename: () => void;
  onDelete: () => void;
}

/** One typed collection as the reference's list row: real fields only. */
export function CollectionCard({
  collection,
  selected,
  vi,
  now,
  onOpen,
  onToggleFavorite,
  onAddDocuments,
  onExport,
  onRename,
  onDelete,
}: CollectionCardProps) {
  const { shown, hiddenCount } = visibleTags(collection.tags);
  const favoriteLabel = collection.favorite
    ? vi ? `Bỏ yêu thích ${collection.name}` : `Remove ${collection.name} from favorites`
    : vi ? `Đánh dấu yêu thích ${collection.name}` : `Mark ${collection.name} as favorite`;

  return (
    <article
      id={`collection-card-${collection.collection_id}`}
      className={`collection-card collection-card--accent-${collectionAccent(collection.collection_id)} ${selected ? "is-selected" : ""}`.trim()}
      aria-current={selected ? "true" : undefined}
    >
      <span className="collection-card__tile" aria-hidden="true">
        <FolderOpen />
      </span>
      <div className="collection-card__body">
        <div className="collection-card__top">
          <h3 className="collection-card__title">
            <button
              type="button"
              className="collection-card__title-button"
              onClick={onOpen}
              aria-label={vi ? `Mở ${collection.name}` : `Open ${collection.name}`}
            >
              {collection.name}
            </button>
            <button
              type="button"
              className="collection-card__star"
              aria-label={favoriteLabel}
              aria-pressed={collection.favorite}
              onClick={onToggleFavorite}
            >
              <Star className={collection.favorite ? "is-on" : ""} aria-hidden="true" />
            </button>
          </h3>
          <dl className="collection-card__meta">
            <div className="collection-card__meta-item">
              <dt className="sr-only">{vi ? "Số mục" : "Items"}</dt>
              <dd>
                <FileText className="collection-card__meta-icon" aria-hidden="true" />
                <span className="collection-card__meta-label">{memberCountLabel(collection.item_count, vi)}</span>
              </dd>
            </div>
            <div className="collection-card__meta-item">
              <dt className="sr-only">{vi ? "Cập nhật" : "Updated"}</dt>
              <dd>
                <Clock className="collection-card__meta-icon" aria-hidden="true" />
                <span className="collection-card__meta-label">{collectionSubtitle(collection, vi, now)}</span>
              </dd>
            </div>
          </dl>
          <CollectionActionMenu
            label={vi ? `Hành động cho ${collection.name}` : `Actions for ${collection.name}`}
            items={[
              { key: "rename", label: vi ? "Đổi tên" : "Rename", onSelect: onRename },
              { key: "delete", label: vi ? "Xoá bộ sưu tập" : "Delete collection", onSelect: onDelete, danger: true },
            ]}
          />
        </div>

        {collection.description.trim().length > 0 && (
          <p className="collection-card__description">{collection.description}</p>
        )}

        <div className="collection-card__footer">
          <ul className="collection-card__tags" aria-label={vi ? "Thẻ của bộ sưu tập" : "Collection tags"}>
            {shown.map((tag) => (
              <li key={tag} className="console-chip">{tag}</li>
            ))}
            {hiddenCount > 0 && <li className="console-chip collection-chip--more">+{hiddenCount}</li>}
          </ul>
          <div className="collection-card__actions">
            <button type="button" className="console-btn console-btn--primary" onClick={onOpen}>
              {vi ? "Mở" : "Open"}
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
            <button type="button" className="console-btn" onClick={onExport}>
              {vi ? "Xuất" : "Export"}
            </button>
            <button type="button" className="console-btn" onClick={onAddDocuments}>
              {vi ? "+ Thêm tài liệu" : "+ Add Documents"}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}
