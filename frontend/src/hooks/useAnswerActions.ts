import { useCallback, useRef, useState } from "react";
import type {
  AnswerActionKind,
  AnswerActionState,
  AnswerActionStatus,
  AnswerTarget,
  MessageFeedback,
  SaveAnswerVersionStatus,
} from "../types";
import type { ConversationWriteResult } from "../lib/conversationStore";
import type { SaveAnswerVersionResult } from "./useConversationLibrary";

export interface UseAnswerActionsOptions {
  activeConversationId: string;
  toggleBookmark: (messageId: string) => Promise<ConversationWriteResult>;
  saveNote: (messageId: string, note: string) => Promise<ConversationWriteResult>;
  saveFeedback: (messageId: string, feedback: MessageFeedback | undefined) => Promise<ConversationWriteResult>;
  saveVersion: (target: AnswerTarget) => Promise<SaveAnswerVersionResult>;
}

export interface AnswerActionsController {
  states: Record<string, AnswerActionState>;
  getState: (kind: AnswerActionKind, target: AnswerTarget) => AnswerActionState;
  bookmark: (target: AnswerTarget) => Promise<AnswerActionState>;
  note: (target: AnswerTarget, note: string) => Promise<AnswerActionState>;
  feedback: (target: AnswerTarget, feedback: MessageFeedback | undefined) => Promise<AnswerActionState>;
  saveVersion: (target: AnswerTarget) => Promise<AnswerActionState>;
}

const EMPTY_STATUS: AnswerActionStatus = "idle";

function keyFor(kind: AnswerActionKind, target: AnswerTarget): string {
  return `${target.conversationId}:${target.messageId}:${target.variantId ?? "original"}:${kind}`;
}

function emptyState(kind: AnswerActionKind, target: AnswerTarget): AnswerActionState {
  return { kind, target, status: EMPTY_STATUS, warning: null, updatedAt: 0 };
}

function writeStatus(result: ConversationWriteResult): AnswerActionStatus {
  if (result.status === "persisted") return "persisted";
  if (result.status === "volatile") return "volatile";
  return "retryable";
}

function versionStatus(result: SaveAnswerVersionResult): AnswerActionStatus {
  if (result.status === "saved" || result.status === "persisted") return "persisted";
  if (result.status === "already_saved" || result.status === "already_exists") return "already_exists";
  if (result.status === "volatile") return "volatile";
  if (result.status === "cancelled") return "cancelled";
  return "retryable";
}

/**
 * Owns answer-local action state. Each async operation is keyed to the exact
 * conversation/message/version target, so a late result cannot repaint a
 * different answer after navigation or variant selection.
 */
export function useAnswerActions(options: UseAnswerActionsOptions): AnswerActionsController {
  const [states, setStates] = useState<Record<string, AnswerActionState>>({});
  const attemptsRef = useRef(new Map<string, number>());

  const getState = useCallback((kind: AnswerActionKind, target: AnswerTarget) => {
    const key = keyFor(kind, target);
    return states[key] ?? emptyState(kind, target);
  }, [states]);

  const run = useCallback(async <T,>(
    kind: AnswerActionKind,
    target: AnswerTarget,
    operation: () => Promise<T>,
    getResult: (result: T) => { status: AnswerActionStatus; warning: string | null },
  ): Promise<AnswerActionState> => {
    const key = keyFor(kind, target);
    if (target.conversationId !== options.activeConversationId) {
      const cancelled: AnswerActionState = { kind, target, status: "cancelled", warning: "The answer context is no longer active.", updatedAt: Date.now() };
      setStates((previous) => ({ ...previous, [key]: cancelled }));
      return cancelled;
    }
    const attempt = (attemptsRef.current.get(key) ?? 0) + 1;
    attemptsRef.current.set(key, attempt);
    const pending: AnswerActionState = { kind, target, status: "pending", warning: null, updatedAt: Date.now() };
    setStates((previous) => ({ ...previous, [key]: pending }));
    try {
      const result = await operation();
      // Keep the state target-local. Even if the user navigated away, this
      // write cannot be rendered for the newly active answer.
      if (attemptsRef.current.get(key) !== attempt) return pending;
      const mapped = getResult(result);
      const next: AnswerActionState = { kind, target, ...mapped, updatedAt: Date.now() };
      setStates((previous) => ({ ...previous, [key]: next }));
      return next;
    } catch (error) {
      if (attemptsRef.current.get(key) !== attempt) return pending;
      const next: AnswerActionState = {
        kind,
        target,
        status: "retryable",
        warning: error instanceof Error ? error.message : "The local action could not be completed.",
        updatedAt: Date.now(),
      };
      setStates((previous) => ({ ...previous, [key]: next }));
      return next;
    }
  }, [options.activeConversationId]);

  const bookmark = useCallback((target: AnswerTarget) => run(
    "bookmark",
    target,
    () => options.toggleBookmark(target.messageId),
    (result) => ({ status: writeStatus(result), warning: result.warning }),
  ), [options, run]);

  const note = useCallback((target: AnswerTarget, noteText: string) => run(
    "note",
    target,
    () => options.saveNote(target.messageId, noteText),
    (result) => ({ status: writeStatus(result), warning: result.warning }),
  ), [options, run]);

  const feedback = useCallback((target: AnswerTarget, value: MessageFeedback | undefined) => run(
    "feedback",
    target,
    () => options.saveFeedback(target.messageId, value),
    (result) => ({ status: writeStatus(result), warning: result.warning }),
  ), [options, run]);

  const saveVersion = useCallback((target: AnswerTarget) => run(
    "save_version",
    target,
    () => options.saveVersion(target),
    (result) => ({ status: versionStatus(result), warning: result.warning }),
  ), [options, run]);

  return { states, getState, bookmark, note, feedback, saveVersion };
}

/** Map the shared state to the legacy save-version prop while consumers migrate. */
export function toLegacySaveStatus(status: AnswerActionStatus): SaveAnswerVersionStatus {
  if (status === "pending") return "saving";
  if (status === "persisted") return "saved";
  if (status === "already_exists") return "already_saved";
  return status;
}
