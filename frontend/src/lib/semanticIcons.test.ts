import { describe, expect, it } from "vitest";

import { getSemanticIcon, SEMANTIC_ICONS } from "./semanticIcons";
import { WORKSPACE_NAV_SECTIONS } from "./workspace";

describe("semantic icon registry", () => {
  it("keeps distinct domain icons for the screenshot conflicts", () => {
    expect(getSemanticIcon("evaluation")).not.toBe(getSemanticIcon("analytics"));
    expect(getSemanticIcon("research")).not.toBe(getSemanticIcon("library"));
  });

  it("gives every workspace route one shared icon and description contract", () => {
    const routes = WORKSPACE_NAV_SECTIONS.flatMap((section) => section.items);
    expect(routes.every((route) => route.descriptionKey && SEMANTIC_ICONS[route.icon])).toBe(true);
    expect(routes.find((route) => route.view === "system")?.icon).toBe("system");
    expect(routes.find((route) => route.view === "documents")?.icon).toBe("documents");
  });
});
