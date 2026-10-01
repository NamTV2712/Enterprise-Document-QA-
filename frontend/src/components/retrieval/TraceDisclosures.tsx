import { memo } from "react";
import { ShieldAlert } from "lucide-react";

import {
  SCORE_KEYS,
  SCORE_LABELS,
  availableScoreKeys,
  productionParityEntries,
  scoreFamilyDefinition,
  scoreSemanticsNote,
  scopeSummary,
  stageStatusLabel,
} from "../../lib/traceModel";
import type { RetrievalCandidate, RetrievalTrace } from "../../types";

interface TraceDisclosuresProps {
  vi: boolean;
  trace: RetrievalTrace;
  candidates: RetrievalCandidate[];
}

/**
 * What this trace measured, what it did not run, and what its scores mean.
 *
 * The score families are listed with the API's own scale and definition so they
 * are never read as one comparable number, and production-only stages are named
 * as not executed instead of being implied by the control layout.
 */
export const TraceDisclosures = memo(function TraceDisclosures({ vi, trace, candidates }: TraceDisclosuresProps) {
  const families = availableScoreKeys(trace, candidates);
  const note = scoreSemanticsNote(trace);
  const parity = productionParityEntries(trace);
  const scope = scopeSummary(trace.scope, vi);

  return (
    <div className="console-card retrieval-disclosures">
      <div className="console-card__header">
        <div className="min-w-0">
          <h2 className="console-card__title">{vi ? "Cách đọc trace này" : "How to read this trace"}</h2>
          <p className="console-card__subtitle">
            {vi
              ? `Trace ${trace.trace_version ?? "chưa có phiên bản"} · inspection, không phải production.`
              : `Trace ${trace.trace_version ?? "without a reported version"} · inspection, not production.`}
          </p>
        </div>
      </div>
      <div className="console-card__body retrieval-disclosures__body">
        {note && <p className="retrieval-disclosures__note">{note}</p>}

        <div className="retrieval-disclosures__group">
          <h3 className="console-field__label">{vi ? "Điểm theo từng họ" : "Score families in this trace"}</h3>
          <ul className="retrieval-family-list" data-testid="score-family-list">
            {families.map((key) => {
              const definition = scoreFamilyDefinition(trace.score_semantics, key);
              return (
                <li key={key} className="retrieval-family">
                  <span className="console-chip">{SCORE_LABELS[key]}</span>
                  <span className="retrieval-family__scale">{definition?.scale ?? (vi ? "Chưa có thang đo" : "Scale not reported")}</span>
                  <p className="retrieval-family__definition">
                    {definition?.definition ?? (vi ? "Trace không mô tả họ điểm này." : "This trace does not describe this family.")}
                  </p>
                </li>
              );
            })}
            {families.length === 0 && (
              <li className="retrieval-family__definition">
                {vi ? "Trace không báo cáo họ điểm nào." : "This trace reported no score family."}
              </li>
            )}
          </ul>
        </div>

        <div className="retrieval-disclosures__group">
          <h3 className="console-field__label">{vi ? "Không chạy trong inspection" : "Not executed in inspection"}</h3>
          <ul className="retrieval-parity-list">
            {parity.map((entry) => (
              <li key={entry.name} className="retrieval-parity">
                <ShieldAlert aria-hidden="true" />
                <span className="retrieval-parity__name">{entry.name}</span>
                <span className="console-chip">{stageStatusLabel(entry.status, vi)}</span>
              </li>
            ))}
            {parity.length === 0 && (
              <li className="retrieval-parity">
                <span>{vi ? "Trace không báo cáo production parity." : "This trace did not report production parity."}</span>
              </li>
            )}
          </ul>
          {trace.production_parity?.reason && <p className="retrieval-disclosures__note">{trace.production_parity.reason}</p>}
        </div>

        <div className="retrieval-disclosures__group">
          <h3 className="console-field__label">{vi ? "Phạm vi hiệu lực" : "Effective scope"}</h3>
          <p className="retrieval-disclosures__note">
            {scope ?? (vi ? "Trace không báo cáo phạm vi." : "This trace did not report a scope.")}
          </p>
        </div>
      </div>
      <div className="console-card__footer">
        <span className="text-xs text-[var(--text-muted)]">
          {vi
            ? `Trace cung cấp ${families.length}/${SCORE_KEYS.length} họ điểm; mỗi họ có thang đo riêng.`
            : `The trace reported ${families.length} of ${SCORE_KEYS.length} score families; each has its own scale.`}
        </span>
      </div>
    </div>
  );
});
