import type { MessageKey } from "./i18n";
import type { SemanticIconKey } from "./semanticIcons";

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

export type WorkspaceIcon = Extract<SemanticIconKey,
  | "research"
  | "conversation"
  | "documents"
  | "search"
  | "library"
  | "retrieval"
  | "evaluation"
  | "analytics"
  | "architecture"
  | "system">;

export type WorkspaceSectionId = "workspace" | "retrieval" | "evaluate" | "system";

export interface WorkspaceNavItem {
  view: WorkspaceView;
  labelKey: MessageKey;
  descriptionKey: MessageKey;
  icon: WorkspaceIcon;
  accentFamily: "research" | "documents" | "retrieval" | "evaluation" | "analytics" | "system";
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
      { view: "overview", labelKey: "nav.research", descriptionKey: "nav.researchDescription", icon: "research", accentFamily: "research", keywords: ["home", "start"] },
      {
        view: "conversation",
        labelKey: "nav.currentConversation", descriptionKey: "nav.currentConversationDescription",
        icon: "conversation", accentFamily: "research",
        nested: true,
        requiresMessages: true,
        keywords: ["chat", "question"],
      },
      { view: "documents", labelKey: "nav.documents", descriptionKey: "nav.documentsDescription", icon: "documents", accentFamily: "documents", keywords: ["filings"] },
      { view: "search", labelKey: "nav.search", descriptionKey: "nav.searchDescription", icon: "search", accentFamily: "retrieval", keywords: ["find"] },
      { view: "library", labelKey: "nav.library", descriptionKey: "nav.libraryDescription", icon: "library", accentFamily: "documents", keywords: ["saved", "history"] },
    ],
  },
  {
    id: "retrieval",
    labelKey: "nav.groupRetrieval",
    items: [
      { view: "retrieval", labelKey: "nav.retrieval", descriptionKey: "nav.retrievalDescription", icon: "retrieval", accentFamily: "retrieval", keywords: ["bm25", "reranking"] },
    ],
  },
  {
    id: "evaluate",
    labelKey: "nav.groupEvaluate",
    items: [
      { view: "evaluation", labelKey: "nav.evaluation", descriptionKey: "nav.evaluationDescription", icon: "evaluation", accentFamily: "evaluation", keywords: ["eval", "experiments"] },
      { view: "analytics", labelKey: "nav.analytics", descriptionKey: "nav.analyticsDescription", icon: "analytics", accentFamily: "analytics", keywords: ["metrics", "usage"] },
    ],
  },
  {
    id: "system",
    labelKey: "nav.groupSystem",
    items: [
      { view: "architecture", labelKey: "nav.architecture", descriptionKey: "nav.architectureDescription", icon: "architecture", accentFamily: "system", keywords: ["flow"] },
      { view: "system", labelKey: "nav.system", descriptionKey: "nav.systemDescription", icon: "system", accentFamily: "system", keywords: ["status", "health"] },
    ],
  },
] as const;

export const WORKSPACE_VIEWS: WorkspaceView[] = WORKSPACE_NAV_SECTIONS.flatMap((section) =>
  section.items.map((item) => item.view),
);

export function getWorkspaceNavItem(view: WorkspaceView): WorkspaceNavItem {
  const item = WORKSPACE_NAV_SECTIONS
    .flatMap((section) => section.items)
    .find((candidate) => candidate.view === view);
  if (!item) throw new Error(`Unregistered workspace view: ${view}`);
  return item;
}

export function isWorkspaceView(value: string | null): value is WorkspaceView {
  return value !== null && WORKSPACE_VIEWS.includes(value as WorkspaceView);
}
