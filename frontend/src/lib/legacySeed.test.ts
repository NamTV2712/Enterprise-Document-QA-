import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { ConversationRecord } from "./conversationStore";
import { isLegacySeedRecord, isPristineLegacySeedRecord } from "./legacySeed";

const userText = "What are Apple's main risks mentioned in the 2024 10-K?";
const assistantText = `Based on the 2024 10-K filing, Apple's main risks include:

1. **Macroeconomic and geopolitical risks**
Global economic conditions, inflation, interest rates, and geopolitical conflicts could negatively impact demand for Apple's products and services. [1]

2. **Supply chain disruptions**
Dependence on third-party manufacturers and suppliers may lead to delays, higher costs, or shortages. [2]

3. **Regulatory and legal risks**
Increased regulation, litigation, and changes in laws (e.g., privacy, antitrust, tax) could affect the business. [3]

4. **Competition**
Intense competition in key markets, including smartphones, services, and AI. [4]

5. **Cybersecurity and data privacy**
Risks of data breaches, cyberattacks, and privacy violations could harm reputation and result in financial losses. [5]`;

const sources = [
  {
    citation: "Apple 10-K 2024 (p. 12)",
    document_id: "aapl-2024-10k",
    chunk_id: "aapl-10k-2024-p12",
    ticker: "AAPL",
    section: "risk_factors",
    score: 0.892,
    filing_date: "2024-11-01",
    text_preview: "Macroeconomic conditions, including inflation, interest rates, and global trade...",
    text: "Our business, results of operations, and financial condition could be adversely affected by macroeconomic conditions, including inflation, interest rates, and global trade tensions, as well as geopolitical conflicts, which could negatively impact demand for our products and services. Global economic conditions remain uncertain, and adverse developments in the U.S. or international markets could reduce consumer spending, increase our costs, and disrupt our supply chain.",
  },
  {
    citation: "Apple 10-K 2024 (p. 28)",
    document_id: "aapl-2024-10k",
    chunk_id: "aapl-10k-2024-p28",
    ticker: "AAPL",
    section: "risk_factors",
    score: 0.861,
    filing_date: "2024-11-01",
    text_preview: "Apple's supply chain relies on a limited number of third-party manufacturers...",
    text: "Apple's supply chain relies on a limited number of third-party manufacturers and suppliers, which leaves operations vulnerable to component shortages and shipping disruptions.",
  },
  {
    citation: "Apple 10-K 2024 (p. 45)",
    document_id: "aapl-2024-10k",
    chunk_id: "aapl-10k-2024-p45",
    ticker: "AAPL",
    section: "risk_factors",
    score: 0.823,
    filing_date: "2024-11-01",
    text_preview: "Regulatory developments, including privacy and antitrust laws, may increase...",
    text: "Regulatory developments, including privacy and antitrust laws, may increase compliance obligations and subject the Company to investigations, fines, and operational changes.",
  },
  {
    citation: "Apple 10-K 2024 (p. 67)",
    document_id: "aapl-2024-10k",
    chunk_id: "aapl-10k-2024-p67",
    ticker: "AAPL",
    section: "risk_factors",
    score: 0.781,
    filing_date: "2024-11-01",
    text_preview: "The company faces intense competition in smartphones, wearables, and services...",
    text: "The company faces intense competition in smartphones, wearables, and services, including rapid advancements in artificial intelligence from global technology competitors.",
  },
  {
    citation: "Apple 10-K 2024 (p. 88)",
    document_id: "aapl-2024-10k",
    chunk_id: "aapl-10k-2024-p88",
    ticker: "AAPL",
    section: "risk_factors",
    score: 0.742,
    filing_date: "2024-11-01",
    text_preview: "Cybersecurity risks, including data breaches and system disruptions...",
    text: "Cybersecurity risks, including data breaches and system disruptions, could compromise proprietary information, degrade customer trust, and lead to substantial liability.",
  },
];

function createLegacyRecord(): ConversationRecord {
  return {
    schemaVersion: 4,
    id: "conversation-legacy",
    sessionId: "session-legacy",
    title: userText,
    titleMode: "auto",
    revision: 1,
    createdAt: 1,
    updatedAt: 1,
    messages: [
      { id: "sample-msg-user-1", sender: "user", text: userText },
      {
        id: "sample-msg-asst-1",
        sender: "assistant",
        text: assistantText,
        sources,
        model_used: "GPT-4o",
        numChunks: 5,
      },
    ],
    draft: "",
    bookmarkedMessageIds: [],
    tags: [],
    notes: [],
    variants: [],
  };
}

describe("legacy startup example migration guard", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", webcrypto);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("accepts only the exact untouched legacy record", async () => {
    const record = createLegacyRecord();

    expect(isLegacySeedRecord(record)).toBe(true);
    await expect(isPristineLegacySeedRecord(record)).resolves.toBe(true);
  });

  test.each([
    ["edited answer", (record: ConversationRecord) => { record.messages[1].text += " edited"; }],
    ["edited source", (record: ConversationRecord) => { record.messages[1].sources![0].text_preview += " edited"; }],
    ["custom title", (record: ConversationRecord) => { record.title = "My research"; record.titleMode = "custom"; }],
    ["bookmark", (record: ConversationRecord) => { record.bookmarkedMessageIds = ["sample-msg-asst-1"]; }],
    ["note", (record: ConversationRecord) => { record.notes = [{ id: "note-1", text: "Keep this", createdAt: 1, updatedAt: 1 }]; }],
    ["answer variant", (record: ConversationRecord) => { record.variants = [{ id: "variant-1", originMessageId: "sample-msg-asst-1", text: "saved", sources: [], answerLanguage: "en", status: "completed", createdAt: 1, updatedAt: 1 }]; }],
  ])("preserves a %s modification", async (_label, mutate) => {
    const record = createLegacyRecord();
    mutate(record);

    await expect(isPristineLegacySeedRecord(record)).resolves.toBe(false);
    expect(isLegacySeedRecord(record)).toBe(true);
  });
});
