import { memo } from "react";

import { useLocale } from "../../lib/i18n";
import type { Message } from "../../types";

interface ResearchInsightsRowProps {
  /** The most recent completed assistant message; nothing renders without one. */
  message: Message | null;
}

interface InsightTile {
  id: string;
  value: string;
  label: string;
}

/**
 * Reference-style insight tiles rendered only from values the answer actually
 * carries. Retrieval scores are ranking signals and are labelled as a
 * retrieval score, never as accuracy or confidence. Tiles with no backing data
 * are omitted instead of being filled with a placeholder.
 */
export const ResearchInsightsRow = memo(function ResearchInsightsRow({
  message,
}: ResearchInsightsRowProps) {
  const { t } = useLocale();
  if (!message || message.sender !== "assistant" || message.isStreaming) return null;

  const tiles: InsightTile[] = [];
  const sourcesUsed = message.sources?.length ?? 0;
  if (sourcesUsed > 0) {
    tiles.push({ id: "sources", value: String(sourcesUsed), label: t("conversation.insightSourcesUsed") });
  }
  if (typeof message.numChunks === "number" && message.numChunks > 0) {
    tiles.push({ id: "chunks", value: String(message.numChunks), label: t("conversation.insightTotalChunks") });
  }
  const scores = (message.sources ?? [])
    .map((source) => source.score)
    .filter((score): score is number => typeof score === "number" && Number.isFinite(score));
  if (scores.length > 0) {
    tiles.push({ id: "topScore", value: Math.max(...scores).toFixed(3), label: t("conversation.insightTopScore") });
  }
  if (typeof message.execution?.elapsed_ms === "number" && message.execution.elapsed_ms >= 0) {
    tiles.push({
      id: "responseTime",
      value: `${(message.execution.elapsed_ms / 1000).toFixed(1)}s`,
      label: t("conversation.insightResponseTime"),
    });
  }
  if (tiles.length < 2) return null;

  return (
    <section className="conversation-insights" aria-label={t("conversation.insights")} data-testid="conversation-insights">
      <h3 className="conversation-insights__label">{t("conversation.insights")}</h3>
      <div className="conversation-insights__grid">
        {tiles.map((tile) => (
          <div key={tile.id} className="conversation-insight-tile" data-insight={tile.id}>
            <span className="conversation-insight-tile__value">{tile.value}</span>
            <span className="conversation-insight-tile__label">{tile.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
});
