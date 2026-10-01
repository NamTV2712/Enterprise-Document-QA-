import { memo } from "react";
import { CircleSlash2, CheckCircle2, Info } from "lucide-react";

import { formatDuration, stageStatus, stageStatusLabel } from "../../lib/traceModel";
import type { RetrievalTraceStage } from "../../types";

interface StageSummaryProps {
  vi: boolean;
  stages: RetrievalTraceStage[];
  /** Optional caption under the list, e.g. the pool the durations belong to. */
  note?: string | null;
}

function StatusIcon({ status }: { status: ReturnType<typeof stageStatus> }) {
  if (status === "executed") return <CheckCircle2 aria-hidden="true" />;
  if (status === "skipped") return <CircleSlash2 aria-hidden="true" />;
  return <Info aria-hidden="true" />;
}

/**
 * The named stages of one trace with their real execution state.
 *
 * A stage that did not run says so and carries the API's own reason; a stage
 * with no reported duration says "not reported" instead of showing 0 ms.
 */
export const StageSummary = memo(function StageSummary({ vi, stages, note }: StageSummaryProps) {
  return (
    <div className="retrieval-stages">
      <ul className="retrieval-stages__list">
        {stages.map((stage) => {
          const status = stageStatus(stage);
          return (
            <li key={stage.name} className={`retrieval-stage retrieval-stage--${status}`}>
              <span className={`retrieval-stage__status retrieval-stage__status--${status}`}>
                <StatusIcon status={status} />
                {stageStatusLabel(status, vi)}
              </span>
              <span className="retrieval-stage__name">{stage.name}</span>
              <span className="retrieval-stage__duration">
                {status === "executed" ? formatDuration(stage.elapsed_ms, vi) : "—"}
              </span>
              {stage.reason && <p className="retrieval-stage__reason">{stage.reason}</p>}
            </li>
          );
        })}
      </ul>
      {note && <p className="retrieval-stages__note">{note}</p>}
    </div>
  );
});
