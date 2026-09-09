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
  return STAGE_LABELS[stageId]?.[locale] ?? stageId.replace(/_/g, " ");
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
  const elapsed = trace?.elapsed_ms;
  return (
    <details className="group rounded-lg border border-[var(--border-subtle)] surface-muted text-xs" open={isStreaming}>
      <summary className="flex min-h-10 cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 font-semibold text-[var(--text-muted)] [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2"><Timer className="h-3.5 w-3.5" />{title}</span>
        {typeof elapsed === "number" && <span>{(elapsed / 1000).toFixed(2)}s</span>}
      </summary>
      <div className="ui-expand-enter border-t border-[var(--border-subtle)] px-3 py-2" role="status" aria-live="polite" aria-label={title}>
        {currentStages.length > 0 ? (
          <ul className="space-y-1 text-[var(--text-muted)]">
            {currentStages.map((stage) => {
              const measuredElapsed = stage.status === "running" && isStreaming && stage.elapsed_ms == null
                ? Math.max(0, now - (runningSince.current.get(stage.stage_id) ?? now))
                : stage.elapsed_ms;
              const counter = stage.counters?.source_count ?? stage.counters?.candidate_count ?? stage.counters?.subquery_count;
              return (
                <li key={`${stage.stage_id}-${stage.request_id}`} className="flex items-center justify-between gap-3 py-1">
                  <span className="flex min-w-0 items-center gap-2">
                    <StatusIcon status={stage.status} />
                    <span className="truncate">
                      {stageLabel(stage.stage_id, locale)}
                      {stage.status !== "success" ? ` · ${statusLabel(stage.status, locale)}` : ""}
                    </span>
                    {typeof counter === "number" && <span className="rounded bg-[var(--surface)] px-1.5 py-0.5 font-mono text-[10px]">{counter}</span>}
                  </span>
                  {typeof measuredElapsed === "number" && <span className="shrink-0 font-mono tabular-nums">{measuredElapsed.toFixed(0)} ms</span>}
                </li>
              );
            })}
          </ul>
        ) : trace ? (
          <ul className="space-y-1 text-[var(--text-muted)]">
            {trace.stages.map((stage) => (
              <li key={`${stage.name}-${stage.status}`} className="flex items-center justify-between gap-3 py-1">
                <span className="flex min-w-0 items-center gap-2"><StatusIcon status={stage.status} /><span>{stage.name.replace(/_/g, " ")}{stage.status !== "completed" ? ` · ${statusLabel(stage.status, locale)}` : ""}</span></span>
                <span className="shrink-0 font-mono tabular-nums">{stage.elapsed_ms.toFixed(0)} ms</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </details>
  );
}
