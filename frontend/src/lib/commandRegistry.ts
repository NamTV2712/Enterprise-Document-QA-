import type { MessageKey } from "./i18n";
import { WORKSPACE_NAV_SECTIONS, type WorkspaceIcon, type WorkspaceView } from "./workspace";

export type CommandIcon = WorkspaceIcon | "help";

export interface CommandDefinition {
  id: string;
  kind: "navigation" | "utility";
  labelKey: MessageKey;
  icon: CommandIcon;
  view?: WorkspaceView;
  action: "navigate" | "help" | "new-conversation";
  keywords?: readonly string[];
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
    icon: item.icon,
    view: item.view,
    action: "navigate" as const,
    keywords: item.keywords,
  })),
);

export const COMMAND_REGISTRY: readonly CommandDefinition[] = [
  ...NAVIGATION_COMMANDS,
  { id: "new-conversation", kind: "utility", labelKey: "nav.newConversation", icon: "sparkles", action: "new-conversation", keywords: ["reset", "clear"] },
  { id: "open-help", kind: "utility", labelKey: "nav.help", icon: "help", action: "help", keywords: ["guide", "instructions"] },
];
