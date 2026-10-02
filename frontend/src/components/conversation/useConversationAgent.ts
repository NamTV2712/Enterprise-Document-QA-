import { useCallback, useEffect, useRef, useState } from "react";
import type { ConversationLibraryController } from "../../hooks/useConversationLibrary";
import { useAgentWorkspace } from "../agent/useAgentWorkspace";

export function useConversationAgent(library: ConversationLibraryController, locale: "en" | "vi") {
  const model = useAgentWorkspace(null, { loadList: false });
  const [mode, setModeState] = useState<"quick" | "deep">("quick");
  const [permission, setPermission] = useState<{ conversationId: string; generation: number } | null>(null);
  const [linkError, setLinkError] = useState(false);
  const lock = useRef(false);
  const sessionGeneration = useRef(model.session.generation);
  sessionGeneration.current = model.session.generation;
  useEffect(() => { setModeState("quick"); setPermission(null); setLinkError(false); }, [library.activeConversationId]);
  const setMode = useCallback((next: "quick" | "deep") => { setPermission(null); setLinkError(false); setModeState(next); }, []);
  const consent = mode === "deep" && permission?.conversationId === library.activeConversationId
    && permission.generation === model.session.generation;
  const setConsent = (allowed: boolean) => setPermission(allowed
    ? { conversationId: library.activeConversationId, generation: model.session.generation } : null);
  const readOnly = library.isLegacyExample || !!library.activeRecord?.deletionPending || !library.writerStatus.owned;
  const canSend = model.session.status === "connected" && model.session.canExecute && !readOnly
    && (!model.session.decisionProviderAvailable || consent);
  const send = async (text: string): Promise<boolean> => {
    const goal = text.trim();
    if (mode !== "deep" || lock.current || !canSend || !library.isLibraryReady || goal.length < 5 || goal.length > 500) return false;
    const identity = library.beginSend(goal);
    if (!identity) return false;
    lock.current = true;
    setLinkError(false);
    const generation = model.session.generation;
    try {
      if (!await library.prepareAgentSend(identity) || sessionGeneration.current !== generation) return false;
      let linked = false;
      const created = await model.create({ goal, locale,
        ...(model.session.decisionProviderAvailable && consent ? { allow_decision_provider_execution: true } : {}),
      }, async (reference) => { await library.linkAgentRun(identity, goal, reference); linked = true; });
      return !!created && linked && library.isIdentityActive(identity);
    } catch { setLinkError(true); return false; }
    finally { lock.current = false; setPermission(null); library.finishSend(identity); }
  };
  return { mode, setMode, consent, setConsent, model, readOnly, canSend, send, linkError };
}
