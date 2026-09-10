import type { MessageKey } from "./i18n";
import { WORKSPACE_NAV_SECTIONS, type WorkspaceView } from "./workspace";
import type { SemanticIconKey } from "./semanticIcons";

export type CommandIcon = SemanticIconKey;

export interface CommandDefinition {
  id: string;
  kind: "navigation" | "utility";
  labelKey: MessageKey;
  descriptionKey?: MessageKey;
  accentFamily?: "research" | "documents" | "retrieval" | "evidence" | "evaluation" | "analytics" | "system";
  icon: CommandIcon;
  view?: WorkspaceView;
  action: "navigate" | "help" | "new-conversation";
  keywords?: readonly string[];
}

/** Runtime-bound commands are metadata-compatible with the registry but own
 * their callback in the feature owner. The palette never implements effects.
 */
export interface ContextualCommandDefinition {
  id: string;
  labelKey: MessageKey;
  descriptionKey?: MessageKey;
  accentFamily?: CommandDefinition["accentFamily"];
  icon: CommandIcon;
  run: () => void;
}

/**
 * Palette commands are data so filtering and keyboard execution cannot drift
 * from the visible command rows. Product destinations stay limited to the
 * real WorkspaceView union.
 */
const NAVIGATION_COMMANDS: readonly CommandDefinition[] = WORKSPACE_NAV_SECTIONS.flatMap((section) =>
  section.items.map((item) => ({
    id: `navigate-${item.view}`,
    kind: "navigation" as const,
    labelKey: item.labelKey,
    descriptionKey: item.descriptionKey,
    accentFamily: item.accentFamily,
    icon: item.icon,
    view: item.view,
    action: "navigate" as const,
    keywords: item.keywords,
  })),
);

export const COMMAND_REGISTRY: readonly CommandDefinition[] = [
  ...NAVIGATION_COMMANDS,
  { id: "new-conversation", kind: "utility", labelKey: "nav.newConversation", descriptionKey: "nav.newConversationDescription", icon: "newConversation", action: "new-conversation", keywords: ["reset", "clear"] },
  { id: "open-help", kind: "utility", labelKey: "nav.help", icon: "help", action: "help", keywords: ["guide", "instructions"] },
];
