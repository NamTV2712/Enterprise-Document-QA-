import { describe, expect, test } from "vitest";
import { buildRelatedResearchSuggestions } from "./relatedResearch";
import type { Message } from "../types";

const answer: Message = {
  id: "answer-1",
  sender: "assistant",
  text: "Revenue was reported in the financial table.",
  requestSnapshot: { ticker: "AAPL", section: "financial_table", topK: 5, enableComparative: false, answerLanguage: "en" },
  sources: [{ citation: "AAPL filing", ticker: "AAPL", section: "financial_table", text_preview: "Revenue" }],
};

describe("buildRelatedResearchSuggestions", () => {
  test("uses current identity and available sections without inventing filings", () => {
    const suggestions = buildRelatedResearchSuggestions(answer, ["financial_table", "risk_factors"]);
    expect(suggestions.map((item) => item.id)).toEqual(["source-audit", "section-risk_factors"]);
    expect(suggestions[1]?.scope).toEqual({ ticker: "AAPL", section: "risk_factors" });
    expect(suggestions[1]?.question.en).toContain("AAPL");
    expect(suggestions.map((item) => item.question.en).join(" ")).not.toMatch(/earlier|previous|2023|2024/iu);
  });

  test("returns no suggestions for incomplete or non-assistant messages", () => {
    expect(buildRelatedResearchSuggestions({ ...answer, sender: "user" })).toEqual([]);
    expect(buildRelatedResearchSuggestions({ ...answer, text: "" })).toEqual([]);
    expect(buildRelatedResearchSuggestions({ ...answer, error: true })).toEqual([]);
  });
});
