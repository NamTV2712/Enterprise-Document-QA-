import { useEffect, useMemo, useRef, useState } from "react";
import { Check, CircleSlash2, Clock3, Loader2, OctagonAlert, Timer, XCircle } from "lucide-react";
import type { ExecutionTrace, StageEvent } from "../types";
import { useLocale } from "../lib/i18n";

interface PipelineExecutionProps {
  events?: StageEvent[];
  trace?: ExecutionTrace;
  isStreaming?: boolean;
}

const STAGE_LABELS: Record<string, { en: string; vi: string }> = {
  query_preparation: { en: "Query preparation", vi: "Chuẩn bị câu hỏi" },
  embedding: { en: "Embedding", vi: "Embedding" },
  cache_lookup: { en: "Cache lookup", vi: "Kiểm tra cache" },
  retrieval: { en: "Retrieval", vi: "Truy hồi" },
  generation: { en: "Generation", vi: "Sinh câu trả lời" },
  cache_replay: { en: "Cache replay", vi: "Phát lại từ cache" },
  decomposition: { en: "Query decomposition", vi: "Tách câu hỏi" },
  subquery_retrieval: { en: "Sub-query retrieval", vi: "Truy hồi câu hỏi con" },
};

function stageLabel(stageId: string, locale: "en" | "vi"): string {
  const knownLabel = STAGE_LABELS[stageId]?.[locale];
  if (knownLabel) return knownLabel;
  const rawLabel = stageId.replace(/_/g, " ");
  return locale === "vi" ? `Bước chưa xác định · ${rawLabel}` : `Unknown stage · ${rawLabel}`;
}

function statusLabel(status: string, locale: "en" | "vi"): string {
  const labels: Record<string, { en: string; vi: string }> = {
    pending: { en: "pending", vi: "đang chờ" },
    running: { en: "running", vi: "đang chạy" },
    success: { en: "complete", vi: "hoàn tất" },
    completed: { en: "complete", vi: "hoàn tất" },
    failed: { en: "failed", vi: "lỗi" },
    skipped: { en: "skipped", vi: "bỏ qua" },
    cancelled: { en: "cancelled", vi: "đã huỷ" },
    miss: { en: "miss", vi: "miss" },
    hit: { en: "hit", vi: "hit" },
  };
  return labels[status]?.[locale] ?? status;
}

function StatusIcon({ status }: { status: string }) {
  if (status === "running") return <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--accent-text)]" aria-hidden="true" />;
  if (status === "success" || status === "completed" || status === "hit") return <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />;
  if (status === "failed") return <OctagonAlert className="h-3.5 w-3.5 text-rose-600 dark:text-rose-300" aria-hidden="true" />;
  if (status === "cancelled") return <XCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-300" aria-hidden="true" />;
  if (status === "skipped") return <CircleSlash2 className="h-3.5 w-3.5 text-[var(--text-subtle)]" aria-hidden="true" />;
  return <Clock3 className="h-3.5 w-3.5 text-[var(--text-subtle)]" aria-hidden="true" />;
}

const COUNTER_LABELS: Record<string, { en: string; vi: string }> = {
  candidate_count: { en: "candidates", vi: "ứng viên" },
  source_count: { en: "sources", vi: "nguồn" },
  subquery_count: { en: "sub-queries", vi: "câu hỏi con" },
  token_count: { en: "tokens", vi: "token" },
};

function counterEntries(stage: StageEvent, locale: "en" | "vi"): Array<{ key: string; label: string; value: number }> {
  return Object.entries(stage.counters ?? {})
    .filter((entry): entry is [string, number] => typeof entry[1] === "number" && Number.isFinite(entry[1]))
    .map(([key, value]) => ({
      key,
      value,
      label: COUNTER_LABELS[key]?.[locale] ?? key.replace(/_/g, " "),
    }));
}

function stageDepth(stage: StageEvent, stages: StageEvent[]): number {
  if (!stage.parent_stage_id) return 0;
  const byIdentity = new Map<string, StageEvent>(
    stages.map((candidate) => [`${candidate.request_id}:${candidate.stage_id}`, candidate] as const),
  );
  const seen = new Set<string>();
  let parentId: string | null | undefined = stage.parent_stage_id;
  let depth = 0;
  while (parentId) {
    const identity = `${stage.request_id}:${parentId}`;
    if (seen.has(identity)) break;
    seen.add(identity);
    const parent = byIdentity.get(identity);
    if (!parent) break;
    depth += 1;
    parentId = parent.parent_stage_id;
  }
  return Math.min(depth, 3);
}

export function PipelineExecution({ events = [], trace, isStreaming = false }: PipelineExecutionProps) {
  const { locale } = useLocale();
  const [now, setNow] = useState(() => Date.now());
  const runningSince = useRef(new Map<string, number>());
  const orderedEvents = useMemo(() => [...events].sort((left, right) => left.sequence - right.sequence), [events]);
  const currentStages = useMemo(() => {
    const latest = new Map<string, StageEvent>();
    for (const event of orderedEvents) latest.set(event.stage_id, event);
    return [...latest.values()];
  }, [orderedEvents]);
  const hasRunningStage = currentStages.some((stage) => stage.status === "running");
  const stageAnnouncement = useMemo(
    () => currentStages
      .map((stage) => `${stageLabel(stage.stage_id, locale)} · ${statusLabel(stage.status, locale)}`)
      .join(". "),
    [currentStages, locale],
  );

  useEffect(() => {
    const activeIds = new Set(currentStages.filter((stage) => stage.status === "running").map((stage) => stage.stage_id));
    for (const stageId of activeIds) {
      if (!runningSince.current.has(stageId)) runningSince.current.set(stageId, Date.now());
    }
    for (const stageId of runningSince.current.keys()) {
      if (!activeIds.has(stageId)) runningSince.current.delete(stageId);
    }
  }, [currentStages]);

  useEffect(() => {
    if (!isStreaming || !hasRunningStage) return;
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [hasRunningStage, isStreaming]);

  if (currentStages.length === 0 && !trace) return null;

  const title = locale === "vi" ? "Các bước thực thi" : "Execution stages";
  const workflowTitle = locale === "vi" ? "Cách câu trả lời được xây dựng" : "How this answer was built";
  const elapsed = trace?.elapsed_ms;
  const serverDurationLabel = locale === "vi" ? "Thời lượng server" : "Server duration";
  const localElapsedLabel = locale === "vi" ? "Đã trôi qua trong giao diện" : "Elapsed in this view";
  const serverElapsedLabel = locale === "vi" ? "Server" : "Server";
  return (
    <details className="group rounded-lg border border-[var(--border-subtle)] surface-muted text-xs" open={isStreaming}>
      <summary className="flex min-h-10 cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 font-semibold text-[var(--text-muted)] [&::-webkit-details-marker]:hidden">
        <span className="flex min-w-0 items-center gap-2"><Timer className="h-3.5 w-3.5 shrink-0" /><span className="truncate">{workflowTitle}</span><span aria-hidden="true" className="font-normal text-[var(--text-subtle)]">·</span><span className="font-normal text-[var(--text-subtle)]">{title}</span></span>
        {typeof elapsed === "number" && <span>{serverDurationLabel} · {(elapsed / 1000).toFixed(2)}s</span>}
      </summary>
      <div className="ui-expand-enter border-t border-[var(--border-subtle)] px-3 py-2">
        <p className="mb-2 text-[11px] leading-relaxed text-[var(--text-subtle)]">
          {locale === "vi" ? "Chỉ các bước và thời lượng do pipeline báo cáo mới được hiển thị." : "Only stages and durations reported by the pipeline are shown."}
        </p>
        <div role="status" aria-live="polite" aria-atomic="true" aria-label={title} className="sr-only">
          {stageAnnouncement}
        </div>
        <div data-testid="execution-stage-list" aria-label={title}>
          {currentStages.length > 0 ? (
            <ul className="space-y-1 text-[var(--text-muted)]">
              {currentStages.map((stage) => {
                const isLocalElapsed = stage.status === "running" && isStreaming && stage.elapsed_ms == null;
                const measuredElapsed = isLocalElapsed
                  ? Math.max(0, now - (runningSince.current.get(stage.stage_id) ?? now))
                  : stage.elapsed_ms;
                const depth = stageDepth(stage, currentStages);
                return (
                  <li
                    key={`${stage.stage_id}-${stage.request_id}`}
                    className="flex items-center justify-between gap-3 py-1"
                    data-stage-id={stage.stage_id}
                    data-stage-depth={depth}
                    style={depth > 0 ? { paddingLeft: `${depth * 16}px` } : undefined}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <StatusIcon status={stage.status} />
                      <span className="truncate">
                        {stageLabel(stage.stage_id, locale)}
                        {stage.status !== "success" ? ` · ${statusLabel(stage.status, locale)}` : ""}
                      </span>
                      <span className="flex shrink-0 flex-wrap gap-1">
                        {counterEntries(stage, locale).map((counter) => (
                          <span key={counter.key} className="rounded bg-[var(--surface)] px-1.5 py-0.5 font-mono text-[10px]">
                            {counter.value} {counter.label}
                          </span>
                        ))}
                      </span>
                    </span>
                    {typeof measuredElapsed === "number" && (
                      <span className="shrink-0 font-mono tabular-nums" aria-label={`${isLocalElapsed ? localElapsedLabel : serverElapsedLabel}: ${measuredElapsed.toFixed(0)} ms`}>
                        {isLocalElapsed ? localElapsedLabel : serverElapsedLabel} · {measuredElapsed.toFixed(0)} ms
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
        {currentStages.length === 0 && trace ? (
          <ul className="space-y-1 text-[var(--text-muted)]">
            {trace.stages.map((stage) => (
              <li key={`${stage.name}-${stage.status}`} className="flex items-center justify-between gap-3 py-1">
                <span className="flex min-w-0 items-center gap-2"><StatusIcon status={stage.status} /><span>{stageLabel(stage.name, locale)}{stage.status !== "completed" ? ` · ${statusLabel(stage.status, locale)}` : ""}</span></span>
                <span className="shrink-0 font-mono tabular-nums">{serverElapsedLabel} · {stage.elapsed_ms.toFixed(0)} ms</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </details>
  );
}
