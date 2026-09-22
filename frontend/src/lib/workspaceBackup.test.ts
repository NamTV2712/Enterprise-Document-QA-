import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";
import type { ConversationRecord } from "./conversationStore";
import type { EvidenceCollection } from "./evidenceCollections";
import {
  MAX_WORKSPACE_BACKUP_BYTES,
  WORKSPACE_BACKUP_FORMAT,
  canonicalWorkspaceJson,
  compareUnicodeCodePoints,
  computeWorkspaceBackupDigest,
  createWorkspaceBackup,
  parseWorkspaceBackupJson,
  serializeWorkspaceBackup,
  validateWorkspaceBackup,
  type WorkspaceBackup,
} from "./workspaceBackup";

const fixtureCandidates = [
  resolve(process.cwd(), "..", "tests", "fixtures", "workspace_transfer_roundtrip.json"),
  resolve(process.cwd(), "tests", "fixtures", "workspace_transfer_roundtrip.json"),
];
const fixturePath = fixtureCandidates.find((candidate) => existsSync(candidate));
if (!fixturePath) throw new Error("The shared workspace transfer fixture is missing.");
const transferFixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  fixtures: Array<{ id: string; backup: WorkspaceBackup }>;
};

const conversation: ConversationRecord = {
  schemaVersion: 4,
  id: "conversation-1",
  sessionId: "session-1",
  title: "Revenue review",
  titleMode: "custom",
  revision: 3,
  createdAt: 1_700_000_000_000,
  updatedAt: 1_700_000_000_003,
  messages: [
    { id: "question-1", sender: "user", text: "How did revenue change?" },
    {
      id: "answer-1",
      sender: "assistant",
      text: "Revenue increased [1].",
      sources: [{
        citation: "AAPL 10-K [Source 1]",
        score: 0.91,
        text_preview: "Exact excerpt",
        text: "Exact excerpt",
        chunk_id: "chunk-1",
        document_id: "document-1",
        chunk_text_hash: "sha256:exact",
        stored_snapshot: {
          document_revision: "document-revision-1",
          source_set_revision: "source-set-1",
        },
      }],
    },
  ],
  draft: "",
  bookmarkedMessageIds: ["answer-1"],
  tags: ["revenue"],
  notes: [{ id: "note-1", text: "Review", createdAt: 1_700_000_000_000, updatedAt: 1_700_000_000_000 }],
  variants: [{
    id: "variant-1",
    originMessageId: "answer-1",
    text: "Alternative [1].",
    answerLanguage: "en",
    status: "completed",
    createdAt: 1_700_000_000_001,
    updatedAt: 1_700_000_000_001,
    sources: [{ citation: "AAPL 10-K [Source 1]", score: 0.9, text_preview: "Exact", chunk_id: "chunk-1", document_id: "document-1" }],
  }],
};

const legacyCollection: EvidenceCollection = {
  id: "collection-1",
  name: "Revenue evidence",
  createdAt: 1_700_000_000_000,
  updatedAt: 1_700_000_000_010,
  items: [{
    id: "evidence-1",
    citation: "AAPL 10-K [Source 1]",
    excerpt: "Exact excerpt",
    chunkId: "chunk-1",
    sourceConversationId: "conversation-1",
    sourceMessageId: "answer-1",
    documentId: "document-1",
    documentRevision: "document-revision-1",
    sourceSetRevision: "source-set-1",
    chunkTextHash: "sha256:exact",
    note: "Use in memo",
    savedAt: 1_700_000_000_005,
  }],
};

describe("portable workspace backup", () => {
  test("exports current conversations plus legacy evidence, notes, favorites, and tombstones", async () => {
    const backup = await createWorkspaceBackup({
      conversations: [conversation],
      tombstones: [{ id: "deleted-conversation", revision: 4, deletedAt: 1_700_000_000_020 }],
      collections: [legacyCollection],
      favoriteCollectionIds: ["collection-1"],
    }, "2025-01-01T00:00:00Z");

    expect(backup.format).toBe(WORKSPACE_BACKUP_FORMAT);
    expect(backup.source_schemas).toEqual({
      conversations: [4], evidence_collections: [1], favorites: [1], tombstones: [1],
    });
    expect(backup.source_counts).toEqual({
      conversations: 1, collections: 1, evidence_items: 1, favorites: 1, tombstones: 1, unsupported: 0,
    });
    expect(backup.conversations[0].payload.messages).toEqual(conversation.messages);
    expect(backup.conversations[0].payload.variants).toEqual(conversation.variants);
    expect(backup.evidence_items[0].payload).toEqual(legacyCollection.items[0]);
    expect(backup.favorites).toEqual(["collection-1"]);
    expect(backup.tombstones[0].legacy_id).toBe("deleted-conversation");
    await expect(parseWorkspaceBackupJson(serializeWorkspaceBackup(backup))).resolves.toEqual(backup);
  });

  test("produces a deterministic digest independent of export timestamp and input order", async () => {
    const first = await createWorkspaceBackup({
      conversations: [conversation], tombstones: [], collections: [legacyCollection], favoriteCollectionIds: ["collection-1"],
    }, "2025-01-01T00:00:00Z");
    const second = await createWorkspaceBackup({
      conversations: [conversation], tombstones: [], collections: [legacyCollection], favoriteCollectionIds: ["collection-1"],
    }, "2026-01-01T00:00:00Z");
    expect(first.digest).toBe(second.digest);
  });

  test("reports unsupported browser sources without including their raw bytes", async () => {
    const backup = await createWorkspaceBackup({
      conversations: [], tombstones: [], collections: [], favoriteCollectionIds: [],
      unsupported: [{ source: "indexeddb.conversations", schema_version: 5, count: 2, reason: "Future schema left untouched." }],
    }, "2025-01-01T00:00:00Z");
    expect(backup.source_counts.unsupported).toBe(2);
    expect(JSON.stringify(backup)).not.toContain("rawValue");
  });

  test("rejects future envelope versions, digest changes, secrets, and oversized input", async () => {
    const backup = await createWorkspaceBackup({
      conversations: [], tombstones: [], collections: [], favoriteCollectionIds: [],
    }, "2025-01-01T00:00:00Z");
    await expect(validateWorkspaceBackup({ ...backup, version: 2 })).rejects.toThrow("not supported");
    await expect(validateWorkspaceBackup({ ...backup, digest: "0".repeat(64) })).rejects.toThrow("digest");
    await expect(validateWorkspaceBackup({ ...backup, api_key: "secret" })).rejects.toThrow("schema");
    await expect(parseWorkspaceBackupJson(`{"padding":"${"x".repeat(MAX_WORKSPACE_BACKUP_BYTES)}"}`)).rejects.toThrow("25 MiB");
  });

  test.each(transferFixture.fixtures)("$id reproduces the Python-computed shared fixture digest", async ({ backup }) => {
    await expect(validateWorkspaceBackup(backup)).resolves.toMatchObject({ digest: backup.digest });
    // exported_at stays in the payload on purpose: the digest must exclude it.
    const { digest: _digest, ...payload } = backup;
    await expect(computeWorkspaceBackupDigest(payload)).resolves.toBe(backup.digest);
  });

  test("orders object keys by Unicode code points, not UTF-16 code units", () => {
    expect(compareUnicodeCodePoints("\uE000-zone", "\u{1F600}-alpha")).toBeLessThan(0);
    const canonical = canonicalWorkspaceJson({ "\u{1F600}-alpha": 1, "\uE000-zone": 2, ascii: 3 });
    expect(canonical).toBe('{"ascii":3,"\uE000-zone":2,"\uD83D\uDE00-alpha":1}');
  });

  test("serializes numbers with the ECMAScript JSON.stringify contract", () => {
    expect(canonicalWorkspaceJson({ integral: 5.0, score: 0.91, tiny: 1e-7, big: 1.5e21 })).toBe(
      '{"big":1.5e+21,"integral":5,"score":0.91,"tiny":1e-7}',
    );
  });

  test("rejects unpaired surrogates instead of silently replacing them", async () => {
    const backup = await createWorkspaceBackup({
      conversations: [], tombstones: [], collections: [], favoriteCollectionIds: [],
    }, "2025-01-01T00:00:00Z");
    const poisoned = JSON.parse(JSON.stringify(backup)) as WorkspaceBackup;
    poisoned.conversations = [{
      legacy_id: "conversation-bad",
      schema_version: 4,
      revision: 1,
      created_at: 1_700_000_000_000,
      updated_at: 1_700_000_000_000,
      payload: { id: "conversation-bad", schemaVersion: 4, note: "bad \uD800 surrogate" },
    }];
    await expect(validateWorkspaceBackup(poisoned)).rejects.toThrow("unpaired surrogate");
  });
});
