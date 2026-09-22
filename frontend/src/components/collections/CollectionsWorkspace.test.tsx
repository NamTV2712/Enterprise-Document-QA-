import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { CollectionsWorkspace, collectionItemFocusId } from "./CollectionsWorkspace";
import { LocaleProvider } from "../../lib/i18n";
import {
  ApiError,
  deleteCollection,
  exportCollection,
  getCollection,
  listCollectionItems,
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
  };
});

const listCollectionsMock = vi.mocked(listCollections);
const getCollectionMock = vi.mocked(getCollection);
const listItemsMock = vi.mocked(listCollectionItems);
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

function renderWorkspace(props: Partial<Parameters<typeof CollectionsWorkspace>[0]> = {}) {
  const onSelectCollection = vi.fn();
  const onOpenDocument = vi.fn<(target: DocumentWorkspaceTarget) => void>();
  const onOpenEvidence = vi.fn<(source: Source, returnFocusId: string) => void>();
  const onOpenMessage = vi.fn();
  render(
    <LocaleProvider>
      <CollectionsWorkspace
        selectedCollectionId={null}
        onSelectCollection={onSelectCollection}
        onOpenDocument={onOpenDocument}
        onOpenEvidence={onOpenEvidence}
        onOpenMessage={onOpenMessage}
        librarySlot={<input id="library-search-input" type="search" aria-label="Search saved conversations" />}
        {...props}
      />
    </LocaleProvider>,
  );
  return { onSelectCollection, onOpenDocument, onOpenEvidence, onOpenMessage };
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(NOW);
  listCollectionsMock.mockReset();
  getCollectionMock.mockReset();
  listItemsMock.mockReset();
  updateCollectionMock.mockReset();
  deleteCollectionMock.mockReset();
  exportCollectionMock.mockReset();
  listItemsMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 });
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
});
