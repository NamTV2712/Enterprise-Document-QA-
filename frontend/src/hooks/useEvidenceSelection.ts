import { useEffect, useState } from "react";
import { EvidenceSelection } from "../types";

export type EvidenceInspectorSelection = EvidenceSelection;

/** Keeps source inspection local to the active conversation. */
export function useEvidenceSelection(activeConversationId: string) {
  const [selection, setSelection] = useState<EvidenceInspectorSelection | null>(null);

  useEffect(() => {
    setSelection(null);
  }, [activeConversationId]);

  return [selection, setSelection] as const;
}
