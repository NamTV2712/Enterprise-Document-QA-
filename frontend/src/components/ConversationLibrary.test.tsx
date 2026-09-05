import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ConversationLibrary } from "./ConversationLibrary";
import { ConversationRecord } from "../lib/conversationStore";

const record: ConversationRecord = {
  schemaVersion: 1,
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
});
