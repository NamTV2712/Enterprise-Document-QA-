import { Loader2, StickyNote } from "lucide-react";

import type { CollectionNoteRecord } from "../../types";
import { formatAbsoluteDateTime } from "../../lib/collectionModel";
import type { CollectionFailure } from "../../lib/collectionModel";
import { CollectionActionMenu } from "./CollectionActionMenu";

interface CollectionNotesProps {
  vi: boolean;
  notes: CollectionNoteRecord[];
  total: number;
  loading: boolean;
  failure: CollectionFailure | null;
  draft: string;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  editingNoteId: string | null;
  editingText: string;
  onEditStart: (note: CollectionNoteRecord) => void;
  onEditChange: (value: string) => void;
  onEditCancel: () => void;
  onEditSubmit: () => void;
  onDelete: (note: CollectionNoteRecord) => void;
  pendingNoteId: string | null;
}

/**
 * The rail's Notes tab. A note is exactly its stored text plus the timestamps
 * the repository recorded: the model has no title, so none is invented.
 */
export function CollectionNotes({
  vi,
  notes,
  total,
  loading,
  failure,
  draft,
  onDraftChange,
  onSubmit,
  submitting,
  editingNoteId,
  editingText,
  onEditStart,
  onEditChange,
  onEditCancel,
  onEditSubmit,
  onDelete,
  pendingNoteId,
}: CollectionNotesProps) {
  return (
    <div className="collection-notes">
      <div className="collection-contents__heading">
        <h4 className="collection-contents__title">{vi ? `Ghi chú (${total})` : `Notes (${total})`}</h4>
      </div>

      <form
        className="collection-notes__form"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label className="collection-notes__label" htmlFor="collection-note-draft">
          {vi ? "Thêm ghi chú" : "Add note"}
        </label>
        <textarea
          id="collection-note-draft"
          className="collection-textarea"
          value={draft}
          rows={3}
          maxLength={10_000}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder={vi ? "Ghi chú cho bộ sưu tập này…" : "A note for this collection…"}
        />
        <div className="collection-notes__actions">
          <span className="collection-notes__count">{draft.length}/10000</span>
          <button type="submit" className="console-btn console-btn--primary" disabled={submitting || draft.trim().length === 0}>
            {submitting ? (vi ? "Đang lưu…" : "Saving…") : (vi ? "Lưu ghi chú" : "Save note")}
          </button>
        </div>
      </form>

      {loading && (
        <p className="collection-contents__status" role="status">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          {vi ? "Đang đọc ghi chú…" : "Reading notes…"}
        </p>
      )}

      {failure && !loading && (
        <div className="workspace-alert workspace-alert--error" role="alert">
          <strong>{failure.title}</strong>
          <p>{failure.message}</p>
        </div>
      )}

      {!loading && !failure && notes.length === 0 && (
        <div className="console-empty">
          <StickyNote aria-hidden="true" />
          <strong>{vi ? "Chưa có ghi chú" : "No notes yet"}</strong>
          <p>{vi ? "Ghi chú được lưu cùng bộ sưu tập và hiển thị lại khi mở." : "Notes are stored with the collection and reappear when you reopen it."}</p>
        </div>
      )}

      {notes.length > 0 && (
        <ul className="collection-notes__list" aria-label={vi ? "Ghi chú của bộ sưu tập" : "Collection notes"}>
          {notes.map((note) => {
            const editing = editingNoteId === note.note_id;
            const createdAt = formatAbsoluteDateTime(note.created_at, vi);
            const updatedAt = formatAbsoluteDateTime(note.updated_at, vi);
            return (
              <li key={note.note_id} className="collection-notes__item">
                {editing ? (
                  <form
                    className="collection-notes__edit"
                    onSubmit={(event) => {
                      event.preventDefault();
                      onEditSubmit();
                    }}
                  >
                    <label className="sr-only" htmlFor={`collection-note-edit-${note.note_id}`}>
                      {vi ? "Sửa ghi chú" : "Edit note"}
                    </label>
                    <textarea
                      id={`collection-note-edit-${note.note_id}`}
                      className="collection-textarea"
                      value={editingText}
                      rows={3}
                      maxLength={10_000}
                      onChange={(event) => onEditChange(event.target.value)}
                    />
                    <div className="collection-notes__actions">
                      <button type="button" className="console-btn" onClick={onEditCancel}>
                        {vi ? "Huỷ" : "Cancel"}
                      </button>
                      <button type="submit" className="console-btn console-btn--primary" disabled={editingText.trim().length === 0 || pendingNoteId === note.note_id}>
                        {pendingNoteId === note.note_id ? (vi ? "Đang lưu…" : "Saving…") : (vi ? "Lưu thay đổi" : "Save changes")}
                      </button>
                    </div>
                  </form>
                ) : (
                  <>
                    <p className="collection-notes__text">{note.text}</p>
                    <div className="collection-notes__meta">
                      <span>
                        {vi ? "Tạo" : "Created"} {createdAt ?? (vi ? "không rõ" : "unknown")}
                      </span>
                      {updatedAt && updatedAt !== createdAt && (
                        <span>
                          {vi ? "Sửa" : "Edited"} {updatedAt}
                        </span>
                      )}
                    </div>
                    <div className="collection-notes__item-actions">
                      <CollectionActionMenu
                        label={vi ? "Hành động cho ghi chú" : "Note actions"}
                        items={[
                          { key: "edit", label: vi ? "Sửa ghi chú" : "Edit note", onSelect: () => onEditStart(note) },
                          {
                            key: "delete",
                            label: pendingNoteId === note.note_id ? (vi ? "Đang xoá…" : "Deleting…") : (vi ? "Xoá ghi chú" : "Delete note"),
                            onSelect: () => onDelete(note),
                            danger: true,
                            disabled: pendingNoteId === note.note_id,
                          },
                        ]}
                      />
                    </div>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
