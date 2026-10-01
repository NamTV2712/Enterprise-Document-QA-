import { FileText, HelpCircle, Link2, MessageSquare, StickyNote } from "lucide-react";

import type { CollectionItemKind } from "../../types";
import { collectionItemKindLabel } from "../../lib/collectionModel";

interface CollectionTypeBadgeProps {
  kind: CollectionItemKind | string;
  vi: boolean;
  /** The reference reserves the coloured badge for fetched documents. */
  tone?: "document" | "neutral";
}

const ICONS: Record<string, typeof FileText> = {
  document: FileText,
  evidence: Link2,
  answer: MessageSquare,
  note: StickyNote,
};

/** One member's declared kind, shown as a badge: the type comes from DATA-003. */
export function CollectionTypeBadge({ kind, vi, tone = "neutral" }: CollectionTypeBadgeProps) {
  const Icon = ICONS[kind] ?? HelpCircle;
  return (
    <span className={`collection-kind-badge collection-kind-badge--${tone}`} data-kind={kind}>
      <Icon className="collection-kind-badge__icon" aria-hidden="true" />
      <span className="collection-kind-badge__label">{collectionItemKindLabel(kind, vi)}</span>
    </span>
  );
}
