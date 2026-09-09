import { describe, expect, test } from "vitest";

import { getResearchTemplateCopy, RESEARCH_TEMPLATES } from "./researchTemplates";

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
});
