import { describe, expect, test, vi } from "vitest";
import {
  WorkspaceRepositoryAuthoritySession,
  createWorkspaceTransferClient,
  type WorkspaceRepositoryWriter,
} from "./workspaceRepository";
import { createWorkspaceBackup } from "./workspaceBackup";

function writer(kind: "browser" | "sqlite", write = vi.fn().mockResolvedValue({ ok: true })): WorkspaceRepositoryWriter {
  return { kind, availability: "available", write };
}

describe("WorkspaceRepositoryAuthoritySession", () => {
  test("uses one authoritative writer and switches only explicitly", async () => {
    const browserWrite = vi.fn().mockResolvedValue("browser");
    const sqliteWrite = vi.fn().mockResolvedValue("sqlite");
    const session = new WorkspaceRepositoryAuthoritySession({
      browser: writer("browser", browserWrite),
      sqlite: writer("sqlite", sqliteWrite),
    });

    await expect(session.write("save-conversation", { id: "one" })).resolves.toBe("browser");
    expect(browserWrite).toHaveBeenCalledTimes(1);
    expect(sqliteWrite).not.toHaveBeenCalled();

    session.selectAuthority("sqlite");
    await expect(session.write("save-conversation", { id: "two" })).resolves.toBe("sqlite");
    expect(sqliteWrite).toHaveBeenCalledTimes(1);
    expect(browserWrite).toHaveBeenCalledTimes(1);
  });

  test("does not fall back or dual-write after a SQLite failure", async () => {
    const browserWrite = vi.fn().mockResolvedValue("browser");
    const sqliteWrite = vi.fn().mockRejectedValue(new Error("offline"));
    const session = new WorkspaceRepositoryAuthoritySession({
      browser: writer("browser", browserWrite),
      sqlite: writer("sqlite", sqliteWrite),
      authority: "sqlite",
    });

    await expect(session.write("save-note", { text: "Unsaved research note" })).rejects.toThrow("offline");
    expect(sqliteWrite).toHaveBeenCalledTimes(1);
    expect(browserWrite).not.toHaveBeenCalled();
    expect(session.getState()).toMatchObject({
      authority: "sqlite",
      sqlite: "disconnected",
      unsavedExportable: true,
      unsavedOperationCount: 1,
    });
    expect(session.exportUnsavedOperations()[0].payload).toEqual({ text: "Unsaved research note" });
  });

  test("rejects unavailable authority instead of silently falling back", () => {
    const sqlite = writer("sqlite");
    sqlite.availability = "unavailable";
    const session = new WorkspaceRepositoryAuthoritySession({ browser: writer("browser"), sqlite });
    expect(() => session.selectAuthority("sqlite")).toThrow("not available");
    expect(session.getState().authority).toBe("browser");
  });

  test("constructor rejects an unavailable initial authority", () => {
    const sqlite = writer("sqlite");
    sqlite.availability = "unavailable";
    expect(() =>
      new WorkspaceRepositoryAuthoritySession({ browser: writer("browser"), sqlite, authority: "sqlite" }),
    ).toThrow("not available");
    const browser = writer("browser");
    browser.availability = "unavailable";
    expect(() =>
      new WorkspaceRepositoryAuthoritySession({ browser, sqlite: writer("sqlite") }),
    ).toThrow("not available");
  });

  test("write-time unavailability does not call the writer or record unsaved state", async () => {
    const sqliteWrite = vi.fn().mockResolvedValue("sqlite");
    const sqlite = writer("sqlite", sqliteWrite);
    const session = new WorkspaceRepositoryAuthoritySession({
      browser: writer("browser"),
      sqlite,
      authority: "sqlite",
    });
    session.setAvailability("sqlite", "unavailable");

    await expect(session.write("save-conversation", { id: "one" })).rejects.toThrow("unavailable");
    expect(sqliteWrite).not.toHaveBeenCalled();
    expect(session.getState()).toMatchObject({
      authority: "sqlite",
      sqlite: "unavailable",
      unsavedExportable: false,
      unsavedOperationCount: 0,
    });
  });

  test("a browser write failure records unsaved work without disconnecting the browser writer", async () => {
    const browserWrite = vi.fn().mockRejectedValue(new Error("quota exceeded"));
    const session = new WorkspaceRepositoryAuthoritySession({
      browser: writer("browser", browserWrite),
      sqlite: writer("sqlite"),
    });

    await expect(session.write("save-answer-version", { id: "v1" })).rejects.toThrow("quota exceeded");
    expect(session.getState()).toMatchObject({
      authority: "browser",
      browser: "available",
      unsavedExportable: true,
      unsavedOperationCount: 1,
    });
  });

  test("accumulates unsaved operations and exports deep copies", async () => {
    const sqliteWrite = vi.fn().mockRejectedValue(new Error("offline"));
    const session = new WorkspaceRepositoryAuthoritySession({
      browser: writer("browser"),
      sqlite: writer("sqlite", sqliteWrite),
      authority: "sqlite",
    });

    await expect(session.write("op-one", { n: 1 })).rejects.toThrow("offline");
    session.setAvailability("sqlite", "available");
    await expect(session.write("op-two", { n: 2 })).rejects.toThrow("offline");
    expect(session.getState()).toMatchObject({ unsavedExportable: true, unsavedOperationCount: 2 });

    const exported = session.exportUnsavedOperations();
    expect(exported.map((operation) => operation.payload)).toEqual([{ n: 1 }, { n: 2 }]);
    exported[0].payload = { mutated: true };
    expect(session.exportUnsavedOperations()[0].payload).toEqual({ n: 1 });
  });

  test("dispatches concurrent writes only to the authoritative writer in order", async () => {
    const order: string[] = [];
    const sqliteWrite = vi.fn().mockImplementation(async (_operation: string, payload: { n: number }) => {
      order.push(`sqlite:${payload.n}`);
      return "sqlite";
    });
    const browserWrite = vi.fn().mockImplementation(async (_operation: string, payload: { n: number }) => {
      order.push(`browser:${payload.n}`);
      return "browser";
    });
    const session = new WorkspaceRepositoryAuthoritySession({
      browser: writer("browser", browserWrite),
      sqlite: writer("sqlite", sqliteWrite),
      authority: "sqlite",
    });

    await Promise.all([session.write("op-a", { n: 1 }), session.write("op-b", { n: 2 })]);
    expect(sqliteWrite).toHaveBeenCalledTimes(2);
    expect(browserWrite).not.toHaveBeenCalled();
    expect(order).toEqual(["sqlite:1", "sqlite:2"]);
  });

  test("re-switching to a disconnected repository requires explicit availability restoration", async () => {
    const sqliteWrite = vi.fn().mockRejectedValue(new Error("offline"));
    const browserWrite = vi.fn().mockResolvedValue("browser");
    const session = new WorkspaceRepositoryAuthoritySession({
      browser: writer("browser", browserWrite),
      sqlite: writer("sqlite", sqliteWrite),
      authority: "sqlite",
    });

    await expect(session.write("op", { id: 1 })).rejects.toThrow("offline");
    expect(() => session.selectAuthority("sqlite")).toThrow("not available");

    session.selectAuthority("browser");
    await expect(session.write("op", { id: 2 })).resolves.toBe("browser");
    expect(sqliteWrite).toHaveBeenCalledTimes(1);
    expect(browserWrite).toHaveBeenCalledTimes(1);

    session.setAvailability("sqlite", "available");
    session.selectAuthority("sqlite");
    expect(session.getState().authority).toBe("sqlite");
  });
});
describe("workspace transfer client", () => {
  test("keeps the bearer token caller-owned and binds import to the preview digest", async () => {
    const backup = await createWorkspaceBackup({
      conversations: [], tombstones: [], collections: [], favoriteCollectionIds: [],
    }, "2025-01-01T00:00:00Z");
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ digest: backup.digest }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...backup, status: "committed" }), { status: 200 }));
    const client = createWorkspaceTransferClient({
      apiBaseUrl: "http://localhost:8000/",
      getBearerToken: () => "memory-only-token",
      fetchImpl,
    });

    await client.preview(backup);
    await client.importBackup(backup, backup.digest);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    expect(fetchImpl.mock.calls[0][1].headers.Authorization).toBe("Bearer memory-only-token");
    expect(fetchImpl.mock.calls[1][1].body).toContain(backup.digest);
    await expect(client.importBackup(backup, "f".repeat(64))).rejects.toThrow("Preview digest");
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });
});
