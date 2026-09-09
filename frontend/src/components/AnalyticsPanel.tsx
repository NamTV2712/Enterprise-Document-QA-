import { useMemo, useState } from "react";
import { Activity, Download, Trash2 } from "lucide-react";
import { clearAnalytics, exportAnalytics, readAnalyticsEvents } from "../lib/analyticsStore";
import { useLocale } from "../lib/i18n";
import { AnalyticsRange, getAnalyticsCutoff } from "../lib/analyticsRange";
import { SegmentedControl } from "./ui/SegmentedControl";

const EVENT_KINDS = ["query_completed", "query_error", "feedback"];

export function AnalyticsPanel() {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [events, setEvents] = useState(readAnalyticsEvents);
  const [range, setRange] = useState<AnalyticsRange>("7");
  const cutoff = getAnalyticsCutoff(range);
  const filtered = useMemo(() => events.filter((event) => event.at >= cutoff), [cutoff, events]);
  const counts = useMemo(
    () => filtered.reduce<Record<string, number>>((result, event) => {
      result[event.kind] = (result[event.kind] ?? 0) + 1;
      return result;
    }, {}),
    [filtered],
  );

  const download = () => {
    const url = URL.createObjectURL(new Blob([exportAnalytics(filtered)], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "enterprise-document-qa-local-analytics.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const rangeOptions = [
    { value: "24h", label: vi ? "24 giờ" : "24 hours" },
    { value: "7", label: vi ? "7 ngày" : "7 days" },
    { value: "30", label: vi ? "30 ngày" : "30 days" },
    { value: "all", label: vi ? "Tất cả" : "All time" },
  ];

  return (
    <section className="workspace-page workspace-page--wide" aria-labelledby="analytics-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-300">
            {vi ? "Dữ liệu trên thiết bị" : "On-device telemetry"}
          </p>
          <h1 id="analytics-title" className="mt-1 text-2xl font-bold text-[var(--text-primary)]">
            {vi ? "Analytics & diagnostics" : "Analytics & diagnostics"}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--text-muted)]">
            {vi ? "Đây chỉ là hoạt động local đã làm mờ nội dung. Không phải tổng usage backend/provider." : "This is local activity with content removed. It is not total backend/provider usage."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SegmentedControl label={vi ? "Khoảng thời gian" : "Time range"} value={range} options={rangeOptions} onValueChange={(value) => setRange(value as AnalyticsRange)} />
          <button type="button" onClick={download} className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-[var(--border-subtle)] px-3 text-xs font-semibold text-[var(--text-primary)] hover:surface-muted-hover">
            <Download className="h-3.5 w-3.5" aria-hidden="true" />{vi ? "Xuất" : "Export"}
          </button>
          <button type="button" onClick={() => { clearAnalytics(); setEvents([]); }} className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-rose-300/50 px-3 text-xs font-semibold text-rose-700 hover:bg-rose-500/10 dark:text-rose-300">
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />{vi ? "Xóa analytics" : "Clear analytics"}
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <article className="rounded-2xl border border-[var(--border-subtle)] surface-raised p-4">
          <Activity className="h-5 w-5 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />
          <div className="mt-3 text-2xl font-bold text-[var(--text-primary)]">{filtered.length}</div>
          <div className="text-xs text-[var(--text-muted)]">{vi ? "Sự kiện local" : "Local events"}</div>
        </article>
        {EVENT_KINDS.map((kind) => (
          <article key={kind} className="rounded-2xl border border-[var(--border-subtle)] surface-raised p-4">
            <div className="text-xs uppercase tracking-wide text-[var(--text-muted)]">{kind.replaceAll("_", " ")}</div>
            <div className="mt-3 text-2xl font-bold text-[var(--text-primary)]">{counts[kind] ?? 0}</div>
            <div className="text-xs text-[var(--text-muted)]">{vi ? "Trong khoảng đã chọn" : "In selected range"}</div>
          </article>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-[var(--border-subtle)] surface-raised p-4">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">{vi ? "Hoạt động gần đây" : "Recent activity"}</h2>
        {events.length === 0 ? (
          <p className="mt-3 text-sm text-[var(--text-muted)]">{vi ? "Chưa có hoạt động local." : "No local activity recorded yet."}</p>
        ) : filtered.length === 0 ? (
          <p className="mt-3 text-sm text-[var(--text-muted)]">{vi ? "Không có hoạt động trong khoảng đã chọn." : "No local activity in this time range."}</p>
        ) : (
          <div className="mt-3 divide-y divide-[var(--border-subtle)]" role="list" aria-label={vi ? "Hoạt động trong khoảng đã chọn" : "Activity in selected time range"}>
            {filtered.slice(0, 20).map((event) => (
              <div key={event.id} role="listitem" className="flex flex-wrap items-center justify-between gap-2 py-2 text-xs">
                <span className="font-semibold text-[var(--text-primary)]">{event.kind.replaceAll("_", " ")}</span>
                <span className="text-[var(--text-muted)]">{event.ticker ?? (vi ? "Không gắn công ty" : "No ticker")} · {new Date(event.at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
