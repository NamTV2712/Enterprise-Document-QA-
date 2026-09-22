import { describe, expect, test } from "vitest";

import { APP_ROUTE_DEFINITIONS, primaryRouteId, resolveAppRoute, routeForWorkspaceView, translateLegacyLocation } from "./routes";

describe("UI-002 route contract", () => {
  test.each(APP_ROUTE_DEFINITIONS)("resolves $path", (definition) => {
    const path = definition.path.replace(":conversationId", "conversation%2F42").replace(":documentId", "AAPL%3A10-K%3A2025").replace(":collectionId", "collection-7").replace(":runId", "run-9");
    expect(resolveAppRoute(path)).toMatchObject({ id: definition.id, isKnown: true });
  });

  test("retains decoded nested route parameters", () => {
    expect(resolveAppRoute("/research/conversation%2F42").params).toEqual({ conversationId: "conversation/42" });
    expect(resolveAppRoute("/documents/AAPL%3A10-K%3A2025").params).toEqual({ documentId: "AAPL:10-K:2025" });
    expect(resolveAppRoute("/pipeline/runs/run-9").params).toEqual({ runId: "run-9" });
    expect(resolveAppRoute("/evaluation/runs/eval-2").params).toEqual({ runId: "eval-2" });
  });

  test("maps known legacy views and preserves query/hash identity", () => {
    expect(translateLegacyLocation("/", "?view=documents&company=AAPL&company=MSFT", "#section=risk")).toBe("/documents?company=AAPL&company=MSFT#section=risk");
    expect(translateLegacyLocation("/", "?view=library&filter=saved", "")).toBe("/collections?filter=saved");
    expect(translateLegacyLocation("/", "?view=architecture", "")).toBe("/settings?panel=architecture");
  });

  test("preserves exact evidence hashes and promotes conversation identity", () => {
    const hash = "#evidence=answer-1-0?conversationId=conversation%2F42&variantId=v1&sourceKey=s%2F1";
    expect(translateLegacyLocation("/", "?view=conversation&lang=vi", hash)).toBe(`/research/conversation%2F42?lang=vi${hash}`);
  });

  test("does not redirect unsupported legacy views or routed locations", () => {
    expect(translateLegacyLocation("/", "?view=users&keep=1", "#unchanged")).toBeNull();
    expect(translateLegacyLocation("/documents", "?view=search", "")).toBeNull();
    expect(resolveAppRoute("/", "?view=users&keep=1")).toMatchObject({ isKnown: false, legacyView: "users" });
  });

  test("keeps chat/research families stable", () => {
    expect(routeForWorkspaceView("conversation", { currentRouteId: "chat", conversationId: "c/1" })).toBe("/chat/c%2F1");
    expect(routeForWorkspaceView("conversation", { currentRouteId: "research", conversationId: "c/1" })).toBe("/research/c%2F1");
    expect(primaryRouteId(resolveAppRoute("/collections/collection-7"))).toBe("collections");
  });

  test("marks deferred and unknown routes truthfully", () => {
    expect(resolveAppRoute("/datasets")).toMatchObject({ isDeferred: false, workspaceView: "datasets" });
    expect(resolveAppRoute("/logs").isDeferred).toBe(true);
    expect(resolveAppRoute("/does-not-exist")).toMatchObject({ id: "not-found", isKnown: false, isDeferred: true });
  });
});
