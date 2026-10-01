import { describe, expect, test } from "vitest";
import { COMMAND_REGISTRY } from "./commandRegistry";
import { getWorkspaceNavItem, WORKSPACE_NAV_SECTIONS, WORKSPACE_VIEWS } from "./workspace";
import { SHELL_NAVIGATION_SECTIONS } from "../app/routes";

describe("workspace navigation registry", () => {
  test("exposes the exact four navigation groups and only real views", () => {
    expect(WORKSPACE_NAV_SECTIONS.map((section) => section.id)).toEqual([
      "workspace",
      "retrieval",
      "evaluate",
      "system",
    ]);

    const registeredViews = WORKSPACE_NAV_SECTIONS.flatMap((section) =>
      section.items.map((item) => item.view),
    );

    expect(new Set(registeredViews).size).toBe(registeredViews.length);
    expect(registeredViews).toEqual(WORKSPACE_VIEWS);
    expect(registeredViews).not.toContain("tools");
    expect(registeredViews as readonly string[]).not.toContain("research");

    const currentConversation = WORKSPACE_NAV_SECTIONS[0].items[1];
    expect(currentConversation.view).toBe("conversation");
    expect(currentConversation.nested).toBe(true);
    expect(currentConversation.requiresMessages).toBe(true);
  });

  test("derives navigation palette commands from the same registry", () => {
    const navigation = COMMAND_REGISTRY.filter((command) => command.kind === "navigation");
    const shellRoutes = SHELL_NAVIGATION_SECTIONS.flatMap((section) => section.items.map((item) => item.routeId));
    expect(navigation.map((command) => command.routeId)).toEqual(shellRoutes);
    expect(navigation.find((command) => command.routeId === "research")?.labelKey).toBe("nav.research");
    expect(navigation.find((command) => command.routeId === "chat")?.labelKey).toBe("nav.chat");
  });

  test("keeps tool introductions bound to registered icon and description metadata", () => {
    for (const view of WORKSPACE_VIEWS) {
      const item = getWorkspaceNavItem(view);
      expect(item.icon).toBeTruthy();
      expect(item.descriptionKey).toMatch(/^nav\..+Description$/);
    }
  });
});
