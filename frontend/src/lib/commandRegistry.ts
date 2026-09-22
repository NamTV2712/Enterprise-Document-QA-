import type { MessageKey } from "./i18n";
import { SHELL_NAVIGATION_SECTIONS, type ShellRouteId } from "../app/routes";
import type { SemanticIconKey } from "./semanticIcons";

export type CommandIcon = SemanticIconKey;

export interface CommandDefinition {
  id: string;
  kind: "navigation" | "utility";
  labelKey: MessageKey;
  descriptionKey?: MessageKey;
  accentFamily?: "research" | "documents" | "retrieval" | "evidence" | "evaluation" | "analytics" | "system";
  icon: CommandIcon;
  routeId?: ShellRouteId;
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
 * real shell route registry.
 */
const NAVIGATION_COMMANDS: readonly CommandDefinition[] = SHELL_NAVIGATION_SECTIONS.flatMap((section) =>
  section.items.map((item) => ({
    id: `navigate-${item.routeId}`,
    kind: "navigation" as const,
    labelKey: item.labelKey,
    descriptionKey: item.descriptionKey,
    accentFamily: item.accentFamily,
    icon: item.icon,
    routeId: item.routeId,
    action: "navigate" as const,
  })),
);

export const COMMAND_REGISTRY: readonly CommandDefinition[] = [
  ...NAVIGATION_COMMANDS,
  { id: "new-conversation", kind: "utility", labelKey: "nav.newConversation", descriptionKey: "nav.newConversationDescription", icon: "newConversation", action: "new-conversation", keywords: ["reset", "clear"] },
  { id: "open-help", kind: "utility", labelKey: "nav.help", icon: "help", action: "help", keywords: ["guide", "instructions"] },
];
