import type { StageEvent, StageEventStatus } from "../types";

const STAGE_STATUSES: ReadonlySet<StageEventStatus> = new Set([
  "pending",
  "running",
  "success",
  "failed",
  "skipped",
  "cancelled",
]);

export function isStageEvent(value: unknown): value is StageEvent {
  if (!value || typeof value !== "object") return false;
  const event = value as Partial<StageEvent>;
  return (
    event.version === 1 &&
    typeof event.request_id === "string" &&
    event.request_id.length > 0 &&
    Number.isInteger(event.sequence) &&
    event.sequence > 0 &&
    typeof event.stage_id === "string" &&
    event.stage_id.length > 0 &&
    typeof event.status === "string" &&
    STAGE_STATUSES.has(event.status as StageEventStatus)
  );
}
export function appendStageEvent(current: StageEvent[], candidate: unknown): StageEvent[] {
  if (!isStageEvent(candidate)) return current;
  if (current.some((event) => event.request_id === candidate.request_id && event.sequence === candidate.sequence)) {
    return current;
  }
  return [...current, candidate].sort((left, right) => left.sequence - right.sequence).slice(-100);
}
