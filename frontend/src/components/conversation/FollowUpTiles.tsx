import { memo } from "react";
import { ArrowUpRight, FlaskConical, Sparkles } from "lucide-react";

import { useLocale, type Locale } from "../../lib/i18n";
import type { RelatedResearchSuggestion } from "../../lib/relatedResearch";
import type { ConversationMode } from "../../types";

interface FollowUpTilesProps {
  mode: ConversationMode;
  suggestions: RelatedResearchSuggestion[];
  onSelect: (question: string, scope: { ticker: string | null; section: string | null }) => void;
}

/**
 * Research presents follow-ups as reference-style tiles; chat keeps the
 * compact chip strip. Both fill the existing composer path — selecting a
 * follow-up never submits by itself.
 */
export const FollowUpTiles = memo(function FollowUpTiles({
  mode,
  suggestions,
  onSelect,
}: FollowUpTilesProps) {
  const { t, locale } = useLocale();
  if (suggestions.length === 0) return null;

  if (mode === "chat") {
    return (
      <div className="followup-strip px-4 pt-2" aria-label={t("conversation.followUps")}>
        <span className="followup-strip__label">
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          {t("conversation.followUps")}
        </span>
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.id}
            type="button"
            className="followup-chip"
            onClick={() => onSelect(suggestion.question[locale as Locale], suggestion.scope)}
          >
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{suggestion.label[locale as Locale]}</span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <section className="conversation-followups" aria-label={t("conversation.followUps")} data-testid="conversation-followups">
      <span className="conversation-followups__label">
        <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
        {t("conversation.followUps")}
      </span>
      <div className="conversation-followups__grid">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.id}
            type="button"
            className="conversation-followup-tile"
            onClick={() => onSelect(suggestion.question[locale as Locale], suggestion.scope)}
          >
            <span className="conversation-followup-tile__text">{suggestion.label[locale as Locale]}</span>
            <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
  );
});
