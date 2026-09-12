import { describe, expect, test } from "vitest";

import {
  getResearchTemplateCopy,
  getResearchTemplateSchema,
  hasUnresolvedTemplatePlaceholders,
  isSendableResearchQuestion,
  renderResearchTemplate,
  deriveResearchTemplateScope,
  RESEARCH_TEMPLATES,
  validateResearchTemplateValues,
} from "./researchTemplates";

describe("research templates", () => {
  test("uses one stable ID per intent with a complete scope preset", () => {
    const ids = RESEARCH_TEMPLATES.map((template) => template.id);

    expect(new Set(ids).size).toBe(ids.length);
    expect(ids.every((id) => !id.startsWith("en-") && !id.startsWith("vi-"))).toBe(true);
    for (const template of RESEARCH_TEMPLATES) {
      expect(template.copy.en.question).toBeTruthy();
      expect(template.copy.vi.question).toBeTruthy();
      expect(Object.keys(template.scope).sort()).toEqual(["enableComparative", "section", "ticker", "topK"]);
      expect(template.scope.ticker === null || typeof template.scope.ticker === "string").toBe(true);
      expect(template.scope.section === null || typeof template.scope.section === "string").toBe(true);
      expect(typeof template.scope.topK).toBe("number");
      expect(typeof template.scope.enableComparative).toBe("boolean");
    }
  });

  test("resolves copy without changing the template identity", () => {
    const template = RESEARCH_TEMPLATES.find((candidate) => candidate.id === "risk-groups");
    expect(template).toBeDefined();
    expect(getResearchTemplateCopy(template!, "en").label).toBe("Risk groups");
    expect(getResearchTemplateCopy(template!, "vi").label).toBe("Nhóm rủi ro");
    expect(template?.id).toBe("risk-groups");
  });

  test("defines bounded, deterministic parameter schemas for every guided template", () => {
    const schemas = RESEARCH_TEMPLATES.map((template) => [template.id, getResearchTemplateSchema(template)] as const);

    expect(schemas.find(([id]) => id === "revenue-fact")?.[1].map((parameter) => parameter.key)).toEqual(["company", "year"]);
    expect(schemas.find(([id]) => id === "dependency-comparison")?.[1].map((parameter) => parameter.key)).toEqual([
      "companyA",
      "companyB",
      "metric",
      "year",
    ]);
    expect(schemas.find(([id]) => id === "source-audit")?.[1].find((parameter) => parameter.key === "claim")?.required).toBe(true);
    expect(schemas.every(([, schema]) => schema.every((parameter) => parameter.label.en && parameter.label.vi))).toBe(true);
  });

  test("validates available tickers, years, bounded text, and comparison identity", () => {
    const dependency = RESEARCH_TEMPLATES.find((template) => template.id === "dependency-comparison")!;
    expect(validateResearchTemplateValues(dependency, {
      companyA: "aapl",
      companyB: "msft",
      metric: "cloud infrastructure",
      year: "2024",
    }, ["AAPL", "MSFT"], 2026).valid).toBe(true);
    expect(validateResearchTemplateValues(dependency, {
      companyA: "AAPL",
      companyB: "AAPL",
      metric: "revenue",
    }, ["AAPL", "MSFT"], 2026).issues).toContainEqual({ key: "companyB", code: "duplicate-company" });
    expect(validateResearchTemplateValues(dependency, {
      companyA: "AAPL",
      companyB: "MSFT",
      metric: "revenue",
      year: "2027",
    }, ["AAPL", "MSFT"], 2026).issues).toContainEqual({ key: "year", code: "invalid-year" });
  });

  test("derives a single-company scope while preserving comparative scope semantics", () => {
    const revenue = RESEARCH_TEMPLATES.find((template) => template.id === "revenue-fact")!;
    expect(deriveResearchTemplateScope(revenue, { company: "aapl", year: "2024" })).toEqual({
      ticker: "AAPL",
      section: "financial_table",
      topK: 5,
      enableComparative: false,
    });

    const dependency = RESEARCH_TEMPLATES.find((template) => template.id === "dependency-comparison")!;
    expect(deriveResearchTemplateScope(dependency, {
      companyA: "AAPL",
      companyB: "MSFT",
      metric: "revenue",
    })).toEqual(dependency.scope);
  });

  test("renders localized questions and only reserves known template tokens", () => {
    const template = RESEARCH_TEMPLATES.find((candidate) => candidate.id === "source-audit")!;
    const question = renderResearchTemplate(template, "vi", {
      company: "AAPL",
      claim: "Doanh thu tăng trong năm",
      year: "2024",
    });

    expect(question).toContain("AAPL");
    expect(question).toContain("2024");
    expect(hasUnresolvedTemplatePlaceholders(question)).toBe(false);
    expect(hasUnresolvedTemplatePlaceholders("Explain [anything] in the filing")).toBe(false);
  });

  test("replaces localized template tokens before Apply", () => {
    const template = RESEARCH_TEMPLATES.find((candidate) => candidate.id === "revenue-fact")!;
    const question = renderResearchTemplate(template, "vi", { company: "AAPL", year: "2024" });

    expect(question).toBe("AAPL báo cáo tổng doanh thu bao nhiêu trong 2024?");
    expect(hasUnresolvedTemplatePlaceholders(question)).toBe(false);
  });

  test("blocks only unresolved reserved placeholders at the send boundary", () => {
    expect(isSendableResearchQuestion("What did AAPL report in 2024?")).toBe(true);
    expect(isSendableResearchQuestion("Explain [anything] in the filing.")).toBe(true);
    expect(isSendableResearchQuestion("What did [company] report in 2024?")).toBe(false);
    expect(isSendableResearchQuestion("x")).toBe(false);
  });
});
