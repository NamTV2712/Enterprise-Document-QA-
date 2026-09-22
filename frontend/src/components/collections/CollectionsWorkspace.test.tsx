import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { CollectionsWorkspace, collectionItemFocusId } from "./CollectionsWorkspace";
import { LocaleProvider } from "../../lib/i18n";
import {
  addCollectionNote,
  ApiError,
  deleteCollection,
  exportCollection,
  getCollection,
  listCollectionActivity,
  listCollectionItems,
  listCollectionNotes,
  listCollections,
  updateCollection,
} from "../../lib/api";
import type {
  CollectionItemRecord,
  CollectionListResponse,
  CollectionRecord,
  DocumentWorkspaceTarget,
  Source,
} from "../../types";

vi.mock("../../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/api")>();
  return {
    ...actual,
    listCollections: vi.fn(),
    getCollection: vi.fn(),
    listCollectionItems: vi.fn(),
    listCollectionNotes: vi.fn(),
    listCollectionActivity: vi.fn(),
    updateCollection: vi.fn(),
    deleteCollection: vi.fn(),
    exportCollection: vi.fn(),
    createCollection: vi.fn(),
    addCollectionItem: vi.fn(),
    addCollectionNote: vi.fn(),
  };
});

const listCollectionsMock = vi.mocked(listCollections);
const getCollectionMock = vi.mocked(getCollection);
const listItemsMock = vi.mocked(listCollectionItems);
const listNotesMock = vi.mocked(listCollectionNotes);
const listActivityMock = vi.mocked(listCollectionActivity);
const addNoteMock = vi.mocked(addCollectionNote);
const updateCollectionMock = vi.mocked(updateCollection);
const deleteCollectionMock = vi.mocked(deleteCollection);
const exportCollectionMock = vi.mocked(exportCollection);

const NOW = new Date("2026-09-22T12:00:00Z").getTime();

function record(overrides: Partial<CollectionRecord> = {}): CollectionRecord {
  return {
    collection_id: "col-risk",
    name: "Risk Analysis",
    description: "Key risks and uncertainties for Apple based on recent filings.",
    tags: ["Risk Factors", "Regulatory", "Macroeconomics", "Competition"],
    favorite: true,
    private: true,
    revision: 4,
    created_at: "2026-09-15T08:00:00Z",
    updated_at: "2026-09-22T10:00:00Z",
    item_count: 2,
    ...overrides,
  };
}

function item(overrides: Partial<CollectionItemRecord> = {}): CollectionItemRecord {
  return {
    item_id: "itm-doc",
    collection_id: "col-risk",
    item_kind: "document",
    citation: "Apple Inc. (AAPL) · 2025-10-31",
    excerpt: "",
    reference: { document_id: "AAPL-2024", ticker: "AAPL", filing_date: "2025-10-31" },
    revision: 1,
    created_at: "2026-09-22T10:00:00Z",
    updated_at: "2026-09-22T10:00:00Z",
    ...overrides,
  };
}

function listResponse(items: CollectionRecord[], total = items.length): CollectionListResponse {
  return { items, total, page: 1, page_size: 25 };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

async function selectDetailTab(rail: HTMLElement, name: "Notes" | "Activity" | "Settings") {
  await waitFor(() => expect(within(rail).queryByText("Reading items…")).toBeNull());
  const tab = within(rail).getByRole("tab", { name });
  fireEvent.click(tab);
  await waitFor(() => expect(tab).toHaveAttribute("aria-selected", "true"));
}

function renderWorkspace(props: Partial<Parameters<typeof CollectionsWorkspace>[0]> = {}) {
  const onSelectCollection = vi.fn();
  const onOpenDocument = vi.fn<(target: DocumentWorkspaceTarget) => void>();
  const onOpenEvidence = vi.fn<(source: Source, returnFocusId: string) => void>();
  const onOpenMessage = vi.fn();
  const view = (selectedCollectionId: string | null) => (
    <LocaleProvider>
      <CollectionsWorkspace
        onSelectCollection={onSelectCollection}
        onOpenDocument={onOpenDocument}
        onOpenEvidence={onOpenEvidence}
        onOpenMessage={onOpenMessage}
        librarySlot={<input id="library-search-input" type="search" aria-label="Search saved conversations" />}
        {...props}
        selectedCollectionId={selectedCollectionId}
      />
    </LocaleProvider>
  );
  const rendered = render(view(props.selectedCollectionId ?? null));
  return {
    onSelectCollection,
    onOpenDocument,
    onOpenEvidence,
    onOpenMessage,
    rerenderSelection: (collectionId: string | null) => rendered.rerender(view(collectionId)),
  };
}

beforeEach(() => {
  localStorage.clear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(NOW);
  listCollectionsMock.mockReset();
  getCollectionMock.mockReset();
  listItemsMock.mockReset();
  listNotesMock.mockReset();
  listActivityMock.mockReset();
  addNoteMock.mockReset();
  updateCollectionMock.mockReset();
  deleteCollectionMock.mockReset();
  exportCollectionMock.mockReset();
  listItemsMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 });
  listNotesMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 });
  listActivityMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("CollectionsWorkspace", () => {
  test("renders typed collections with their real fields only", async () => {
    listCollectionsMock.mockImplementation(async (params = {}) =>
      params.page_size === 1 ? listResponse([record()], params.favorite ? 1 : 1) : listResponse([record()]),
    );

    renderWorkspace();

    expect(await screen.findByRole("heading", { name: "Risk Analysis" })).toBeInTheDocument();
    // The reference's owner, share and storage values have no capability here
    // and must not appear.
    expect(screen.queryByText(/Nguyen/)).toBeNull();
    expect(screen.queryByText(/Share/)).toBeNull();
    expect(screen.queryByText(/GB/)).toBeNull();
    // Real fields do appear: item count, update time, tags with an overflow.
    expect(screen.getByText("2 items")).toBeInTheDocument();
    expect(screen.getByText("2 hours ago", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Risk Factors")).toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  test("browsing never writes to the workspace", async () => {
    listCollectionsMock.mockResolvedValue(listResponse([record()]));
    renderWorkspace({ selectedCollectionId: "col-risk" });
    getCollectionMock.mockResolvedValue(record());

    await screen.findByRole("heading", { name: "Risk Analysis" });
    fireEvent.change(screen.getByLabelText("Search collections"), { target: { value: "risk" } });
    fireEvent.click(screen.getByRole("tab", { name: /Favorites/ }));

    await waitFor(() => expect(listCollectionsMock).toHaveBeenCalled());
    expect(updateCollectionMock).not.toHaveBeenCalled();
    expect(deleteCollectionMock).not.toHaveBeenCalled();
    expect(exportCollectionMock).not.toHaveBeenCalled();
  });

  test("a 404 from the workspace boundary is an unavailable state, not an empty list", async () => {
    listCollectionsMock.mockRejectedValue(new ApiError("Local workspace capability is unavailable", 404));

    renderWorkspace();

    expect(await screen.findByText("Collections are unavailable in this mode")).toBeInTheDocument();
    expect(screen.queryByText("No collections yet")).toBeNull();
    expect(screen.queryByRole("button", { name: "New Collection" })).toBeNull();
  });

  test("an empty workspace is honest about being empty", async () => {
    listCollectionsMock.mockResolvedValue(listResponse([], 0));

    renderWorkspace();

    expect(await screen.findByText("No collections yet")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "New Collection" }).length).toBeGreaterThan(0);
  });

  test("selecting a collection opens its route and reads its typed members", async () => {
    listCollectionsMock.mockResolvedValue(listResponse([record()]));
    listItemsMock.mockResolvedValue({ items: [item()], total: 1, page: 1, page_size: 100 });

    const { onSelectCollection } = renderWorkspace();

    fireEvent.click(await screen.findByRole("button", { name: "Open Risk Analysis" }));
    expect(onSelectCollection).toHaveBeenCalledWith("col-risk");
  });

  test("a stale list response cannot replace a newer search's results", async () => {
    let resolveSlow: ((value: CollectionListResponse) => void) | null = null;
    listCollectionsMock.mockImplementation((params = {}) => {
      if (params.page_size === 1) return Promise.resolve(listResponse([record()], 1));
      if (params.search === "slow") {
        return new Promise<CollectionListResponse>((resolve) => {
          resolveSlow = resolve;
        });
      }
      if (params.search === "fast") {
        return Promise.resolve(listResponse([record({ collection_id: "col-new", name: "Newer query result", favorite: false })]));
      }
      return Promise.resolve(listResponse([record()]));
    });

    renderWorkspace();
    await screen.findByRole("heading", { name: "Risk Analysis" });

    fireEvent.change(screen.getByLabelText("Search collections"), { target: { value: "slow" } });
    fireEvent.change(screen.getByLabelText("Search collections"), { target: { value: "fast" } });
    await screen.findByRole("heading", { name: "Newer query result" });

    resolveSlow?.(listResponse([record({ collection_id: "col-slow", name: "Stale result", favorite: false })]));
    await waitFor(() => expect(listCollectionsMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Stale result" })).toBeNull());
    expect(screen.getByRole("heading", { name: "Newer query result" })).toBeInTheDocument();
  });

  test("a revision conflict while favouriting is reported as a conflict", async () => {
    listCollectionsMock.mockImplementation(async (params = {}) =>
      params.page_size === 1 ? listResponse([record()], 1) : listResponse([record({ favorite: false })]),
    );
    updateCollectionMock.mockRejectedValue(new ApiError("Collection revision is stale", 409));

    renderWorkspace();

    fireEvent.click(await screen.findByRole("button", { name: "Mark Risk Analysis as favorite" }));
    expect(await screen.findByText(/changed elsewhere/)).toBeInTheDocument();
    expect(updateCollectionMock).toHaveBeenCalledWith("col-risk", { revision: 4, favorite: true });
  });

  test("opening a document member hands off the canonical identity and return focus", async () => {
    const detail = record({ item_count: 1 });
    listCollectionsMock.mockResolvedValue(listResponse([detail]));
    getCollectionMock.mockResolvedValue(detail);
    listItemsMock.mockResolvedValue({ items: [item()], total: 1, page: 1, page_size: 100 });

    const { onOpenDocument } = renderWorkspace({ selectedCollectionId: "col-risk" });

    const member = await waitFor(() => {
      const element = document.getElementById(collectionItemFocusId("itm-doc"));
      if (!element) throw new Error("member row not rendered yet");
      return element;
    });
    fireEvent.click(member);

    expect(onOpenDocument).toHaveBeenCalledTimes(1);
    const target = onOpenDocument.mock.calls[0][0];
    expect(target).toMatchObject({
      kind: "catalog",
      documentId: "AAPL-2024",
      ticker: "AAPL",
      filingDate: "2025-10-31",
      returnView: "library",
    });
    expect(target.returnFocusId).toBe(collectionItemFocusId("itm-doc"));
  });

  test("opening an evidence member reuses the stored snapshot without re-running retrieval", async () => {
    const detail = record({ item_count: 1 });
    listCollectionsMock.mockResolvedValue(listResponse([detail]));
    getCollectionMock.mockResolvedValue(detail);
    listItemsMock.mockResolvedValue({
      items: [
        item({
          item_id: "itm-evidence",
          item_kind: "evidence",
          citation: "AAPL indexed excerpt · financial_statements",
          excerpt: "Total net sales were $391 billion.",
          reference: { document_id: "AAPL-2024", chunk_id: "AAPL_0", ticker: "AAPL", document_revision: "rev-7" },
          snapshot: { representation: "indexed_excerpt" },
        }),
      ],
      total: 1,
      page: 1,
      page_size: 100,
    });

    const { onOpenEvidence, onOpenDocument } = renderWorkspace({ selectedCollectionId: "col-risk" });

    const member = await waitFor(() => {
      const element = document.getElementById(collectionItemFocusId("itm-evidence"));
      if (!element) throw new Error("member row not rendered yet");
      return element;
    });
    fireEvent.click(member);

    expect(onOpenDocument).not.toHaveBeenCalled();
    expect(onOpenEvidence).toHaveBeenCalledTimes(1);
    const [source, focusId] = onOpenEvidence.mock.calls[0];
    expect(source.chunk_id).toBe("AAPL_0");
    expect(source.document_id).toBe("AAPL-2024");
    expect(source.stored_snapshot?.document_revision).toBe("rev-7");
    expect(source.score).toBeUndefined();
    expect(focusId).toBe(collectionItemFocusId("itm-evidence"));
  });

  test("the Conversations tab stays reachable and takes the Ctrl/Cmd+K handoff", async () => {
    listCollectionsMock.mockResolvedValue(listResponse([record()]));
    const onConversationSearchFocused = vi.fn();

    renderWorkspace({ focusConversationSearch: true, onConversationSearchFocused });

    const search = await screen.findByRole("searchbox", { name: "Search saved conversations" });
    await waitFor(() => expect(search).toHaveFocus());
    expect(screen.getByRole("tab", { name: /Conversations/ })).toHaveAttribute("aria-selected", "true");
    expect(onConversationSearchFocused).toHaveBeenCalledTimes(1);
    // The collections list is not rendered while the library tab is active.
    expect(screen.queryByRole("heading", { name: "Risk Analysis" })).toBeNull();
  });

  test("the rail lists members with their declared kinds", async () => {
    const detail = record({ item_count: 3 });
    listCollectionsMock.mockResolvedValue(listResponse([detail]));
    getCollectionMock.mockResolvedValue(detail);
    listItemsMock.mockResolvedValue({
      items: [
        item(),
        item({ item_id: "itm-ev", item_kind: "evidence", citation: "Excerpt", reference: { chunk_id: "AAPL_0" } }),
        item({ item_id: "itm-note", item_kind: "note", citation: "A note", reference: {} }),
      ],
      total: 3,
      page: 1,
      page_size: 100,
    });

    renderWorkspace({ selectedCollectionId: "col-risk" });

    const rail = await screen.findByRole("complementary", { name: /Risk Analysis/ });
    await waitFor(() => expect(within(rail).getAllByText("Document").length).toBeGreaterThan(0));
    // The badge next to each member states the kind DATA-003 returned.
    const kinds = Array.from(rail.querySelectorAll(".collection-kind-badge__label")).map((node) => node.textContent);
    expect(kinds).toEqual(["Document", "Evidence", "Note"]);
    expect(within(rail).getByText("Items (3)")).toBeInTheDocument();
    expect(within(rail).getByText("Revision 4 · activity and notes recorded by the workspace")).toBeInTheDocument();
  });

  test("the list menu requires confirmation and Cancel or Escape performs no write", async () => {
    listCollectionsMock.mockResolvedValue(listResponse([record()]));
    renderWorkspace();

    const trigger = await screen.findByRole("button", { name: "Actions for Risk Analysis" });
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete collection" }));

    let dialog = screen.getByRole("dialog", { name: "Delete collection?" });
    expect(within(dialog).getByText(/Risk Analysis/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(deleteCollectionMock).not.toHaveBeenCalled();
    await waitFor(() => expect(trigger).toHaveFocus());

    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete collection" }));
    dialog = screen.getByRole("dialog", { name: "Delete collection?" });
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(dialog).not.toBeInTheDocument());
    expect(deleteCollectionMock).not.toHaveBeenCalled();
  });

  test("the detail menu confirms once with the captured identity and revision", async () => {
    const current = record({ revision: 7 });
    listCollectionsMock.mockResolvedValue(listResponse([current]));
    getCollectionMock.mockResolvedValue(current);
    let finishDelete: ((receipt: Awaited<ReturnType<typeof deleteCollection>>) => void) | null = null;
    deleteCollectionMock.mockImplementation(() => new Promise((resolve) => {
      finishDelete = resolve;
    }));
    renderWorkspace({ selectedCollectionId: current.collection_id });

    const rail = await screen.findByRole("complementary", { name: /Risk Analysis/ });
    fireEvent.click(within(rail).getByRole("button", { name: "Collection actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete collection" }));
    const confirm = within(screen.getByRole("dialog", { name: "Delete collection?" }))
      .getByRole("button", { name: "Delete permanently" });
    fireEvent.click(confirm);
    fireEvent.click(confirm);

    expect(deleteCollectionMock).toHaveBeenCalledTimes(1);
    expect(deleteCollectionMock).toHaveBeenCalledWith("col-risk", 7);
    finishDelete?.({
      operation: "delete_collection",
      entity_type: "collection",
      entity_id: "col-risk",
      revision: 8,
      deleted_at: "2026-09-22T12:00:00Z",
    });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Delete collection?" })).toBeNull());
  });

  test("Settings opens the same confirmation and a conflict is visible without retry", async () => {
    const current = record({ revision: 9 });
    listCollectionsMock.mockResolvedValue(listResponse([current]));
    getCollectionMock.mockResolvedValue(current);
    deleteCollectionMock.mockRejectedValue(new ApiError("Collection revision is stale", 409));
    renderWorkspace({ selectedCollectionId: current.collection_id });

    const rail = await screen.findByRole("complementary", { name: /Risk Analysis/ });
    await selectDetailTab(rail, "Settings");
    const deleteFromSettings = await waitFor(() =>
      within(rail).getByRole("button", { name: "Delete collection" }),
    );
    fireEvent.click(deleteFromSettings);
    const dialog = screen.getByRole("dialog", { name: "Delete collection?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete permanently" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(/changed elsewhere/i);
    expect(deleteCollectionMock).toHaveBeenCalledTimes(1);
    expect(deleteCollectionMock).toHaveBeenCalledWith("col-risk", 9);
  });

  test("the shared confirmation has Vietnamese labels and consequences", async () => {
    localStorage.setItem("sec_qa_locale", "vi");
    listCollectionsMock.mockResolvedValue(listResponse([record()]));
    renderWorkspace();

    const trigger = await screen.findByRole("button", { name: "Hành động cho Risk Analysis" });
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("menuitem", { name: "Xoá bộ sưu tập" }));

    const dialog = screen.getByRole("dialog", { name: "Xoá bộ sưu tập?" });
    expect(within(dialog).getByText(/không thể tạo lại/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Huỷ" })).toHaveFocus();
    expect(within(dialog).getByRole("button", { name: "Xoá vĩnh viễn" })).toBeInTheDocument();
  });

  test("late A cannot replace cached B or a cleared selection", async () => {
    const pendingA: Array<ReturnType<typeof deferred<CollectionRecord>>> = [];
    const collectionB = record({ collection_id: "col-b", name: "Collection B" });
    listCollectionsMock.mockResolvedValue(listResponse([collectionB]));
    getCollectionMock.mockImplementation(() => {
      const request = deferred<CollectionRecord>();
      pendingA.push(request);
      return request.promise;
    });
    const { rerenderSelection } = renderWorkspace({ selectedCollectionId: "col-a" });
    await waitFor(() => expect(getCollectionMock).toHaveBeenCalledWith("col-a", expect.any(AbortSignal)));

    rerenderSelection("col-b");
    expect(await screen.findByRole("complementary", { name: /Collection B/ })).toBeInTheDocument();
    const firstLifetimeCount = pendingA.length;
    pendingA.slice(0, firstLifetimeCount).forEach((request) => {
      request.resolve(record({ collection_id: "col-a", name: "Late Collection A" }));
    });
    await Promise.resolve();
    expect(screen.getByRole("complementary", { name: /Collection B/ })).toBeInTheDocument();
    expect(screen.queryByText("Late Collection A")).toBeNull();

    rerenderSelection("col-a");
    await waitFor(() => expect(pendingA.length).toBeGreaterThan(firstLifetimeCount));
    rerenderSelection(null);
    pendingA.slice(firstLifetimeCount).forEach((request) => {
      request.resolve(record({ collection_id: "col-a", name: "Late after close" }));
    });
    await Promise.resolve();
    expect(screen.queryByText("Late after close")).toBeNull();
    expect(screen.getByText("Select a collection")).toBeInTheDocument();
  });

  test("an older A lifetime cannot overwrite a newer A lifetime", async () => {
    const pendingA: Array<ReturnType<typeof deferred<CollectionRecord>>> = [];
    const collectionB = record({ collection_id: "col-b", name: "Collection B" });
    listCollectionsMock.mockResolvedValue(listResponse([collectionB]));
    getCollectionMock.mockImplementation(() => {
      const request = deferred<CollectionRecord>();
      pendingA.push(request);
      return request.promise;
    });
    const { rerenderSelection } = renderWorkspace({ selectedCollectionId: "col-a" });
    await waitFor(() => expect(pendingA.length).toBeGreaterThan(0));
    rerenderSelection("col-b");
    await screen.findByRole("complementary", { name: /Collection B/ });
    const firstLifetimeCount = pendingA.length;
    rerenderSelection("col-a");
    await waitFor(() => expect(pendingA.length).toBeGreaterThan(firstLifetimeCount));

    pendingA.at(-1)?.resolve(record({ collection_id: "col-a", name: "Current Collection A" }));
    expect(await screen.findByRole("complementary", { name: /Current Collection A/ })).toBeInTheDocument();
    pendingA.slice(0, firstLifetimeCount).forEach((request) => {
      request.resolve(record({ collection_id: "col-a", name: "Obsolete Collection A" }));
    });
    await Promise.resolve();
    expect(screen.queryByText("Obsolete Collection A")).toBeNull();
    expect(screen.getByRole("complementary", { name: /Current Collection A/ })).toBeInTheDocument();
  });

  test("old notes and activity cannot paint into another collection", async () => {
    const collectionA = record({ collection_id: "col-a", name: "Collection A" });
    const collectionB = record({ collection_id: "col-b", name: "Collection B" });
    const notesA = deferred<Awaited<ReturnType<typeof listCollectionNotes>>>();
    const activityA = deferred<Awaited<ReturnType<typeof listCollectionActivity>>>();
    listCollectionsMock.mockResolvedValue(listResponse([collectionA, collectionB]));
    listNotesMock.mockImplementation((collectionId) => collectionId === "col-a"
      ? notesA.promise
      : Promise.resolve({
          items: [{ note_id: "note-b", collection_id: "col-b", text: "B note", revision: 1, created_at: "2026-09-22T10:00:00Z", updated_at: "2026-09-22T10:00:00Z" }],
          total: 1,
          page: 1,
          page_size: 100,
        }));
    listActivityMock.mockImplementation((collectionId) => collectionId === "col-a"
      ? activityA.promise
      : Promise.resolve({
          items: [{ activity_id: "act-b", collection_id: "col-b", entity_type: "collection", entity_id: "col-b", event_type: "collection_created", occurred_at: "2026-09-22T10:00:00Z" }],
          total: 1,
          page: 1,
          page_size: 100,
        }));
    const { rerenderSelection } = renderWorkspace({ selectedCollectionId: "col-a" });
    let rail = await screen.findByRole("complementary", { name: /Collection A/ });
    await selectDetailTab(rail, "Notes");
    await waitFor(() => expect(listNotesMock).toHaveBeenCalledWith("col-a", expect.anything(), expect.any(AbortSignal)));
    rerenderSelection("col-b");
    rail = await screen.findByRole("complementary", { name: /Collection B/ });
    await selectDetailTab(rail, "Notes");
    expect(await within(rail).findByText("B note")).toBeInTheDocument();
    notesA.resolve({
      items: [{ note_id: "note-a", collection_id: "col-a", text: "Late A note", revision: 1, created_at: "2026-09-22T10:00:00Z", updated_at: "2026-09-22T10:00:00Z" }],
      total: 1,
      page: 1,
      page_size: 100,
    });
    await Promise.resolve();
    expect(screen.queryByText("Late A note")).toBeNull();

    rerenderSelection("col-a");
    rail = await screen.findByRole("complementary", { name: /Collection A/ });
    await selectDetailTab(rail, "Activity");
    await waitFor(() => expect(listActivityMock).toHaveBeenCalledWith("col-a", expect.anything(), expect.any(AbortSignal)));
    rerenderSelection("col-b");
    rail = await screen.findByRole("complementary", { name: /Collection B/ });
    await selectDetailTab(rail, "Activity");
    expect(await within(rail).findByText("Collection created")).toBeInTheDocument();
    activityA.resolve({
      items: [{ activity_id: "act-a", collection_id: "col-a", entity_type: "note", entity_id: "note-a", event_type: "note_added", occurred_at: "2026-09-22T10:00:00Z" }],
      total: 1,
      page: 1,
      page_size: 100,
    });
    await Promise.resolve();
    expect(screen.queryByText("Note added")).toBeNull();
  });

  test("a late old mutation cannot replace B, clear its draft, or navigate away", async () => {
    const collectionA = record({ collection_id: "col-a", name: "Collection A" });
    const collectionB = record({ collection_id: "col-b", name: "Collection B" });
    const noteWrite = deferred<Awaited<ReturnType<typeof addCollectionNote>>>();
    listCollectionsMock.mockResolvedValue(listResponse([collectionA, collectionB]));
    addNoteMock.mockReturnValue(noteWrite.promise);
    const { onSelectCollection, rerenderSelection } = renderWorkspace({ selectedCollectionId: "col-a" });
    let rail = await screen.findByRole("complementary", { name: /Collection A/ });
    await selectDetailTab(rail, "Notes");
    const draftA = await within(rail).findByLabelText("Add note");
    fireEvent.change(draftA, { target: { value: "A draft" } });
    fireEvent.click(within(rail).getByRole("button", { name: "Save note" }));
    await waitFor(() => expect(addNoteMock).toHaveBeenCalledWith("col-a", { text: "A draft" }));

    rerenderSelection("col-b");
    rail = await screen.findByRole("complementary", { name: /Collection B/ });
    await selectDetailTab(rail, "Notes");
    const draftB = await within(rail).findByLabelText("Add note");
    fireEvent.change(draftB, { target: { value: "B draft stays" } });
    noteWrite.resolve({
      note_id: "note-a",
      collection_id: "col-a",
      text: "A draft",
      revision: 1,
      created_at: "2026-09-22T10:00:00Z",
      updated_at: "2026-09-22T10:00:00Z",
    });
    await Promise.resolve();

    expect(screen.getByRole("complementary", { name: /Collection B/ })).toBeInTheDocument();
    expect(draftB).toHaveValue("B draft stays");
    expect(onSelectCollection).not.toHaveBeenCalled();
  });

  test("a late detail update cannot replace the newer selected collection", async () => {
    const collectionA = record({ collection_id: "col-a", name: "Collection A", favorite: true });
    const collectionB = record({ collection_id: "col-b", name: "Collection B", favorite: false });
    const updateA = deferred<CollectionRecord>();
    listCollectionsMock.mockResolvedValue(listResponse([collectionA, collectionB]));
    updateCollectionMock.mockReturnValue(updateA.promise);
    const { rerenderSelection } = renderWorkspace({ selectedCollectionId: "col-a" });
    let rail = await screen.findByRole("complementary", { name: /Collection A/ });
    fireEvent.click(within(rail).getByRole("button", { name: "Remove from favorites" }));
    await waitFor(() => expect(updateCollectionMock).toHaveBeenCalledWith("col-a", { revision: 4, favorite: false }));

    rerenderSelection("col-b");
    rail = await screen.findByRole("complementary", { name: /Collection B/ });
    updateA.resolve({ ...collectionA, name: "Late updated A", favorite: false, revision: 5 });
    await Promise.resolve();

    expect(rail).toBeInTheDocument();
    expect(screen.queryByText("Late updated A")).toBeNull();
  });

  test("a late delete completion cannot navigate away from a newer selection", async () => {
    const collectionA = record({ collection_id: "col-a", name: "Collection A" });
    const collectionB = record({ collection_id: "col-b", name: "Collection B" });
    const deleteA = deferred<Awaited<ReturnType<typeof deleteCollection>>>();
    listCollectionsMock.mockResolvedValue(listResponse([collectionA, collectionB]));
    deleteCollectionMock.mockReturnValue(deleteA.promise);
    const { onSelectCollection, rerenderSelection } = renderWorkspace({ selectedCollectionId: "col-a" });
    let rail = await screen.findByRole("complementary", { name: /Collection A/ });
    fireEvent.click(within(rail).getByRole("button", { name: "Collection actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete collection" }));
    fireEvent.click(within(screen.getByRole("dialog", { name: "Delete collection?" }))
      .getByRole("button", { name: "Delete permanently" }));
    await waitFor(() => expect(deleteCollectionMock).toHaveBeenCalledWith("col-a", 4));

    rerenderSelection("col-b");
    rail = await screen.findByRole("complementary", { name: /Collection B/ });
    deleteA.resolve({
      operation: "delete_collection",
      entity_type: "collection",
      entity_id: "col-a",
      revision: 5,
      deleted_at: "2026-09-22T12:00:00Z",
    });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Delete collection?" })).toBeNull());

    expect(rail).toBeInTheDocument();
    expect(onSelectCollection).not.toHaveBeenCalledWith(null);
  });

  test("a failed old selection cannot publish an error under B", async () => {
    const pendingA: Array<ReturnType<typeof deferred<CollectionRecord>>> = [];
    const collectionB = record({ collection_id: "col-b", name: "Collection B" });
    listCollectionsMock.mockResolvedValue(listResponse([collectionB]));
    getCollectionMock.mockImplementation(() => {
      const request = deferred<CollectionRecord>();
      pendingA.push(request);
      return request.promise;
    });
    const { rerenderSelection } = renderWorkspace({ selectedCollectionId: "col-a" });
    await waitFor(() => expect(pendingA.length).toBeGreaterThan(0));
    rerenderSelection("col-b");
    const rail = await screen.findByRole("complementary", { name: /Collection B/ });
    pendingA.forEach((request) => request.reject(new ApiError("Old A failed", 503)));
    await Promise.resolve();

    expect(within(rail).queryByRole("alert")).toBeNull();
    expect(screen.queryByText("Old A failed")).toBeNull();
  });

  test("aborted and failed old reads do not own B loading or error state", async () => {
    const collectionB = record({ collection_id: "col-b", name: "Collection B" });
    listCollectionsMock.mockResolvedValue(listResponse([collectionB]));
    getCollectionMock.mockImplementation((_collectionId, signal) => new Promise<CollectionRecord>((_resolve, reject) => {
      signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    }));
    const { rerenderSelection } = renderWorkspace({ selectedCollectionId: "col-a" });
    await waitFor(() => expect(getCollectionMock).toHaveBeenCalledTimes(1));
    rerenderSelection("col-b");

    const rail = await screen.findByRole("complementary", { name: /Collection B/ });
    expect(within(rail).queryByText("Reading the collection…")).toBeNull();
    expect(within(rail).queryByRole("alert")).toBeNull();
  });
});
