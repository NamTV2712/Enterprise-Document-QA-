import type { NativeAggregateMetric, NativeCaseMetric, NativeMetricDefinition, SafeJobCase, NativeCaseResult } from "../../lib/evaluationTypes";

export type EvaluationLocale = "en" | "vi";
export function metricValue(metric: Pick<NativeCaseMetric, "status" | "value"> | undefined, locale: EvaluationLocale = "en"): string {
  if (!metric) return locale === "vi" ? "Chưa được báo cáo" : "Not reported";
  if (metric.status === "unavailable") return locale === "vi" ? "Không khả dụng" : "Unavailable";
  if (metric.status === "not_applicable") return locale === "vi" ? "Không áp dụng" : "Not applicable";
  if (metric.value === true) return locale === "vi" ? "Đúng (true)" : "True";
  if (metric.value === false) return locale === "vi" ? "Sai (false)" : "False";
  return typeof metric.value === "number" ? metric.value.toFixed(3) : (locale === "vi" ? "Chưa được báo cáo" : "Not reported");
}
export function MetricCounts({ metric, locale = "en" }: { metric: NativeAggregateMetric; locale?: EvaluationLocale }) {
  return <dl className="evaluation-counts">
    <div><dt>{locale === "vi" ? "Đã tính / tổng" : "Computed / total"}</dt><dd>{metric.denominator} / {metric.total_cases}</dd></div>
    <div><dt>{locale === "vi" ? "Không khả dụng" : "Unavailable"}</dt><dd>{metric.unavailable_count}</dd></div>
    <div><dt>{locale === "vi" ? "Không áp dụng" : "Not applicable"}</dt><dd>{metric.not_applicable_count}</dd></div>
  </dl>;
}
export function NativeMetrics({ definitions, aggregates = [], locale = "en" }: {
  definitions: NativeMetricDefinition[]; aggregates?: NativeAggregateMetric[]; locale?: EvaluationLocale;
}) {
  return <section className="evaluation-metrics" aria-label={locale === "vi" ? "Chỉ số native" : "Native metrics"}>
    {definitions.map((definition) => {
      const metric = aggregates.find((item) => item.metric_id === definition.metric_id && item.metric_version === definition.metric_version);
      return <article className="evaluation-metric" key={definition.metric_id}>
        <h2>{definition.label}</h2>
        <p className="evaluation-metric-value">{metricValue(metric, locale)}</p>
        {metric && <MetricCounts metric={metric} locale={locale} />}
        <details>
          <summary>{locale === "vi" ? "Định nghĩa" : "Definition"} · v{definition.metric_version}</summary>
          <p>{definition.meaning}</p>
          <dl className="evaluation-provenance">
            <div><dt>ID</dt><dd>{definition.metric_id}</dd></div>
            <div><dt>{locale === "vi" ? "Kiểu / khoảng" : "Type / range"}</dt><dd>{definition.value_kind} · [{definition.minimum}, {definition.maximum}]</dd></div>
            <div><dt>{locale === "vi" ? "Tổng hợp" : "Aggregate"}</dt><dd>{definition.aggregate_kind}</dd></div>
            <div><dt>{locale === "vi" ? "Hướng" : "Direction"}</dt><dd>{definition.direction}</dd></div>
            <div><dt>{locale === "vi" ? "Nguồn" : "Source"}</dt><dd>{definition.source}</dd></div>
            <div><dt>{locale === "vi" ? "Đầu vào bắt buộc" : "Required inputs"}</dt><dd>{definition.required_inputs.join(", ")}</dd></div>
          </dl>
          <p>{locale === "vi" ? "Không khả dụng và không áp dụng không phải là điểm 0. False là kết quả đã tính." : "Unavailable and not applicable are not zero scores. False is a computed result."}</p>
        </details>
      </article>;
    })}
  </section>;
}
export function NativeCases({ items, definitions, total, page, pageSize, onPage, locale = "en" }: {
  items: Array<SafeJobCase | NativeCaseResult>; definitions: NativeMetricDefinition[];
  total: number; page: number; pageSize: number; onPage: (page: number) => void; locale?: EvaluationLocale;
}) {
  return <section className="evaluation-cases" aria-label={locale === "vi" ? "Kết quả theo case" : "Case results"}>
    <h3>{locale === "vi" ? "Kết quả theo case" : "Case results"}</h3>
    <p>{locale === "vi" ? "Chỉ hiển thị ID, hash và chỉ số; không hiển thị nội dung case." : "Identifiers, hashes and metrics only; case text is not displayed."}</p>
    {items.length === 0 ? <p>{locale === "vi" ? "Chưa có kết quả bền vững trên trang này." : "No durable results on this page yet."}</p>
      : <ul className="evaluation-case-list">{items.map((item) => <li key={item.case_id}>
        <h4>{item.case_id}</h4>
        <dl>{item.metrics.map((metric) => <div key={metric.metric_id}>
          <dt>{definitions.find((definition) => definition.metric_id === metric.metric_id)?.label ?? metric.metric_id} · v{metric.metric_version}</dt>
          <dd>{metricValue(metric, locale)}{metric.reason_code && <span className="evaluation-reason"> · {metric.reason_code}</span>}</dd>
        </div>)}</dl>
        <details><summary>{locale === "vi" ? "Hash bằng chứng" : "Evidence hashes"}</summary>
          {"context_sha256" in item ? <p>{item.context_sha256 ?? (locale === "vi" ? "Chưa được báo cáo" : "Not reported")}</p>
            : <dl className="evaluation-provenance"><div><dt>Generation context</dt><dd>{item.generation_context_sha256 ?? "Not reported"}</dd></div><div><dt>Judge context</dt><dd>{item.judge_context_sha256 ?? "Not reported"}</dd></div><div><dt>Judge prompt</dt><dd>{item.judge_prompt_sha256}</dd></div></dl>}
        </details>
      </li>)}</ul>}
    <nav className="evaluation-pager" aria-label={locale === "vi" ? "Trang kết quả" : "Result pages"}>
      <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>{locale === "vi" ? "Trước" : "Previous"}</button>
      <span>{locale === "vi" ? "Trang" : "Page"} {page} · {total} {locale === "vi" ? "kết quả" : "results"}</span>
      <button type="button" disabled={page * pageSize >= total} onClick={() => onPage(page + 1)}>{locale === "vi" ? "Tiếp" : "Next"}</button>
    </nav>
  </section>;
}
