import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, Loader2, Search } from "lucide-react";

import { addCollectionItem, getDocuments } from "../../lib/api";
import type { DocumentRow } from "../../types";
import {
  describeCollectionFailure,
  documentReference,
} from "../../lib/collectionModel";
import type { CollectionFailure } from "../../lib/collectionModel";
import { formatCompanyLabel } from "../../lib/displayMetadata";
import { ModalDialog } from "../ui/ModalDialog";

interface AddItemsDialogProps {
  open: boolean;
  vi: boolean;
  collectionId: string;
  collectionName: string;
  onClose: () => void;
  /** Called once per committed member so the rail can refresh its own view. */
  onAdded: (count: number) => void;
}

const PAGE_SIZE = 20;

/**
 * "+ Add Documents": the picker promised by the gap matrix, sourced from the
 * real API-003 catalog. Each selection becomes a `document` member carrying the
 * canonical `document_id`; DATA-003 remains the authority that accepts or
 * refuses the reference.
 */
export function AddItemsDialog({ open, vi, collectionId, collectionName, onClose, onAdded }: AddItemsDialogProps) {
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<DocumentRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState<CollectionFailure | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);
  const [addedCount, setAddedCount] = useState(0);
  const searchRef = useRef<HTMLInputElement>(null);
  const epoch = useRef(0);
  const controller = useRef<AbortController | null>(null);

  const load = useCallback(
    async (nextPage: number, nextSearch: string) => {
      const current = ++epoch.current;
      controller.current?.abort();
      const abort = new AbortController();
      controller.current = abort;
      setLoading(true);
      setFailure(null);
      try {
        const response = await getDocuments(
          { search: nextSearch || undefined, page: nextPage, page_size: PAGE_SIZE, sort: "filing_date", direction: "desc" },
          abort.signal,
        );
        if (epoch.current !== current) return;
        setRows(response.items);
        setTotal(response.total);
      } catch (error) {
        if (epoch.current !== current) return;
        if ((error as { name?: string })?.name === "AbortError") return;
        setRows([]);
        setTotal(0);
        setFailure(describeCollectionFailure(error, vi));
      } finally {
        if (epoch.current === current) setLoading(false);
      }
    },
    [vi],
  );

  useEffect(() => {
    if (!open) return;
    setSearch("");
    setSelected([]);
    setAddedCount(0);
    setFailure(null);
    setPage(1);
    void load(1, "");
  }, [open, load]);

  useEffect(
    () => () => {
      controller.current?.abort();
    },
    [],
  );

  const documentTitle = (row: DocumentRow) =>
    `${row.ticker ? formatCompanyLabel(row.ticker) : vi ? "Hồ sơ SEC" : "SEC filing"} · ${row.filing_date ?? (vi ? "không rõ ngày" : "date unavailable")}`;

  const toggle = (documentId: string) => {
    setSelected((current) =>
      current.includes(documentId) ? current.filter((entry) => entry !== documentId) : [...current, documentId],
    );
  };

  const chosen = useMemo(
    () => rows.filter((row) => selected.includes(row.document_id)),
    [rows, selected],
  );

  const handleAdd = async () => {
    if (chosen.length === 0 || adding) return;
    setAdding(true);
    setFailure(null);
    let added = 0;
    try {
      for (const row of chosen) {
        await addCollectionItem(collectionId, {
          item_kind: "document",
          citation: documentTitle(row),
          excerpt: "",
          reference: documentReference(row.document_id, {
            ticker: row.ticker,
            filingDate: row.filing_date,
            reportDate: row.report_date,
            accessionNumber: row.accession_number,
            sourceUrl: row.source_url,
          }),
          snapshot: {
            document_id: row.document_id,
            ticker: row.ticker ?? "",
            filing_date: row.filing_date ?? "",
            sections: row.sections,
          },
        });
        added += 1;
        setAddedCount(added);
      }
      setSelected([]);
      onAdded(added);
      onClose();
    } catch (error) {
      setFailure(describeCollectionFailure(error, vi));
      if (added > 0) onAdded(added);
    } finally {
      setAdding(false);
    }
  };

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <ModalDialog
      open={open}
      onClose={onClose}
      labelledBy="collection-add-items-title"
      describedBy="collection-add-items-hint"
      initialFocusRef={searchRef}
      overlayClassName="items-start pt-[10vh]"
      className="collections-dialog w-full max-w-2xl overflow-hidden rounded-2xl border border-[var(--border-subtle)] surface-raised shadow-2xl"
    >
      <div className="collections-dialog__header">
        <div>
          <h2 id="collection-add-items-title" className="collections-dialog__title">
            {vi ? "Thêm tài liệu vào bộ sưu tập" : "Add documents to the collection"}
          </h2>
          <p id="collection-add-items-hint" className="collections-dialog__hint">
            {vi
              ? `Mục được thêm vào “${collectionName}” với document_id chuẩn từ corpus.`
              : `Members are added to “${collectionName}” with the canonical corpus document_id.`}
          </p>
        </div>
      </div>

      <div className="collections-dialog__search console-input-row">
        <Search aria-hidden="true" />
        <input
          ref={searchRef}
          className="console-input"
          type="search"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
            void load(1, event.target.value);
          }}
          placeholder={vi ? "Tìm tài liệu trong corpus…" : "Search the corpus…"}
          aria-label={vi ? "Tìm tài liệu" : "Search documents"}
        />
      </div>

      {failure && (
        <div className="workspace-alert workspace-alert--error" role="alert">
          <strong>{failure.title}</strong>
          <p>{failure.message}</p>
        </div>
      )}

      <div className="collections-dialog__body">
        {loading && (
          <p className="collection-contents__status" role="status">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            {vi ? "Đang đọc corpus…" : "Reading the corpus…"}
          </p>
        )}
        {!loading && rows.length === 0 && !failure && (
          <p className="collections-dialog__empty">
            {vi ? "Không có tài liệu nào khớp tìm kiếm." : "No indexed document matches this search."}
          </p>
        )}
        {rows.length > 0 && (
          <ul className="collections-dialog__list" aria-label={vi ? "Tài liệu đã index" : "Indexed documents"}>
            {rows.map((row) => {
              const checked = selected.includes(row.document_id);
              return (
                <li key={row.document_id}>
                  <label className="collections-dialog__row">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(row.document_id)}
                      aria-label={documentTitle(row)}
                    />
                    <span className="collections-dialog__mark" aria-hidden="true">{checked && <Check className="h-3 w-3" />}</span>
                    <span className="collections-dialog__row-body">
                      <span className="collections-dialog__row-title">{documentTitle(row)}</span>
                      <span className="collections-dialog__row-meta">
                        {row.sections.slice(0, 3).join(" · ") || (vi ? "Không có mục nào được index" : "No indexed sections")}
                        {row.chunk_count > 0 ? ` · ${row.chunk_count} ${vi ? "đoạn" : "chunks"}` : ""}
                      </span>
                      <span className="collections-dialog__row-id">{row.document_id}</span>
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="collections-dialog__footer">
        <span className="collections-dialog__count">
          {vi
            ? `${selected.length} đã chọn · ${total} tài liệu đã index`
            : `${selected.length} selected · ${total} indexed documents`}
        </span>
        <div className="collections-dialog__pager">
          <button
            type="button"
            className="console-btn"
            disabled={page <= 1 || loading}
            onClick={() => {
              const next = page - 1;
              setPage(next);
              void load(next, search);
            }}
          >
            {vi ? "Trước" : "Previous"}
          </button>
          <span aria-live="polite">
            {page}/{pageCount}
          </span>
          <button
            type="button"
            className="console-btn"
            disabled={page >= pageCount || loading}
            onClick={() => {
              const next = page + 1;
              setPage(next);
              void load(next, search);
            }}
          >
            {vi ? "Sau" : "Next"}
          </button>
        </div>
        <div className="collections-dialog__actions">
          <button type="button" className="console-btn" onClick={onClose} disabled={adding}>
            {vi ? "Huỷ" : "Cancel"}
          </button>
          <button
            type="button"
            className="console-btn console-btn--primary"
            onClick={() => void handleAdd()}
            disabled={adding || selected.length === 0}
          >
            {adding
              ? vi
                ? `Đang thêm ${addedCount}/${selected.length}…`
                : `Adding ${addedCount}/${selected.length}…`
              : vi
                ? `Thêm ${selected.length} tài liệu`
                : `Add ${selected.length} document${selected.length === 1 ? "" : "s"}`}
          </button>
        </div>
      </div>
    </ModalDialog>
  );
}
