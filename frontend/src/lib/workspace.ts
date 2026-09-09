import type { MessageKey } from "./i18n";

export type WorkspaceView =
  | "overview"
  | "conversation"
  | "search"
  | "documents"
  | "library"
  | "retrieval"
  | "architecture"
  | "evaluation"
  | "analytics"
  | "system";

export type WorkspaceIcon =
  | "analytics"
  | "book"
  | "file"
  | "flask"
  | "network"
  | "search"
  | "settings"
  | "sparkles";

export type WorkspaceSectionId = "workspace" | "retrieval" | "evaluate" | "system";

export interface WorkspaceNavItem {
  view: WorkspaceView;
  labelKey: MessageKey;
  icon: WorkspaceIcon;
  nested?: boolean;
  requiresMessages?: boolean;
  keywords?: readonly string[];
}

export interface WorkspaceNavSection {
  id: WorkspaceSectionId;
  labelKey: MessageKey;
  items: readonly WorkspaceNavItem[];
}

/**
 * The navigation registry is the contract for every real workspace route.
 * Keep legacy view values such as `overview` and `conversation` stable so
 * saved URLs and existing callers continue to work.
 */
export const WORKSPACE_NAV_SECTIONS: readonly WorkspaceNavSection[] = [
  {
    id: "workspace",
    labelKey: "nav.groupWorkspace",
    items: [
      { view: "overview", labelKey: "nav.research", icon: "book", keywords: ["home", "start"] },
      {
        view: "conversation",
        labelKey: "nav.currentConversation",
        icon: "sparkles",
        nested: true,
        requiresMessages: true,
        keywords: ["chat", "question"],
      },
      { view: "documents", labelKey: "nav.documents", icon: "file", keywords: ["filings"] },
      { view: "search", labelKey: "nav.search", icon: "search", keywords: ["find"] },
      { view: "library", labelKey: "nav.library", icon: "book", keywords: ["saved", "history"] },
    ],
  },
  {
    id: "retrieval",
    labelKey: "nav.groupRetrieval",
    items: [
      { view: "retrieval", labelKey: "nav.retrieval", icon: "flask", keywords: ["bm25", "reranking"] },
    ],
  },
  {
    id: "evaluate",
    labelKey: "nav.groupEvaluate",
    items: [
      { view: "evaluation", labelKey: "nav.evaluation", icon: "analytics", keywords: ["eval", "experiments"] },
      { view: "analytics", labelKey: "nav.analytics", icon: "analytics", keywords: ["metrics", "usage"] },
    ],
  },
  {
    id: "system",
    labelKey: "nav.groupSystem",
    items: [
      { view: "architecture", labelKey: "nav.architecture", icon: "network", keywords: ["flow"] },
      { view: "system", labelKey: "nav.system", icon: "settings", keywords: ["status", "health"] },
    ],
  },
] as const;

export const WORKSPACE_VIEWS: WorkspaceView[] = WORKSPACE_NAV_SECTIONS.flatMap((section) =>
  section.items.map((item) => item.view),
);

export function isWorkspaceView(value: string | null): value is WorkspaceView {
  return value !== null && WORKSPACE_VIEWS.includes(value as WorkspaceView);
}
