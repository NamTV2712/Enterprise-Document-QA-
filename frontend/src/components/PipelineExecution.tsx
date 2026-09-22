import { useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  CircleSlash2,
  Clock3,
  Loader2,
  OctagonAlert,
  XCircle,
  Search,
  Layers,
  Database,
  ArrowUpDown,
  Sparkles,
  ArrowRight,
  Timer,
} from "lucide-react";
import type { ExecutionTrace, StageEvent } from "../types";
import { useLocale } from "../lib/i18n";

interface PipelineExecutionProps {
  events?: StageEvent[];
  trace?: ExecutionTrace;
  isStreaming?: boolean;
}

const STAGE_LABELS: Record<string, { en: string; vi: string }> = {
  query_preparation: { en: "Query", vi: "Chuẩn bị câu hỏi" },
  embedding: { en: "Embedding", vi: "Embedding" },
  cache_lookup: { en: "Cache lookup", vi: "Kiểm tra cache" },
  retrieval: { en: "Retrieval", vi: "Truy hồi" },
  reranking: { en: "Reranking", vi: "Xếp hạng lại" },
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
  if (status === "success" || status === "completed" || status === "hit") return <Check className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />;
  if (status === "failed") return <OctagonAlert className="h-3.5 w-3.5 text-rose-400" aria-hidden="true" />;
  if (status === "cancelled") return <XCircle className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />;
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
  const [showDetails, setShowDetails] = useState(false);
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

  const [liveElapsedMs, setLiveElapsedMs] = useState(0);
  const streamStartRef = useRef<number | null>(null);

  useEffect(() => {
    if (isStreaming) {
      if (streamStartRef.current === null) {
        streamStartRef.current = Date.now();
      }
      const interval = window.setInterval(() => {
        if (streamStartRef.current) {
          setLiveElapsedMs(Date.now() - streamStartRef.current);
        }
      }, 50);
      return () => window.clearInterval(interval);
    } else {
      streamStartRef.current = null;
      setLiveElapsedMs(0);
    }
  }, [isStreaming]);

  const totalElapsedSec = useMemo<string | null>(() => {
    if (isStreaming && liveElapsedMs > 0) {
      return (liveElapsedMs / 1000).toFixed(1);
    }
    if (typeof trace?.elapsed_ms === "number") {
      return (trace.elapsed_ms / 1000).toFixed(1);
    }
    const sumMs = currentStages.reduce((acc, s) => acc + (s.elapsed_ms || 0), 0);
    if (sumMs > 0) return (sumMs / 1000).toFixed(1);
    return null;
  }, [isStreaming, liveElapsedMs, trace, currentStages]);

  if (currentStages.length === 0 && !trace && !isStreaming) return null;

  const title = locale === "vi" ? "Các bước thực thi" : "Execution stages";
  const workflowTitle = locale === "vi" ? "Cách câu trả lời được xây dựng" : "How this answer was built";
  const elapsed = trace?.elapsed_ms;
  const serverDurationLabel = locale === "vi" ? "Thời lượng server" : "Server duration";
  const localElapsedLabel = locale === "vi" ? "Đã trôi qua trong giao diện" : "Elapsed in this view";
  const serverElapsedLabel = locale === "vi" ? "Server" : "Server";

  const stageIcons = [Search, Layers, Database, ArrowUpDown, Sparkles] as const;
  const stageColors = [
    "bg-blue-600/25 text-blue-400 border-blue-500/40",
    "bg-teal-500/25 text-teal-400 border-teal-500/40",
    "bg-cyan-500/25 text-cyan-400 border-cyan-500/40",
    "bg-purple-600/25 text-purple-400 border-purple-500/40",
    "bg-emerald-500/25 text-emerald-400 border-emerald-500/40",
  ] as const;
  const unavailableElapsed = locale === "vi" ? "Chưa báo cáo" : "Not reported";
  const pipelineSteps = currentStages.map((stage, index) => {
    const localElapsed = stage.status === "running" && isStreaming
      ? Math.max(0, now - (runningSince.current.get(stage.stage_id) ?? now))
      : null;
    const measuredElapsed = typeof stage.elapsed_ms === "number" ? stage.elapsed_ms : localElapsed;
    return {
      name: stageLabel(stage.stage_id, locale),
      icon: stageIcons[index % stageIcons.length],
      time: typeof measuredElapsed === "number" ? `${(measuredElapsed / 1000).toFixed(1)}s` : unavailableElapsed,
      active: stage.status === "running",
      done: ["success", "completed", "failed", "skipped", "cancelled"].includes(stage.status),
      color: stageColors[index % stageColors.length],
    };
  });

  return (
    <div className="pipeline-execution-container rounded-2xl border border-slate-800/80 bg-slate-900/70 p-3.5 my-3 shadow-sm text-xs select-none">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 font-semibold text-[var(--text-primary)]">
          {isStreaming ? (
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          ) : (
            <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Check className="w-2.5 h-2.5" />
            </div>
          )}
          <span>Pipeline Execution</span>
        </div>
        <div className="flex items-center gap-2 text-slate-400 text-xs">
          <span>{locale === "vi" ? "Tổng thời gian" : "Total time"}: <span className="font-mono text-[var(--text-primary)]">{totalElapsedSec ? `${totalElapsedSec}s` : unavailableElapsed}</span></span>
          <button
            type="button"
            onClick={() => setShowDetails((prev) => !prev)}
            className="text-blue-400 hover:text-blue-300 font-medium transition-colors ml-1"
          >
            {showDetails ? (locale === "vi" ? "Ẩn chi tiết" : "Hide details") : (locale === "vi" ? "Xem chi tiết" : "View details")}
          </button>
        </div>
      </div>

      {/* Horizontal Pipeline Steps */}
      <div className="flex items-center justify-between gap-1 overflow-x-auto py-1">
        {pipelineSteps.length > 0 ? pipelineSteps.map((step, idx) => {
          const StepIcon = step.icon;
          return (
            <div key={step.name} className="flex items-center gap-1.5 flex-1 min-w-[70px]">
              <div className="flex flex-col items-center text-center flex-1">
                <div className={`w-9 h-9 rounded-full border flex items-center justify-center mb-1.5 shadow-sm transition-all ${
                  step.active ? "ring-2 ring-blue-400 animate-pulse " + step.color : step.color
                }`}>
                  {step.active ? <Loader2 className="w-4 h-4 animate-spin" /> : <StepIcon className="w-4 h-4" />}
                </div>
                <span className="text-[11px] font-medium text-[var(--text-primary)] truncate w-full">{step.name.split("").join("\u200B")}</span>
                <span className="text-[10px] font-mono text-slate-400 mt-0.5">{step.time}</span>
              </div>
              {idx < pipelineSteps.length - 1 && (
                <ArrowRight className="w-3.5 h-3.5 text-slate-600 shrink-0 mx-0.5" />
              )}
            </div>
          );
        }) : (
          <p className="w-full py-3 text-center text-[11px] text-slate-500">
            {locale === "vi" ? "Pipeline chưa báo cáo sự kiện bước." : "The pipeline has not reported stage events."}
          </p>
        )}
      </div>

      {/* Expandable Granular Stage Details matching tests & accessibility */}
      <details className="mt-3 group rounded-lg border border-slate-800/60 bg-slate-950/40 text-xs" open={showDetails}>
        <summary
          className="flex min-h-8 cursor-pointer list-none items-center justify-between gap-3 px-2.5 py-1.5 font-semibold text-slate-400 hover:text-[var(--text-primary)] [&::-webkit-details-marker]:hidden"
          onClick={(e) => {
            e.preventDefault();
            setShowDetails((prev) => !prev);
          }}
        >
          <span className="flex min-w-0 items-center gap-1.5">
            <Timer className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{workflowTitle}</span>
            <span aria-hidden="true" className="font-normal text-slate-600">·</span>
            <span className="font-normal text-slate-400">{title}</span>
          </span>
          {typeof elapsed === "number" && <span>{serverDurationLabel} · {(elapsed / 1000).toFixed(2)}s</span>}
        </summary>
        <div className="ui-expand-enter border-t border-slate-800/80 px-2.5 py-2">
          <p className="mb-2 text-[11px] leading-relaxed text-slate-500">
            {locale === "vi" ? "Chỉ các bước và thời lượng do pipeline báo cáo mới được hiển thị." : "Only stages and durations reported by the pipeline are shown."}
          </p>
          <div role="status" aria-live="polite" aria-atomic="true" aria-label={title} className="sr-only">
            {stageAnnouncement}
          </div>
          <div data-testid="execution-stage-list" aria-label={title}>
            {currentStages.length > 0 ? (
              <ul className="space-y-1 text-slate-400">
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
                            <span key={counter.key} className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-muted)]">
                              {counter.value} {counter.label}
                            </span>
                          ))}
                        </span>
                      </span>
                      {typeof measuredElapsed === "number" && (
                        <span className="shrink-0 font-mono tabular-nums text-slate-400" aria-label={`${isLocalElapsed ? localElapsedLabel : serverElapsedLabel}: ${measuredElapsed.toFixed(0)} ms`}>
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
            <ul className="space-y-1 text-slate-400">
              {trace.stages.map((stage) => (
                <li key={`${stage.name}-${stage.status}`} className="flex items-center justify-between gap-3 py-1">
                  <span className="flex min-w-0 items-center gap-2">
                    <StatusIcon status={stage.status} />
                    <span>{stageLabel(stage.name, locale)}{stage.status !== "completed" ? ` · ${statusLabel(stage.status, locale)}` : ""}</span>
                  </span>
                  <span className="shrink-0 font-mono tabular-nums text-slate-400">
                    {serverElapsedLabel} · {typeof stage.elapsed_ms === "number" ? `${stage.elapsed_ms.toFixed(0)} ms` : unavailableElapsed}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </details>
    </div>
  );
}
