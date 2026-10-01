/**
 * UI-008 collection model.
 *
 * Every derivation the Collections workspace needs lives here so the page
 * components stay presentational: status mapping, labels, relative time, the
 * typed reference builders and the open-each-member handoff. Nothing in this
 * module invents a collection field, a member kind or a revision — DATA-003
 * responses are the only source of collection truth, and an unavailable
 * identity is reported as unavailable rather than guessed.
 */

import type {
  CollectionActivityEvent,
  CollectionExportFormat,
  CollectionItemKind,
  CollectionItemRecord,
  CollectionRecord,
  ReaderCoverageStatus,
  Source,
} from "../types";
import { SECTION_METADATA, formatCompanyLabel } from "./displayMetadata";

/** The four member kinds DATA-003 defines; there is no fifth. */
export const COLLECTION_ITEM_KINDS: readonly CollectionItemKind[] = ["document", "evidence", "answer", "note"] as const;

/** The accent tile for a collection card is presentation, derived from its id. */
const COLLECTION_ACCENTS = 6;

export type CollectionFailureKind =
  | "unavailable"
  | "auth_required"
  | "restricted"
  | "not_found"
  | "gone"
  | "conflict"
  | "validation"
  | "rate_limited"
  | "server"
  | "offline"
  | "unknown";

export interface CollectionFailure {
  kind: CollectionFailureKind;
  /** Short localized headline for the state. */
  title: string;
  /** One truthful sentence describing what happened and what to do. */
  message: string;
  /** The bounded server detail, when the API supplied one (never a secret). */
  detail: string | null;
  status: number | null;
}

/**
 * Read a status and a bounded detail off whatever the client threw. The model
 * deliberately duck-types instead of narrowing on the API class, so a failure
 * surfaced by a test double, a wrapper or a transport error still maps to the
 * same state.
 */
function failureLike(error: unknown): { status: number | null; detail: string | null } {
  if (!error || typeof error !== "object") return { status: null, detail: null };
  const status = (error as { status?: unknown }).status;
  const message = (error as { message?: unknown }).message;
  return {
    status: typeof status === "number" ? status : null,
    detail: typeof message === "string" && message.length > 0 ? message : null,
  };
}

/**
 * Map a collections request failure onto the exact state it represents.
 * A 404 here is the API-001 local-workspace boundary answering, a 410 is a
 * tombstone, a 409 a stale revision and a 422 a refused bound, kind or
 * reference. They are never collapsed into "not found".
 */
export function describeCollectionFailure(error: unknown, vi: boolean): CollectionFailure {
  const { status, detail } = failureLike(error);
  const base = { detail, status };
  switch (status) {
    case 401:
      return {
        ...base,
        kind: "auth_required",
        title: vi ? "Cần quyền truy cập cục bộ" : "Local workspace access required",
        message: vi
          ? "Bộ sưu tập là dữ liệu riêng của workspace cục bộ và API yêu cầu token truy cập cục bộ mà bản dựng này không lưu."
          : "Collections are private local-workspace data, and the API requires a local access token that this build deliberately does not hold.",
      };
    case 403:
      return {
        ...base,
        kind: "restricted",
        title: vi ? "Chỉ truy cập được từ máy này" : "Available from this machine only",
        message: vi
          ? "Workspace cục bộ chỉ phục vụ client loopback với Host/Origin được cho phép."
          : "The local workspace only serves loopback clients with an allowed Host and Origin.",
      };
    case 404:
      return {
        ...base,
        kind: "not_found",
        title: vi ? "Không tìm thấy bộ sưu tập" : "Collection not found",
        message: vi
          ? "Bộ sưu tập này không tồn tại trong workspace cục bộ."
          : "This collection does not exist in the local workspace.",
      };
    case 410:
      return {
        ...base,
        kind: "gone",
        title: vi ? "Bộ sưu tập đã bị xoá" : "Collection deleted",
        message: vi
          ? "Bộ sưu tập này đã bị xoá và không thể tạo lại dưới cùng định danh."
          : "This collection was deleted and cannot be recreated under the same identity.",
      };
    case 409:
      return {
        ...base,
        kind: "conflict",
        title: vi ? "Bộ sưu tập đã thay đổi ở nơi khác" : "Collection changed elsewhere",
        message: vi
          ? "Bản sửa đổi bạn đang xem đã cũ. Tải lại bộ sưu tập rồi thực hiện lại thay đổi."
          : "The revision you are viewing is stale. Reload the collection and make the change again.",
      };
    case 422:
      return {
        ...base,
        kind: "validation",
        title: vi ? "Yêu cầu không hợp lệ" : "Request refused",
        message: vi
          ? "API đã từ chối yêu cầu này vì vi phạm giới hạn, loại mục hoặc tham chiếu."
          : "The API refused this request over a bound, a member kind or a reference.",
      };
    case 429:
      return {
        ...base,
        kind: "rate_limited",
        title: vi ? "Tạm thời bị giới hạn" : "Temporarily rate limited",
        message: vi ? "Hãy thử lại sau giây lát." : "Try again in a moment.",
      };
    default:
      break;
  }
  if (status !== null && status >= 500) {
    return {
      ...base,
      kind: "server",
      title: vi ? "Workspace trả lỗi" : "Workspace error",
      message: vi ? "API cục bộ gặp lỗi khi xử lý yêu cầu này." : "The local API failed while handling this request.",
    };
  }
  if (status !== null) {
    return {
      ...base,
      kind: "unknown",
      title: vi ? "Không thể hoàn tất" : "Could not complete",
      message: vi ? "Yêu cầu bộ sưu tập không thành công." : "The collection request did not succeed.",
    };
  }
  return {
    ...base,
    kind: "offline",
    title: vi ? "Không kết nối được API" : "API unreachable",
    message: vi
      ? "Không thể kết nối tới API cục bộ, nên bộ sưu tập chưa được đọc."
      : "The local API could not be reached, so collections were not read.",
  };
}

/**
 * A list request that failed at the workspace boundary is a page-level
 * availability state, not an empty workspace: the page must say which one it is.
 */
export function isWorkspaceAvailabilityFailure(failure: CollectionFailure): boolean {
  return failure.kind === "unavailable" || failure.kind === "auth_required" || failure.kind === "restricted";
}

/** A 404 on the list route is the boundary hiding the capability in this mode. */
export function listUnavailableFailure(vi: boolean): CollectionFailure {
  return {
    kind: "unavailable",
    status: 404,
    detail: null,
    title: vi ? "Bộ sưu tập không khả dụng ở chế độ này" : "Collections are unavailable in this mode",
    message: vi
      ? "Bộ sưu tập thuộc workspace cục bộ riêng tư; chế độ triển khai hiện tại không phục vụ chúng."
      : "Collections belong to the private local workspace, and this deployment mode does not serve them.",
  };
}

export function collectionItemKindLabel(kind: CollectionItemKind | string, vi: boolean): string {
  switch (kind) {
    case "document":
      return vi ? "Tài liệu" : "Document";
    case "evidence":
      return vi ? "Bằng chứng" : "Evidence";
    case "answer":
      return vi ? "Câu trả lời" : "Answer";
    case "note":
      return vi ? "Ghi chú" : "Note";
    default:
      return String(kind);
  }
}

export function activityEventLabel(event: CollectionActivityEvent | string, vi: boolean): string {
  switch (event) {
    case "collection_created":
      return vi ? "Đã tạo bộ sưu tập" : "Collection created";
    case "collection_updated":
      return vi ? "Đã cập nhật thông tin bộ sưu tập" : "Collection details updated";
    case "collection_deleted":
      return vi ? "Đã xoá bộ sưu tập" : "Collection deleted";
    case "item_added":
      return vi ? "Đã thêm mục" : "Item added";
    case "item_removed":
      return vi ? "Đã xoá mục" : "Item removed";
    case "note_added":
      return vi ? "Đã thêm ghi chú" : "Note added";
    case "note_updated":
      return vi ? "Đã sửa ghi chú" : "Note updated";
    case "note_removed":
      return vi ? "Đã xoá ghi chú" : "Note removed";
    default:
      return String(event);
  }
}

export function memberCountLabel(count: number, vi: boolean): string {
  if (vi) return `${count} mục`;
  return count === 1 ? "1 item" : `${count} items`;
}

export function tagOverflowLabel(hiddenCount: number, vi: boolean): string {
  return vi ? `+${hiddenCount}` : `+${hiddenCount}`;
}

/** At most `limit` tag chips render as chips; the rest collapse into "+N". */
export function visibleTags(tags: readonly string[], limit = 3): { shown: string[]; hiddenCount: number } {
  const clean = tags.filter((tag) => tag.trim().length > 0);
  return { shown: clean.slice(0, limit), hiddenCount: Math.max(0, clean.length - limit) };
}

export function collectionAccent(collectionId: string): number {
  let hash = 0;
  for (const char of collectionId) hash = (hash * 31 + char.charCodeAt(0)) % 9973;
  return hash % COLLECTION_ACCENTS;
}

function toDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * A stored timestamp rendered relative while it is recent, and as an absolute
 * date after that. Returns null when the API reported no timestamp at all, so
 * the caller can print an honest "not reported" instead of "just now".
 */
export function formatRelativeTime(value: string | null | undefined, vi: boolean, now: number = Date.now()): string | null {
  const date = toDate(value);
  if (!date) return null;
  const deltaMinutes = Math.round((now - date.getTime()) / 60_000);
  if (deltaMinutes < 0) return formatAbsoluteDate(value, vi);
  if (deltaMinutes < 1) return vi ? "vừa xong" : "just now";
  if (deltaMinutes < 60) return vi ? `${deltaMinutes} phút trước` : `${deltaMinutes} minutes ago`;
  const deltaHours = Math.round(deltaMinutes / 60);
  if (deltaHours < 24) return vi ? `${deltaHours} giờ trước` : `${deltaHours} hours ago`;
  const deltaDays = Math.round(deltaHours / 24);
  if (deltaDays < 30) return vi ? `${deltaDays} ngày trước` : `${deltaDays} days ago`;
  return formatAbsoluteDate(value, vi);
}

export function formatAbsoluteDate(value: string | null | undefined, vi: boolean): string | null {
  const date = toDate(value);
  if (!date) return null;
  return date.toLocaleDateString(vi ? "vi-VN" : "en-US", { day: "numeric", month: "short", year: "numeric" });
}

export function formatAbsoluteDateTime(value: string | null | undefined, vi: boolean): string | null {
  const date = toDate(value);
  if (!date) return null;
  return date.toLocaleString(vi ? "vi-VN" : "en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** The card's meta line keeps only identities the workspace can actually name. */
export function collectionSubtitle(collection: CollectionRecord, vi: boolean, now: number = Date.now()): string {
  const updated = formatRelativeTime(collection.updated_at, vi, now);
  if (!updated) return vi ? "Chưa ghi nhận thời điểm cập nhật" : "No update time recorded";
  return vi ? `Cập nhật ${updated}` : `Updated ${updated}`;
}

export function privacySummary(privateFlag: boolean, vi: boolean): { label: string; detail: string } {
  if (privateFlag) {
    return { label: vi ? "Riêng tư" : "Private", detail: vi ? "Chỉ trong workspace cục bộ" : "Local workspace only" };
  }
  return { label: vi ? "Không đặt riêng tư" : "Not private", detail: vi ? "Cờ riêng tư đang tắt" : "The private flag is off" };
}

/* ------------------------------------------------------------------ *
 * Member references.
 *
 * These builders only copy fields the item actually carries, so a member
 * always satisfies the DATA-003 membership rule for its kind or is refused
 * by the API instead of being coerced into another kind.
 * ------------------------------------------------------------------ */

function referenceString(reference: Record<string, unknown>, key: string): string | null {
  const value = reference[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

/** The evidence reference for a retrieved source: only its real identities. */
export function evidenceReferenceFromSource(source: Source): Record<string, unknown> {
  const reference: Record<string, unknown> = {};
  const copy = (key: string, value: unknown) => {
    if (typeof value === "string" && value.length > 0) reference[key] = value;
  };
  copy("document_id", source.document_id);
  copy("chunk_id", source.chunk_id);
  copy("ticker", source.ticker);
  copy("section", source.section);
  copy("filing_date", source.filing_date);
  copy("report_date", source.report_date);
  copy("source_url", source.source_url);
  copy("sec_index_url", source.sec_index_url);
  const snapshot = source.stored_snapshot;
  if (snapshot) {
    copy("document_revision", snapshot.document_revision);
    copy("source_set_revision", snapshot.source_set_revision);
    copy("representation", snapshot.representation);
    copy("coverage_status", snapshot.coverage_status);
    copy("location_status", snapshot.location_status);
    if (snapshot.chunk_id && !reference.chunk_id) reference.chunk_id = snapshot.chunk_id;
  }
  copy("chunk_text_hash", source.chunk_text_hash);
  return reference;
}

export function snapshotFromSource(source: Source): Record<string, unknown> | null {
  const snapshot: Record<string, unknown> = {};
  const copy = (key: string, value: unknown) => {
    if (typeof value === "string" && value.length > 0) snapshot[key] = value;
  };
  copy("ticker", source.ticker);
  copy("section", source.section);
  copy("filing_date", source.filing_date);
  copy("report_date", source.report_date);
  copy("document_id", source.document_id);
  copy("chunk_id", source.chunk_id);
  copy("source_url", source.source_url);
  copy("sec_index_url", source.sec_index_url);
  if (source.stored_snapshot) {
    copy("document_revision", source.stored_snapshot.document_revision);
    copy("source_set_revision", source.stored_snapshot.source_set_revision);
    copy("representation", source.stored_snapshot.representation);
  }
  return Object.keys(snapshot).length > 0 ? snapshot : null;
}

export function citationForSource(source: Source): string {
  return source.citation.length > 0 ? source.citation : (source.document_id ?? "");
}

export function excerptForSource(source: Source): string {
  return source.text ?? source.text_preview ?? "";
}

/** The document member reference: the canonical catalog identity and nothing else. */
export function documentReference(documentId: string, meta: {
  ticker?: string | null;
  section?: string | null;
  filingDate?: string | null;
  reportDate?: string | null;
  accessionNumber?: string | null;
  sourceUrl?: string | null;
  title?: string | null;
} = {}): Record<string, unknown> {
  const reference: Record<string, unknown> = { document_id: documentId };
  const copy = (key: string, value: unknown) => {
    if (typeof value === "string" && value.length > 0) reference[key] = value;
  };
  copy("ticker", meta.ticker);
  copy("section", meta.section);
  copy("filing_date", meta.filingDate);
  copy("report_date", meta.reportDate);
  copy("accession_number", meta.accessionNumber);
  copy("source_url", meta.sourceUrl);
  copy("title", meta.title);
  return reference;
}

export function documentMetaFromItem(item: CollectionItemRecord): {
  ticker: string | null;
  section: string | null;
  filingDate: string | null;
  reportDate: string | null;
  accessionNumber: string | null;
} {
  const reference = item.reference;
  return {
    ticker: referenceString(reference, "ticker"),
    section: referenceString(reference, "section"),
    filingDate: referenceString(reference, "filing_date"),
    reportDate: referenceString(reference, "report_date"),
    accessionNumber: referenceString(reference, "accession_number"),
  };
}

/** Human-readable provenance line for a member row; empty when nothing is known. */
export function itemProvenanceLine(item: CollectionItemRecord, vi: boolean): string {
  const parts: string[] = [];
  const ticker = referenceString(item.reference, "ticker");
  const section = referenceString(item.reference, "section");
  const filingDate = referenceString(item.reference, "filing_date");
  const representation = referenceString(item.reference, "representation");
  if (ticker) parts.push(formatCompanyLabel(ticker));
  if (section) parts.push(SECTION_METADATA[section]?.shortLabel ?? section);
  if (filingDate) parts.push(filingDate);
  if (parts.length === 0 && representation) parts.push(representation);
  return parts.join(" · ");
}

export type CollectionItemTarget =
  | { kind: "document"; documentId: string; title: string; ticker: string | null; filingDate: string | null; reportDate: string | null; accessionNumber: string | null }
  | { kind: "evidence"; source: Source }
  | { kind: "answer"; conversationId: string | null; messageId: string | null }
  | { kind: "unavailable"; reason: string };

/** Where a member actually opens: canonical document reader, the evidence
 * reader, the originating conversation message, or an honest unavailable state. */
export function itemOpenTarget(item: CollectionItemRecord, vi: boolean): CollectionItemTarget {
  const reference = item.reference;
  const documentId = referenceString(reference, "document_id");
  const chunkId = referenceString(reference, "chunk_id");
  const conversationId = referenceString(reference, "conversation_id");
  const messageId = referenceString(reference, "message_id");
  if (item.item_kind === "document") {
    if (!documentId) {
      return { kind: "unavailable", reason: vi ? "Mục tài liệu này không mang document_id." : "This document member carries no document_id." };
    }
    return {
      kind: "document",
      documentId,
      title: item.citation || documentId,
      ticker: referenceString(reference, "ticker"),
      filingDate: referenceString(reference, "filing_date"),
      reportDate: referenceString(reference, "report_date"),
      accessionNumber: referenceString(reference, "accession_number"),
    };
  }
  if (item.item_kind === "answer") {
    if (!conversationId && !messageId) {
      return { kind: "unavailable", reason: vi ? "Mục câu trả lời này không mang định danh hội thoại hay tin nhắn." : "This answer member carries no conversation or message identity." };
    }
    return { kind: "answer", conversationId, messageId };
  }
  if (item.item_kind === "note") {
    return { kind: "unavailable", reason: vi ? "Ghi chú được đọc trong tab Notes của bộ sưu tập." : "Notes are read in the collection's Notes tab." };
  }
  // evidence: the stored snapshot is a historical capture; opening it never
  // re-runs retrieval and never regenerates an answer.
  const source: Source = {
    citation: item.citation,
    text_preview: item.excerpt,
    text: item.excerpt,
    chunk_id: chunkId,
    document_id: documentId,
    ticker: referenceString(reference, "ticker"),
    section: referenceString(reference, "section"),
    filing_date: referenceString(reference, "filing_date"),
    report_date: referenceString(reference, "report_date"),
    source_url: referenceString(reference, "source_url"),
    sec_index_url: referenceString(reference, "sec_index_url"),
  };
  if (referenceString(reference, "chunk_text_hash")) source.chunk_text_hash = referenceString(reference, "chunk_text_hash") as string;
  const stored: NonNullable<Source["stored_snapshot"]> = { chunk_id: chunkId };
  const snapshot = item.snapshot ?? {};
  const snapshotValue = (key: string) => referenceString(snapshot, key) ?? referenceString(reference, key);
  const documentRevision = snapshotValue("document_revision");
  if (documentRevision) stored.document_revision = documentRevision;
  const sourceRevision = snapshotValue("source_set_revision");
  if (sourceRevision) stored.source_set_revision = sourceRevision;
  const representation = snapshotValue("representation");
  if (representation === "indexed_excerpt" || representation === "structured_html" || representation === "normalized_text") {
    stored.representation = representation;
  }
  const coverage = snapshotValue("coverage_status");
  if (coverage) stored.coverage_status = coverage as ReaderCoverageStatus;
  const location = snapshotValue("location_status");
  if (location) stored.location_status = location as NonNullable<Source["stored_snapshot"]>["location_status"];
  source.stored_snapshot = stored;
  if (!chunkId && !documentId && !conversationId && !messageId) {
    return { kind: "unavailable", reason: vi ? "Mục bằng chứng này không mang định danh nguồn nào." : "This evidence member carries no source identity." };
  }
  return { kind: "evidence", source };
}

/** Members that can actually be opened; the rest render a truthful reason. */
export function isItemOpenable(item: CollectionItemRecord, vi: boolean): boolean {
  return itemOpenTarget(item, vi).kind !== "unavailable";
}

export function exportFileName(collection: CollectionRecord, format: CollectionExportFormat): string {
  const slug = collection.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "collection";
  return `${slug}-${collection.collection_id.slice(0, 12)}.${format === "markdown" ? "md" : "json"}`;
}

export function exportPayload(collection: CollectionRecord, format: CollectionExportFormat, result: { format: "json" | "markdown"; document?: unknown; content?: string }): string {
  if (format === "markdown") return result.content ?? "";
  return JSON.stringify(result.document ?? null, null, 2);
}

/** Page-level note about the 100-item ceiling DATA-003 enforces per collection. */
export function itemCeilingNote(shown: number, total: number, vi: boolean): string | null {
  if (total <= shown) return null;
  return vi ? `Đang hiển thị ${shown}/${total} mục.` : `Showing ${shown} of ${total} items.`;
}
