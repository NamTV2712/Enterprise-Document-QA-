import type {
  FailureCategory, NativeComparison, NativeFailures, NativeMetricDefinition, NativeMetricId, NativeTrends,
} from "../../lib/evaluationTypes";
import { MetricCounts, metricValue, type EvaluationLocale } from "./NativeMetrics";

export const failureLabels: Record<FailureCategory, { en: string; vi: string }> = {
  fallback_expectation_mismatch: { en: "Fallback expectation mismatch", vi: "Fallback không khớp kỳ vọng" },
  invalid_citation_index: { en: "Invalid citation indices", vi: "Chỉ số trích dẫn không hợp lệ" },
  missing_required_keyword: { en: "Missing required keywords", vi: "Thiếu từ khóa bắt buộc" },
  unavailable_prerequisite: { en: "Unavailable prerequisites", vi: "Điều kiện tiên quyết không khả dụng" },
};
function definitionLabel(id: string, definitions: NativeMetricDefinition[]) { return definitions.find((item) => item.metric_id === id)?.label ?? id; }
function delta(value: number | null): string { return value === null ? "Not reported" : `${value > 0 ? "+" : ""}${value.toFixed(3)}`; }

export function ComparisonResults({ comparison, definitions, locale = "en" }: { comparison: NativeComparison; definitions: NativeMetricDefinition[]; locale?: EvaluationLocale }) {
  const vi = locale === "vi";
  return <section className="evaluation-analysis" aria-labelledby="evaluation-compare-results">
    <header><div><h3 id="evaluation-compare-results">{vi ? "So sánh backend" : "Backend comparison"}</h3><p>{comparison.baseline_run_id} → {comparison.candidate_run_id}</p></div>
      <span className={`evaluation-state evaluation-state--${comparison.eligible_for_complete_comparison ? "computed" : "incompatible"}`}>{comparison.eligible_for_complete_comparison ? (vi ? "Đủ điều kiện đầy đủ" : "Complete comparison eligible") : (vi ? "Không tương thích đầy đủ" : "Not fully compatible")}</span></header>
    <p>{vi ? "Delta tuyệt đối do backend tính: candidate − baseline. Không phải tuyên bố người thắng hay ý nghĩa thống kê." : "Backend absolute delta: candidate − baseline. This is not a winner or statistical-significance claim."}</p>
    {!comparison.same_case_universe && <p className="evaluation-warning">{vi ? "Tập case không giống nhau." : "Case universes differ."}</p>}
    {comparison.eligibility_reasons.length > 0 && <ul className="evaluation-reasons">{comparison.eligibility_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}
    <div className="evaluation-comparison-list">{comparison.metrics.map((metric) => <article key={`${metric.metric_id}:${metric.metric_version}`}>
      <header><h4>{definitionLabel(metric.metric_id, definitions)} · v{metric.metric_version}</h4><span className={`evaluation-state evaluation-state--${metric.status}`}>{metric.status}</span></header>
      <div className="evaluation-compare-values">
        <div><span>{vi ? "Baseline" : "Baseline"}</span><strong>{metricValue(metric.baseline, locale)}</strong><MetricCounts metric={metric.baseline} locale={locale} /></div>
        <div><span>{vi ? "Candidate" : "Candidate"}</span><strong>{metricValue(metric.candidate, locale)}</strong><MetricCounts metric={metric.candidate} locale={locale} /></div>
        <div><span>Candidate − baseline</span><strong>{delta(metric.candidate_minus_baseline)}</strong><small>{metric.same_computed_case_coverage ? (vi ? "Cùng độ phủ case đã tính" : "Same computed-case coverage") : (vi ? "Độ phủ case đã tính khác nhau" : "Computed-case coverage differs")}</small></div>
      </div>
      {metric.reason_code && <p className="evaluation-reason">{metric.reason_code}</p>}
    </article>)}</div>
    <p className="evaluation-note">{comparison.total_cases} {vi ? "case trong so sánh; các case baseline-only/candidate-only vẫn giữ trạng thái unpaired." : "cases in comparison; baseline-only and candidate-only cases remain unpaired."}</p>
  </section>;
}

function pointY(value: number) { return 112 - Math.max(0, Math.min(1, value)) * 92; }
export function TrendsView({ trends, definitions, locale = "en" }: { trends: NativeTrends; definitions: NativeMetricDefinition[]; locale?: EvaluationLocale }) {
  const vi = locale === "vi";
  if (trends.total_points === 0) return <div className="evaluation-empty"><strong>{vi ? "Chưa có lịch sử native đã publish" : "No published native trend history"}</strong><p>{vi ? "Không có điểm demo hoặc nội suy được thêm." : "No demo or interpolated observations are added."}</p></div>;
  const charts = trends.groups.map((group) => {
    const width = 520;
    const left = 32;
    const right = 12;
    const plot = width - left - right;
    const denominator = Math.max(1, group.points.length - 1);
    return (
      <article key={group.binding_group}>
        <header>
          <h4>{vi ? "Nhóm binding" : "Binding group"} · v{group.metric_version}</h4>
          <code>{group.binding_group}</code>
        </header>
        <svg viewBox={`0 0 ${width} 140`} role="img" aria-label={`${definitionLabel(group.metric_id, definitions)} ${vi ? "theo lần publish" : "by publication"}`}>
          {[0, 0.5, 1].map((tick) => (
            <g key={tick}><line x1={left} x2={width - right} y1={pointY(tick)} y2={pointY(tick)} /><text x={left - 6} y={pointY(tick) + 3}>{tick.toFixed(1)}</text></g>
          ))}
          {group.points.map((point, index) => {
            if (point.aggregate.status !== "computed" || point.aggregate.value === null) return null;
            const x = left + (index / denominator) * plot;
            const y = pointY(point.aggregate.value);
            return <circle key={`${point.run_id}:${point.report_digest}`} cx={x} cy={y} r="4"><title>{point.run_id}: {point.aggregate.value.toFixed(3)}</title></circle>;
          })}
        </svg>
        <div className="evaluation-trend-table" role="table" aria-label={vi ? "Bảng quan sát xu hướng" : "Trend observations table"}>
          {group.points.map((point) => (
            <div role="row" key={`${point.run_id}:${point.report_digest}`}>
              <span role="cell">{point.run_id}</span>
              <span role="cell">{new Date(point.published_at).toLocaleString()}</span>
              <span role="cell">{metricValue(point.aggregate, locale)}</span>
              <span role="cell">{point.aggregate.denominator} / {point.aggregate.total_cases}</span>
            </div>
          ))}
        </div>
      </article>
    );
  });
  return (
    <section className="evaluation-analysis" aria-labelledby="evaluation-trends-results">
      <header><div><h3 id="evaluation-trends-results">{definitionLabel(trends.metric_id, definitions)}</h3><p>{trends.total_points} {vi ? "quan sát backend" : "backend observations"}</p></div></header>
      <div className="evaluation-trend-groups">{charts}</div>
      <p className="evaluation-note">{vi ? "Các nhóm binding hiển thị riêng. Điểm thiếu không được nối, làm mượt hay dự báo." : "Binding groups remain separate. Missing points are not connected, smoothed, or forecast."}</p>
    </section>
  );
}

export function FailuresView({ failures, definitions, locale = "en" }: { failures: NativeFailures; definitions: NativeMetricDefinition[]; locale?: EvaluationLocale }) {
  const vi = locale === "vi";
  if (failures.total === 0) return <div className="evaluation-empty"><strong>{vi ? "Không có failure trong phạm vi này" : "No failures in this scope"}</strong><p>{vi ? "Không áp dụng ngưỡng điểm tùy ý." : "No arbitrary score threshold was applied."}</p></div>;
  const max = Math.max(1, ...failures.category_counts.map((item) => item.count));
  return <section className="evaluation-analysis" aria-labelledby="evaluation-failure-results">
    <header><div><h3 id="evaluation-failure-results">{vi ? "Phân tích failure" : "Failure analysis"}</h3><p>{failures.total} {vi ? "finding do backend phân loại" : "backend-classified findings"}</p></div></header>
    <div className="evaluation-failure-bars">{failures.category_counts.map((item) => <div key={item.category_id}><span>{failureLabels[item.category_id][locale]}</span><span className="evaluation-failure-track"><span style={{ width: `${item.count / max * 100}%` }} /></span><strong>{item.count}</strong></div>)}</div>
    <ul className="evaluation-finding-list">{failures.items.map((item) => <li key={`${item.category_id}:${item.case_id}:${item.metric_id}`}>
      <div><strong>{failureLabels[item.category_id][locale]}</strong><span className={`evaluation-state evaluation-state--${item.metric_status}`}>{item.metric_status}</span></div>
      <dl><div><dt>Case ID</dt><dd>{item.case_id}</dd></div><div><dt>{vi ? "Chỉ số" : "Metric"}</dt><dd>{definitionLabel(item.metric_id, definitions)} · v{item.metric_version}</dd></div><div><dt>{vi ? "Giá trị" : "Value"}</dt><dd>{metricValue({ status: item.metric_status, value: item.value }, locale)}</dd></div><div><dt>{vi ? "Lý do" : "Reason"}</dt><dd>{item.reason_code ?? (vi ? "Chưa được báo cáo" : "Not reported")}</dd></div><div><dt>Context hash</dt><dd>{item.context_sha256 ?? (vi ? "Chưa được báo cáo" : "Not reported")}</dd></div></dl>
    </li>)}</ul>
    <p className="evaluation-note">{vi ? "Unavailable prerequisite không tự động là model failure. Nội dung question, answer, ground truth và evidence không được hiển thị." : "An unavailable prerequisite is not automatically a model failure. Question, answer, ground truth and evidence text are not displayed."}</p>
  </section>;
}
