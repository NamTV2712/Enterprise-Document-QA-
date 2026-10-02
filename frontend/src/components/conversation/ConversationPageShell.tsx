import { memo, type ReactNode, type RefObject } from "react";

import { ConversationPageHeader } from "./ConversationPageHeader";
import { FollowUpTiles } from "./FollowUpTiles";
import { ResearchInsightsRow } from "./ResearchInsightsRow";
import type { RelatedResearchSuggestion } from "../../lib/relatedResearch";
import type { ConversationMode, Message } from "../../types";

interface ConversationPageShellProps {
  mode: ConversationMode;
  /** Latest completed assistant answer backing the research insight tiles. */
  insightMessage: Message | null;
  followUps: RelatedResearchSuggestion[];
  onNewConversation: () => void;
  onOpenHistory: () => void;
  onSelectFollowUp: (question: string, scope: { ticker: string | null; section: string | null }) => void;
  /** Scroll container owned here so App keeps its scroll/focus behavior. */
  scrollContainerRef: RefObject<HTMLDivElement | null>;
  messagesEndRef: RefObject<HTMLDivElement | null>;
  canShowFollowUps: boolean;
  scrollButton?: ReactNode;
  composer: ReactNode;
  children: ReactNode;
}

/**
 * Conversation page composition. It owns presentation and scroll structure
 * only: the answer thread, request lifecycle, evidence identity, and composer
 * state stay with the existing App/hook owners passed in as children and slots.
 */
export const ConversationPageShell = memo(function ConversationPageShell({
  mode,
  insightMessage,
  followUps,
  onNewConversation,
  onOpenHistory,
  onSelectFollowUp,
  scrollContainerRef,
  messagesEndRef,
  canShowFollowUps,
  scrollButton,
  composer,
  children,
}: ConversationPageShellProps) {
  return (
    <div className="conversation-primary-shell flex flex-col h-full overflow-hidden">
      <ConversationPageHeader
        mode={mode}
        onNewConversation={onNewConversation}
        onOpenHistory={onOpenHistory}
      />
      <div ref={scrollContainerRef} className="conversation-message-scroll flex-1 overflow-y-auto">
        <div className="flex flex-col w-full min-h-full py-4 md:py-5 pb-6 relative">
          {children}
          <div ref={messagesEndRef} />
          {insightMessage && mode === "research" && (
            <div className="mx-auto w-full max-w-4xl px-3 md:px-4 pb-3">
              <ResearchInsightsRow message={insightMessage} />
            </div>
          )}
          {canShowFollowUps && (
            <FollowUpTiles mode={mode} suggestions={followUps} onSelect={onSelectFollowUp} />
          )}
          {scrollButton}
        </div>
      </div>
      {composer}
    </div>
  );
});
