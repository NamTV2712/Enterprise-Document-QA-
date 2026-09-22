import { matchPath } from "react-router-dom";

import type { MessageKey } from "../lib/i18n";
import type { SemanticIconKey } from "../lib/semanticIcons";
import { parseEvidenceDeepLink } from "../lib/evidenceDeepLink";
import { isWorkspaceView, type WorkspaceView } from "../lib/workspace";

export type AppRouteId =
  | "legacy-root" | "chat" | "chat-conversation" | "research" | "research-conversation"
  | "documents" | "document-detail" | "search" | "collections" | "collection-detail"
  | "retrieval" | "models" | "pipeline" | "pipeline-run" | "reranker"
  | "evaluation" | "evaluation-run" | "analytics" | "datasets" | "settings" | "logs"
  | "not-found";

export type ShellRouteId = Exclude<AppRouteId,
  | "legacy-root" | "chat-conversation" | "research-conversation" | "document-detail"
  | "collection-detail" | "pipeline-run" | "evaluation-run" | "not-found">;

export interface AppRouteDefinition {
  id: AppRouteId;
  path: string;
  workspaceView: WorkspaceView;
}

export interface ResolvedAppRoute extends AppRouteDefinition {
  params: Readonly<Record<string, string>>;
  isKnown: boolean;
  isDeferred: boolean;
  legacyView: string | null;
}

export interface ShellNavigationItem {
  routeId: ShellRouteId;
  path: string;
  labelKey: MessageKey;
  descriptionKey: MessageKey;
  icon: SemanticIconKey;
  accentFamily: "research" | "documents" | "retrieval" | "evaluation" | "analytics" | "system";
  availability: "available" | "partial" | "deferred";
}

export interface ShellNavigationSection {
  id: "workspace" | "build" | "evaluate" | "manage";
  labelKey: MessageKey;
  items: readonly ShellNavigationItem[];
}

export const APP_ROUTE_DEFINITIONS: readonly AppRouteDefinition[] = [
  { id: "chat-conversation", path: "/chat/:conversationId", workspaceView: "conversation" },
  { id: "chat", path: "/chat", workspaceView: "conversation" },
  { id: "research-conversation", path: "/research/:conversationId", workspaceView: "conversation" },
  { id: "research", path: "/research", workspaceView: "overview" },
  { id: "document-detail", path: "/documents/:documentId", workspaceView: "documents" },
  { id: "documents", path: "/documents", workspaceView: "documents" },
  { id: "search", path: "/search", workspaceView: "search" },
  { id: "collection-detail", path: "/collections/:collectionId", workspaceView: "library" },
  { id: "collections", path: "/collections", workspaceView: "library" },
  { id: "retrieval", path: "/retrieval", workspaceView: "retrieval" },
  { id: "models", path: "/models", workspaceView: "models" },
  { id: "pipeline-run", path: "/pipeline/runs/:runId", workspaceView: "pipeline" },
  { id: "pipeline", path: "/pipeline", workspaceView: "pipeline" },
  { id: "reranker", path: "/reranker", workspaceView: "retrieval" },
  { id: "evaluation-run", path: "/evaluation/runs/:runId", workspaceView: "evaluation" },
  { id: "evaluation", path: "/evaluation", workspaceView: "evaluation" },
  { id: "analytics", path: "/analytics", workspaceView: "analytics" },
  { id: "datasets", path: "/datasets", workspaceView: "datasets" },
  { id: "settings", path: "/settings", workspaceView: "system" },
  { id: "logs", path: "/logs", workspaceView: "system" },
] as const;

export const SHELL_NAVIGATION_SECTIONS: readonly ShellNavigationSection[] = [
  {
    id: "workspace", labelKey: "nav.groupWorkspace", items: [
      { routeId: "chat", path: "/chat", labelKey: "nav.chat", descriptionKey: "nav.chatDescription", icon: "conversation", accentFamily: "research", availability: "available" },
      { routeId: "research", path: "/research", labelKey: "nav.research", descriptionKey: "nav.researchDescription", icon: "research", accentFamily: "research", availability: "available" },
      { routeId: "documents", path: "/documents", labelKey: "nav.documents", descriptionKey: "nav.documentsDescription", icon: "documents", accentFamily: "documents", availability: "available" },
      { routeId: "search", path: "/search", labelKey: "nav.search", descriptionKey: "nav.searchDescription", icon: "search", accentFamily: "retrieval", availability: "available" },
      { routeId: "collections", path: "/collections", labelKey: "nav.collections", descriptionKey: "nav.collectionsDescription", icon: "library", accentFamily: "documents", availability: "available" },
    ],
  },
  {
    id: "build", labelKey: "nav.groupBuild", items: [
      { routeId: "retrieval", path: "/retrieval", labelKey: "nav.retrieval", descriptionKey: "nav.retrievalDescription", icon: "retrieval", accentFamily: "retrieval", availability: "available" },
      { routeId: "models", path: "/models", labelKey: "nav.models", descriptionKey: "nav.modelsDescription", icon: "models", accentFamily: "retrieval", availability: "available" },
      { routeId: "pipeline", path: "/pipeline", labelKey: "nav.pipeline", descriptionKey: "nav.pipelineDescription", icon: "pipeline", accentFamily: "retrieval", availability: "available" },
      { routeId: "reranker", path: "/reranker", labelKey: "nav.reranker", descriptionKey: "nav.rerankerDescription", icon: "retrieval", accentFamily: "retrieval", availability: "available" },
    ],
  },
  {
    id: "evaluate", labelKey: "nav.groupEvaluate", items: [
      { routeId: "evaluation", path: "/evaluation", labelKey: "nav.evaluation", descriptionKey: "nav.evaluationDescription", icon: "evaluation", accentFamily: "evaluation", availability: "available" },
      { routeId: "analytics", path: "/analytics", labelKey: "nav.analytics", descriptionKey: "nav.analyticsDescription", icon: "analytics", accentFamily: "analytics", availability: "available" },
      { routeId: "datasets", path: "/datasets", labelKey: "nav.datasets", descriptionKey: "nav.datasetsDescription", icon: "documents", accentFamily: "evaluation", availability: "available" },
    ],
  },
  {
    id: "manage", labelKey: "nav.groupManage", items: [
      { routeId: "settings", path: "/settings", labelKey: "nav.settings", descriptionKey: "nav.settingsDescription", icon: "system", accentFamily: "system", availability: "available" },
      { routeId: "logs", path: "/logs", labelKey: "nav.logs", descriptionKey: "nav.logsDescription", icon: "system", accentFamily: "system", availability: "deferred" },
    ],
  },
] as const;

const LEGACY_VIEW_TO_ROUTE: Readonly<Record<WorkspaceView, ShellRouteId>> = {
  overview: "research", conversation: "research", search: "search", documents: "documents",
  library: "collections", retrieval: "retrieval", architecture: "settings", evaluation: "evaluation",
  analytics: "analytics", system: "settings", models: "models", pipeline: "pipeline",
  datasets: "datasets",
};

const DEFERRED_ROUTE_IDS = new Set<AppRouteId>(["logs"]);

function safeDecode(value: string): string {
  try { return decodeURIComponent(value); } catch { return value; }
}

function matchedParams(params: Record<string, string | undefined>): Readonly<Record<string, string>> {
  return Object.fromEntries(Object.entries(params).flatMap(([key, value]) => value === undefined ? [] : [[key, safeDecode(value)]]));
}

export function resolveAppRoute(pathname: string, search = "", hash = ""): ResolvedAppRoute {
  for (const definition of APP_ROUTE_DEFINITIONS) {
    const match = matchPath({ path: definition.path, end: true, caseSensitive: false }, pathname);
    if (!match) continue;
    const query = new URLSearchParams(search);
    const workspaceView = definition.id === "research" && query.get("mode") === "conversation"
      ? "conversation"
      : definition.id === "settings" && query.get("panel") === "architecture"
        ? "architecture"
        : definition.workspaceView;
    return { ...definition, workspaceView, params: matchedParams(match.params), isKnown: true, isDeferred: DEFERRED_ROUTE_IDS.has(definition.id), legacyView: null };
  }

  if (pathname === "/" || pathname === "") {
    const query = new URLSearchParams(search);
    const legacyView = query.get("view");
    const parsedView = isWorkspaceView(legacyView) ? legacyView : "overview";
    const evidence = parseEvidenceDeepLink(hash);
    return {
      id: "legacy-root", path: "/", workspaceView: evidence ? "conversation" : parsedView,
      params: evidence?.conversationId ? { conversationId: evidence.conversationId } : {},
      isKnown: legacyView === null || isWorkspaceView(legacyView), isDeferred: false, legacyView,
    };
  }

  return { id: "not-found", path: pathname, workspaceView: "overview", params: {}, isKnown: false, isDeferred: true, legacyView: null };
}

export function routePath(routeId: ShellRouteId): string {
  return SHELL_NAVIGATION_SECTIONS.flatMap((section) => section.items).find((item) => item.routeId === routeId)?.path ?? "/research";
}

export function routeIdForWorkspaceView(view: WorkspaceView): ShellRouteId {
  return LEGACY_VIEW_TO_ROUTE[view];
}

export function routeForWorkspaceView(view: WorkspaceView, options: { conversationId?: string | null; currentRouteId?: AppRouteId; family?: "chat" | "research" } = {}): string {
  if (view === "conversation") {
    const family = options.family ?? (options.currentRouteId === "chat" || options.currentRouteId === "chat-conversation" ? "chat" : "research");
    return options.conversationId ? `/${family}/${encodeURIComponent(options.conversationId)}` : `/${family}?mode=conversation`;
  }
  if (view === "architecture") return "/settings?panel=architecture";
  return routePath(routeIdForWorkspaceView(view));
}

export function translateLegacyLocation(pathname: string, search: string, hash: string): string | null {
  if (pathname !== "/" && pathname !== "") return null;
  const query = new URLSearchParams(search);
  const legacyView = query.get("view");
  if (legacyView !== null && !isWorkspaceView(legacyView)) return null;
  const parsedView: WorkspaceView = legacyView === null ? "overview" : legacyView as WorkspaceView;
  const evidence = parseEvidenceDeepLink(hash);
  query.delete("view");

  let path = routePath(routeIdForWorkspaceView(parsedView));
  if (parsedView === "conversation" || evidence) {
    const conversationId = query.get("conversationId") ?? evidence?.conversationId ?? null;
    path = routeForWorkspaceView("conversation", { conversationId });
    if (!conversationId && !query.has("mode")) query.set("mode", "conversation");
  }
  if (parsedView === "architecture" && !query.has("panel")) query.set("panel", "architecture");
  const pathParts = path.split("?");
  if (!query.toString() && pathParts[1]) return `${path}${hash}`;
  return `${pathParts[0]}${query.toString() ? `?${query}` : ""}${hash}`;
}

export function primaryRouteId(route: ResolvedAppRoute): ShellRouteId | null {
  const mapping: Partial<Record<AppRouteId, ShellRouteId>> = {
    chat: "chat", "chat-conversation": "chat", research: "research", "research-conversation": "research",
    documents: "documents", "document-detail": "documents", search: "search", collections: "collections",
    "collection-detail": "collections", retrieval: "retrieval", models: "models", pipeline: "pipeline",
    "pipeline-run": "pipeline", reranker: "reranker", evaluation: "evaluation", "evaluation-run": "evaluation",
    analytics: "analytics", datasets: "datasets", settings: "settings", logs: "logs",
  };
  return mapping[route.id] ?? (route.id === "legacy-root" && route.isKnown ? routeIdForWorkspaceView(route.workspaceView) : null);
}
