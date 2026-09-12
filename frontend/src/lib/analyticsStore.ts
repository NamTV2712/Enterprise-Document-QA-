export type AnalyticsEventKind =
  | "query_started"
  | "query_completed"
  | "query_error"
  | "feedback"
  | "retrieval_inspect"
  | "evaluation_opened";

export interface AnalyticsEvent {
  id: string;
  kind: AnalyticsEventKind;
  at: number;
  language?: "en" | "vi";
  ticker?: string | null;
  durationMs?: number;
  status?: string;
  view?: string;
}

const STORAGE_KEY = "sec_qa_local_analytics_v1";
const MAX_EVENTS = 1000;

function safeRead(): AnalyticsEvent[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((event): event is AnalyticsEvent =>
      Boolean(
        event &&
          typeof event === "object" &&
          typeof event.id === "string" &&
          typeof event.kind === "string" &&
          typeof event.at === "number",
      ),
    );
  } catch {
    return [];
  }
}

function safeWrite(events: AnalyticsEvent[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events.slice(-MAX_EVENTS)));
  } catch {
    // Analytics must never make the research flow fail when storage is full.
  }
}

export function recordAnalyticsEvent(
  event: Omit<AnalyticsEvent, "id" | "at"> & { at?: number },
): void {
  const events = safeRead();
  safeWrite([
    ...events,
    {
      ...event,
      id: `analytics-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      at: event.at ?? Date.now(),
    },
  ]);
}

export function readAnalyticsEvents(): AnalyticsEvent[] {
  return safeRead().sort((a, b) => b.at - a.at);
}

export function clearAnalytics(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing else to do; the panel will show the next readable snapshot.
  }
}

export function exportAnalytics(events: AnalyticsEvent[] = readAnalyticsEvents()): string {
  return JSON.stringify(
    {
      schema_version: 1,
      exported_at: new Date().toISOString(),
      note: "Local activity only; no question, answer, source text, session ID, or secret is stored.",
      events: events.map(({ id, ...event }) => event),
    },
    null,
    2,
  );
}
