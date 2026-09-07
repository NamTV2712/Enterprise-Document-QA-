import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ConversationLibrary } from "./ConversationLibrary";
import { ConversationRecord } from "../lib/conversationStore";
import { conversationsToJson } from "../lib/conversationExport";

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

describe("ConversationLibrary", () => {
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
});
