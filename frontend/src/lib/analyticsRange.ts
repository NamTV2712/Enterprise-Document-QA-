export type AnalyticsRange = "24h" | "7" | "30" | "all";

export function getAnalyticsCutoff(range: AnalyticsRange, now = Date.now()): number {
  if (range === "all") return 0;
  const hours = range === "24h" ? 24 : Number(range) * 24;
  return now - hours * 60 * 60 * 1000;
}
