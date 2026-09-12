import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ConversationLibrary } from "./ConversationLibrary";
import { ConversationRecord } from "../lib/conversationStore";
import { conversationsToJson } from "../lib/conversationExport";
import { saveEvidence } from "../lib/evidenceCollections";
import type { AnswerVariant, RequestSnapshot } from "../types";

const record: ConversationRecord = {
  schemaVersion: 2,
  titleMode: "auto",
  revision: 1,
  id: "conversation-1",
  sessionId: "session-1",
  title: "Revenue review",
  createdAt: 1,
  updatedAt: Date.now(),
  draft: "",
  bookmarkedMessageIds: [],
  messages: [
    { id: "u-1", sender: "user", text: "What was revenue?" },
    { id: "a-1", sender: "assistant", text: "Revenue was $100B." },
  ],
};

function renderLibrary(overrides: Partial<ComponentProps<typeof ConversationLibrary>> = {}) {
  return render(
    <ConversationLibrary
      conversations={[record]}
      activeConversationId="conversation-1"
      storageMode="localstorage"
      storageWarning={null}
      onSelect={vi.fn()}
      onRename={vi.fn()}
      onToggleBookmark={vi.fn()}
      onDelete={vi.fn()}
      onExport={vi.fn()}
      onClose={vi.fn()}
      {...overrides}
    />,
  );
}

function makeConversation(index: number, overrides: Partial<ConversationRecord> = {}): ConversationRecord {
  return {
    ...record,
    id: `conversation-${index}`,
    sessionId: `session-${index}`,
    title: `Research ${index}`,
    createdAt: index,
    updatedAt: index,
    messages: [
      { id: `u-${index}`, sender: "user", text: `Question ${index}` },
      { id: `a-${index}`, sender: "assistant", text: `Answer ${index}` },
    ],
    ...overrides,
  };
}

describe("ConversationLibrary", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => cleanup());

  test("filters saved conversations and exposes bookmark/export controls", () => {
    const onToggleBookmark = vi.fn();
    const onExport = vi.fn();
    renderLibrary({ onToggleBookmark, onExport });

    fireEvent.change(screen.getByRole("searchbox", { name: "Search saved conversations" }), {
      target: { value: "revenue" },
    });
    expect(screen.getByText("Revenue review")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Bookmark latest answer" }));
    fireEvent.click(screen.getByRole("button", { name: "Export conversation" }));

    expect(onToggleBookmark).toHaveBeenCalledWith("conversation-1", "a-1");
    expect(onExport).toHaveBeenCalledWith(record);
  });

  test("does not claim durable storage while the persistence owner reports a warning", () => {
    renderLibrary({ storageMode: "indexeddb", storageWarning: "Conversation storage is unavailable." });

    expect(screen.getByText("Storage needs attention")).toBeInTheDocument();
    expect(screen.queryByText("Saved on this device")).not.toBeInTheDocument();
  });

  test("requires confirmation before deleting a saved conversation", () => {
    const onDelete = vi.fn();
    renderLibrary({ onDelete });

    fireEvent.click(screen.getByRole("button", { name: "Delete conversation" }));
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(onDelete).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledWith("conversation-1");
  });

  test("previews a backup before calling the durable import handler", async () => {
    const onImportBackup = vi.fn().mockResolvedValue({
      imported: 1,
      persisted: 1,
      volatile: 0,
      failed: 0,
    });
    const { container } = renderLibrary({ onImportBackup });
    const backupText = conversationsToJson([record]);
    const file = Object.assign(new File([backupText], "research-backup.json", {
      type: "application/json",
    }), { text: vi.fn().mockResolvedValue(backupText) });
    const input = container.querySelector('input[type="file"]');
    expect(input).not.toBeNull();

    fireEvent.change(input as HTMLInputElement, { target: { files: [file] } });
    expect(await screen.findByRole("dialog", { name: "Review backup before import" })).toBeInTheDocument();
    expect(onImportBackup).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));
    await screen.findByText(/Imported 1/);
    expect(onImportBackup).toHaveBeenCalledTimes(1);
    expect(onImportBackup.mock.calls[0][0].conversations).toHaveLength(1);
  });

  test("browses a saved evidence snapshot and opens it through the reader", () => {
    const onOpenEvidence = vi.fn();
    saveEvidence({
      citation: "AAPL 10-K · Financial Table",
      text_preview: "Revenue snapshot",
      text: "Revenue snapshot captured at save time",
      chunk_id: "chunk-1",
      ticker: "AAPL",
      section: "financial_table",
    });
    renderLibrary({ onOpenEvidence });

    fireEvent.click(screen.getByRole("button", { name: /Research evidence · 1/ }));
    fireEvent.click(screen.getByRole("button", { name: /AAPL 10-K · Financial Table/ }));

    expect(onOpenEvidence).toHaveBeenCalledWith(expect.objectContaining({
      citation: "AAPL 10-K · Financial Table",
      excerpt: "Revenue snapshot captured at save time",
      chunkId: "chunk-1",
    }));
  });

  test("lists and reopens the exact immutable saved answer variant", () => {
    const snapshot: RequestSnapshot = { ticker: "AAPL", section: "risk_factors", topK: 5, enableComparative: false, answerLanguage: "en" };
    const variant: AnswerVariant = {
      id: "variant-1",
      originMessageId: "a-1",
      text: "Immutable saved answer",
      sources: [{ citation: "AAPL risk", text_preview: "Exact saved source", text: "Exact saved source", chunk_id: "chunk-1", ticker: "AAPL", section: "risk_factors" }],
      requestSnapshot: snapshot,
      answerLanguage: "en",
      status: "completed",
      createdAt: 10,
      updatedAt: 10,
    };
    const onOpenVariant = vi.fn();
    renderLibrary({
      conversations: [{ ...record, messages: record.messages.map((message) => message.id === "a-1" ? { ...message, requestSnapshot: snapshot } : message), variants: [variant] }],
      onOpenVariant,
    });

    expect(screen.getAllByText("Apple Inc. (AAPL)")).not.toHaveLength(0);
    expect(screen.getByText(/Saved on this device · linked sources/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open saved answer" }));
    expect(onOpenVariant).toHaveBeenCalledWith("conversation-1", "a-1", "variant-1");
  });

  test("shows exact current-source handoff separately from the historical snapshot", async () => {
    const onOpenCurrentSource = vi.fn().mockResolvedValue({ status: "current" as const });
    saveEvidence({
      citation: "AAPL 10-K · Risk Factors",
      text_preview: "Risk snapshot",
      text: "Risk snapshot captured at save time",
      chunk_id: "chunk-current",
      document_id: "AAPL:filing",
      ticker: "AAPL",
      section: "risk_factors",
    });
    renderLibrary({ onOpenCurrentSource });
    fireEvent.click(screen.getByRole("button", { name: /Research evidence · 1/ }));
    fireEvent.click(screen.getByRole("button", { name: "Open exact current source" }));
    expect(onOpenCurrentSource).toHaveBeenCalledWith(expect.objectContaining({ chunkId: "chunk-current" }));
  });

  test("keeps Recent Research bounded and ordered without inventing missing metadata", () => {
    const conversations = Array.from({ length: 10 }, (_, index) => makeConversation(index + 1));
    const onContinueResearch = vi.fn();
    renderLibrary({ conversations, onContinueResearch });

    const recentSection = screen.getByRole("region", { name: "Recent Research" });
    expect(within(recentSection).getByRole("heading", { name: "Recent Research" })).toBeInTheDocument();
    expect(within(recentSection).getByRole("button", { name: "Open recent research: Research 10" })).toBeInTheDocument();
    expect(within(recentSection).getByRole("button", { name: "Open recent research: Research 3" })).toBeInTheDocument();
    expect(within(recentSection).queryByRole("button", { name: "Open recent research: Research 2" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Conversation history" })).toBeInTheDocument();
    expect(screen.getByText("Research 2")).toBeInTheDocument();
    expect(screen.queryByText("All companies")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /Continue \(fill draft\)/ })[0]);
    expect(onContinueResearch).toHaveBeenCalledWith(expect.objectContaining({ id: "conversation-10" }));
  });

  test("shows an explicit answer state only when stored answer metadata exists", () => {
    renderLibrary({
      conversations: [makeConversation(1, {
        messages: record.messages.map((message) => message.sender === "assistant" ? { ...message, status: "completed" as const } : message),
      })],
    });

    expect(screen.getAllByText(/Completed/)).not.toHaveLength(0);
  });

  test("keeps stored provenance behind a disclosure without dropping supplied fields", () => {
    const collectionSource = {
      citation: "AAPL 10-K · Risk Factors",
      text_preview: "Risk snapshot",
      text: "Risk snapshot captured at save time",
      chunk_id: "chunk-provenance",
      ticker: "AAPL",
      section: "risk_factors",
      filing_date: "2025-10-31",
      document_id: "AAPL:filing",
      report_date: "2025-09-27",
      source_url: "https://example.test/source",
      sec_index_url: "https://example.test/index",
    };
    saveEvidence(collectionSource, {
      provenance: {
        documentId: "AAPL:filing",
        sourceDocumentId: "source-document-1",
        accessionNumber: "0000320193-25-000079",
        reportDate: "2025-09-27",
        documentRevision: "document-revision-1",
        sourceSetRevision: "source-set-revision-1",
        representation: "structured_html",
        coverageStatus: "complete",
        locationStatus: "exact",
        locationReason: "Exact source location verified.",
        sourceUrl: "https://example.test/source",
        secIndexUrl: "https://example.test/index",
        chunkTextHash: "hash-1",
        snapshotState: "captured",
      },
    });
    renderLibrary();
    fireEvent.click(screen.getByRole("button", { name: /Research evidence · 1/ }));
    fireEvent.click(screen.getByRole("button", { name: /AAPL 10-K · Risk Factors/ }));
    fireEvent.click(screen.getByText("Provenance details"));

    expect(screen.getByText("0000320193-25-000079")).toBeInTheDocument();
    expect(screen.getByText("source-document-1")).toBeInTheDocument();
    expect(screen.getByText("document-revision-1")).toBeInTheDocument();
    expect(screen.getByText("source-set-revision-1")).toBeInTheDocument();
    expect(screen.getByText("structured_html")).toBeInTheDocument();
    expect(screen.getByText("Exact source location verified.")).toBeInTheDocument();
  });

  test("reports a stale current-source check while keeping the saved snapshot action", async () => {
    const onOpenCurrentSource = vi.fn().mockResolvedValue({ status: "stale" as const, message: "The current chunk changed." });
    saveEvidence({
      citation: "AAPL 10-K · Risk Factors",
      text_preview: "Risk snapshot",
      text: "Risk snapshot captured at save time",
      chunk_id: "chunk-stale",
      ticker: "AAPL",
      section: "risk_factors",
    });
    renderLibrary({ onOpenCurrentSource });
    fireEvent.click(screen.getByRole("button", { name: /Research evidence · 1/ }));
    fireEvent.click(screen.getByRole("button", { name: "Open exact current source" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The current chunk changed.");
    expect(await screen.findByText(/Stale snapshot · still readable/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /AAPL 10-K · Risk Factors/ })).toBeInTheDocument();
  });

  test("keeps the historical snapshot when the exact current chunk is missing", async () => {
    const onOpenCurrentSource = vi.fn().mockResolvedValue({ status: "missing" as const, message: "The exact chunk is missing from the corpus." });
    saveEvidence({
      citation: "AAPL 10-K · Supply Chain",
      text_preview: "Supply snapshot",
      text: "Supply snapshot captured at save time",
      chunk_id: "chunk-missing",
      ticker: "AAPL",
      section: "risk_factors",
    });
    renderLibrary({ onOpenCurrentSource });
    fireEvent.click(screen.getByRole("button", { name: /Research evidence · 1/ }));
    fireEvent.click(screen.getByRole("button", { name: "Open exact current source" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The exact chunk is missing from the corpus.");
    expect(await screen.findByText(/Missing from corpus · snapshot retained/)).toBeInTheDocument();
    expect(screen.getByText("Supply snapshot captured at save time")).toBeInTheDocument();
  });
});
