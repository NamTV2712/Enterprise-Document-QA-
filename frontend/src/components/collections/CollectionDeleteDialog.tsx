import { useRef } from "react";
import { Loader2, Trash2 } from "lucide-react";

import type { CollectionRecord } from "../../types";
import { ModalDialog } from "../ui/ModalDialog";

interface CollectionDeleteDialogProps {
  vi: boolean;
  collection: CollectionRecord | null;
  deleting: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

/** One confirmation surface for every collection-deletion entry point. */
export function CollectionDeleteDialog({
  vi,
  collection,
  deleting,
  errorMessage,
  onCancel,
  onConfirm,
}: CollectionDeleteDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  return (
    <ModalDialog
      open={collection !== null}
      onClose={() => {
        if (!deleting) onCancel();
      }}
      labelledBy="collection-delete-title"
      describedBy="collection-delete-description"
      initialFocusRef={cancelRef}
      className="collections-dialog w-full max-w-md overflow-hidden rounded-2xl border border-[var(--border-subtle)] surface-raised shadow-2xl"
    >
      <div className="collections-dialog__form">
        <h2 id="collection-delete-title" className="collections-dialog__title">
          {vi ? "Xoá bộ sưu tập?" : "Delete collection?"}
        </h2>
        <p id="collection-delete-description" className="collections-dialog__hint">
          {vi ? (
            <>
              Thao tác này sẽ xoá <strong>“{collection?.name}”</strong> cùng mọi mục và ghi chú. Định danh này không thể tạo lại.
            </>
          ) : (
            <>
              This will delete <strong>“{collection?.name}”</strong> with every member and note. This identity cannot be recreated.
            </>
          )}
        </p>
        {errorMessage && <p className="collections-dialog__error" role="alert">{errorMessage}</p>}
        <div className="collections-dialog__actions">
          <button ref={cancelRef} type="button" className="console-btn" onClick={onCancel} disabled={deleting}>
            {vi ? "Huỷ" : "Cancel"}
          </button>
          <button type="button" className="console-btn console-btn--danger" onClick={onConfirm} disabled={deleting}>
            {deleting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                {vi ? "Đang xoá…" : "Deleting…"}
              </>
            ) : (
              <>
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                {vi ? "Xoá vĩnh viễn" : "Delete permanently"}
              </>
            )}
          </button>
        </div>
      </div>
    </ModalDialog>
  );
}
