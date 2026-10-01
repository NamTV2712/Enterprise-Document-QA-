import { useState } from "react";
import { Loader2, Save, Trash2 } from "lucide-react";

import type { CollectionRecord, CollectionUpdateRequest } from "../../types";
import type { CollectionFailure } from "../../lib/collectionModel";

interface CollectionSettingsProps {
  vi: boolean;
  collection: CollectionRecord;
  saving: boolean;
  /** A conflict or validation failure from the last write, if any. */
  failure: CollectionFailure | null;
  /** The revision the workspace currently holds; a mismatch is a conflict. */
  staleRevision: boolean;
  onReload: () => void;
  onSave: (patch: Omit<CollectionUpdateRequest, "revision">) => void;
  onDelete: () => void;
}

/**
 * The rail's Settings tab: the mutable collection fields DATA-003 defines, sent
 * with the revision the page last read so a stale view is refused as a
 * conflict rather than silently overwriting newer work.
 */
export function CollectionSettings({
  vi,
  collection,
  saving,
  failure,
  staleRevision,
  onReload,
  onSave,
  onDelete,
}: CollectionSettingsProps) {
  const [name, setName] = useState(collection.name);
  const [description, setDescription] = useState(collection.description);
  const [tags, setTags] = useState(collection.tags.join(", "));
  const [privateFlag, setPrivateFlag] = useState(collection.private);
  const [favorite, setFavorite] = useState(collection.favorite);

  const parsedTags = tags
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0)
    .slice(0, 20);

  const dirty =
    name !== collection.name ||
    description !== collection.description ||
    parsedTags.join("\u0000") !== collection.tags.join("\u0000") ||
    privateFlag !== collection.private ||
    favorite !== collection.favorite;

  return (
    <div className="collection-settings">
      <div className="collection-contents__heading">
        <h4 className="collection-contents__title">{vi ? "Thiết lập bộ sưu tập" : "Collection settings"}</h4>
      </div>

      {failure && (
        <div className={`workspace-alert ${failure.kind === "conflict" ? "collection-alert--conflict" : "workspace-alert--error"}`} role="alert">
          <strong>{failure.title}</strong>
          <p>{failure.message}</p>
          {failure.kind === "conflict" && (
            <button type="button" className="console-btn" onClick={onReload}>
              {vi ? "Tải lại bộ sưu tập" : "Reload collection"}
            </button>
          )}
        </div>
      )}

      {(staleRevision || failure?.kind === "conflict") && (
        <p className="collection-settings__stale" role="status">
          {vi
            ? "Bản sửa đổi đang xem đã cũ so với workspace. Tải lại trước khi lưu thay đổi."
            : "The revision you are viewing is older than the workspace. Reload before saving."}
        </p>
      )}

      <form
        className="collection-settings__form"
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim().length === 0) return;
          onSave({
            name: name.trim(),
            description,
            tags: parsedTags,
            private: privateFlag,
            favorite,
          });
        }}
      >
        <label className="collection-settings__field">
          <span className="collection-settings__label">{vi ? "Tên" : "Name"}</span>
          <input
            className="console-input console-input--plain"
            value={name}
            maxLength={200}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </label>

        <label className="collection-settings__field">
          <span className="collection-settings__label">{vi ? "Mô tả" : "Description"}</span>
          <textarea
            className="collection-textarea"
            value={description}
            rows={3}
            maxLength={2_000}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>

        <label className="collection-settings__field">
          <span className="collection-settings__label">{vi ? "Thẻ (phân tách bằng dấu phẩy, tối đa 20)" : "Tags (comma separated, up to 20)"}</span>
          <input
            className="console-input console-input--plain"
            value={tags}
            onChange={(event) => setTags(event.target.value)}
          />
        </label>

        <label className="collection-settings__checkbox">
          <input
            type="checkbox"
            checked={privateFlag}
            onChange={(event) => setPrivateFlag(event.target.checked)}
          />
          <span>{vi ? "Riêng tư trong workspace cục bộ" : "Private to the local workspace"}</span>
        </label>

        <label className="collection-settings__checkbox">
          <input
            type="checkbox"
            checked={favorite}
            onChange={(event) => setFavorite(event.target.checked)}
          />
          <span>{vi ? "Đánh dấu yêu thích" : "Mark as favorite"}</span>
        </label>

        <p className="collection-settings__revision">
          {vi ? `Bản sửa đổi hiện tại: ${collection.revision}` : `Current revision: ${collection.revision}`}
        </p>

        <div className="collection-settings__actions">
          <button type="submit" className="console-btn console-btn--primary" disabled={saving || !dirty}>
            {saving ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                {vi ? "Đang lưu…" : "Saving…"}
              </>
            ) : (
              <>
                <Save className="h-3.5 w-3.5" aria-hidden="true" />
                {vi ? "Lưu thay đổi" : "Save changes"}
              </>
            )}
          </button>
        </div>
      </form>

      <div className="collection-settings__danger">
        <h5>{vi ? "Xoá bộ sưu tập" : "Delete collection"}</h5>
        <p>
          {vi
            ? "Xoá sẽ tạo tombstone cho bộ sưu tập cùng mọi mục và ghi chú bên trong; định danh này không thể tạo lại."
            : "Deleting tombstones the collection with every member and note it holds; the identity cannot be recreated."}
        </p>
        <button type="button" className="console-btn console-btn--danger" onClick={onDelete}>
          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          {vi ? "Xoá bộ sưu tập" : "Delete collection"}
        </button>
      </div>
    </div>
  );
}
