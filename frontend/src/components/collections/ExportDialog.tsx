import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import type { CollectionRecord } from "../../types";
import { ModalDialog } from "../ui/ModalDialog";

interface ExportDialogProps {
  open: boolean;
  vi: boolean;
  collection: CollectionRecord | null;
  exporting: boolean;
  errorMessage: string | null;
  onExport: (format: "json" | "markdown") => void;
  onClose: () => void;
}

/**
 * The reference's "Export" control. DATA-003 exports one collection as either
 * its JSON document or as Markdown; both are reads and neither mutates the
 * workspace, so nothing is written here.
 */
export function ExportDialog({ open, vi, collection, exporting, errorMessage, onExport, onClose }: ExportDialogProps) {
  const [format, setFormat] = useState<"json" | "markdown">("json");
  const firstRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) setFormat("json");
  }, [open]);

  return (
    <ModalDialog
      open={open}
      onClose={onClose}
      labelledBy="collection-export-title"
      initialFocusRef={firstRef}
      overlayClassName="items-center"
      className="collections-dialog w-full max-w-md overflow-hidden rounded-2xl border border-[var(--border-subtle)] surface-raised shadow-2xl"
    >
      <div className="collections-dialog__form">
        <h2 id="collection-export-title" className="collections-dialog__title">
          {vi ? "Xuất bộ sưu tập" : "Export collection"}
        </h2>
        <p className="collections-dialog__hint">
          {collection
            ? vi
              ? `Xuất “${collection.name}” ở bản sửa đổi ${collection.revision}. Việc xuất chỉ đọc dữ liệu.`
              : `Export “${collection.name}” at revision ${collection.revision}. Exporting only reads data.`
            : ""}
        </p>

        <fieldset className="collections-dialog__formats">
          <legend className="collection-settings__label">{vi ? "Định dạng" : "Format"}</legend>
          <label className="collection-settings__checkbox">
            <input
              ref={firstRef}
              type="radio"
              name="collection-export-format"
              checked={format === "json"}
              onChange={() => setFormat("json")}
            />
            <span>{vi ? "JSON (tài liệu đầy đủ của bộ sưu tập)" : "JSON (the full collection document)"}</span>
          </label>
          <label className="collection-settings__checkbox">
            <input
              type="radio"
              name="collection-export-format"
              checked={format === "markdown"}
              onChange={() => setFormat("markdown")}
            />
            <span>{vi ? "Markdown (bản đọc được)" : "Markdown (a readable rendering)"}</span>
          </label>
        </fieldset>

        {errorMessage && <p className="collections-dialog__error" role="alert">{errorMessage}</p>}

        <div className="collections-dialog__actions">
          <button type="button" className="console-btn" onClick={onClose} disabled={exporting}>
            {vi ? "Đóng" : "Close"}
          </button>
          <button
            type="button"
            className="console-btn console-btn--primary"
            onClick={() => onExport(format)}
            disabled={exporting || !collection}
          >
            {exporting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                {vi ? "Đang xuất…" : "Exporting…"}
              </>
            ) : (
              vi ? "Xuất tệp" : "Export file"
            )}
          </button>
        </div>
      </div>
    </ModalDialog>
  );
}
