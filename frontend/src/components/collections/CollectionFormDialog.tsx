import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import type { CollectionCreateRequest, CollectionRecord } from "../../types";
import { ModalDialog } from "../ui/ModalDialog";

interface CollectionFormDialogProps {
  open: boolean;
  vi: boolean;
  mode: "create" | "rename";
  /** The collection being renamed; unused when creating. */
  collection?: CollectionRecord | null;
  submitting: boolean;
  errorMessage: string | null;
  onSubmit: (values: CollectionCreateRequest) => void;
  onClose: () => void;
}

/**
 * Create one collection, or rename an existing one. Only fields DATA-003
 * accepts are collected here, and a create uses the identity the repository
 * returns rather than a client-side one.
 */
export function CollectionFormDialog({
  open,
  vi,
  mode,
  collection,
  submitting,
  errorMessage,
  onSubmit,
  onClose,
}: CollectionFormDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setName(mode === "rename" ? collection?.name ?? "" : "");
    setDescription(mode === "create" ? "" : collection?.description ?? "");
    setTags(mode === "create" ? "" : (collection?.tags ?? []).join(", "));
  }, [collection, mode, open]);

  const parsedTags = tags
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0)
    .slice(0, 20);

  const title = mode === "create"
    ? vi ? "Bộ sưu tập mới" : "New collection"
    : vi ? "Đổi tên bộ sưu tập" : "Rename collection";

  return (
    <ModalDialog
      open={open}
      onClose={onClose}
      labelledBy="collection-form-title"
      initialFocusRef={nameRef}
      overlayClassName="items-center"
      className="collections-dialog w-full max-w-lg overflow-hidden rounded-2xl border border-[var(--border-subtle)] surface-raised shadow-2xl"
    >
      <form
        className="collections-dialog__form"
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim().length === 0) return;
          onSubmit(
            mode === "create"
              ? { name: name.trim(), description, tags: parsedTags }
              : { name: name.trim() },
          );
        }}
      >
        <h2 id="collection-form-title" className="collections-dialog__title">{title}</h2>
        <p className="collections-dialog__hint">
          {vi
            ? "Bộ sưu tập được lưu trong workspace cục bộ với định danh do repository cấp."
            : "The collection is stored in the local workspace with the identity the repository assigns."}
        </p>

        <label className="collection-settings__field">
          <span className="collection-settings__label">{vi ? "Tên" : "Name"}</span>
          <input
            ref={nameRef}
            className="console-input console-input--plain"
            value={name}
            maxLength={200}
            required
            onChange={(event) => setName(event.target.value)}
          />
        </label>

        {mode === "create" && (
          <>
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
              <span className="collection-settings__label">{vi ? "Thẻ (phân tách bằng dấu phẩy)" : "Tags (comma separated)"}</span>
              <input
                className="console-input console-input--plain"
                value={tags}
                onChange={(event) => setTags(event.target.value)}
              />
            </label>
          </>
        )}

        {errorMessage && (
          <p className="collections-dialog__error" role="alert">{errorMessage}</p>
        )}

        <div className="collections-dialog__actions">
          <button type="button" className="console-btn" onClick={onClose} disabled={submitting}>
            {vi ? "Huỷ" : "Cancel"}
          </button>
          <button type="submit" className="console-btn console-btn--primary" disabled={submitting || name.trim().length === 0}>
            {submitting
              ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  {vi ? "Đang lưu…" : "Saving…"}
                </>
              )
              : mode === "create"
                ? vi ? "Tạo bộ sưu tập" : "Create collection"
                : vi ? "Lưu tên mới" : "Save name"}
          </button>
        </div>
      </form>
    </ModalDialog>
  );
}
