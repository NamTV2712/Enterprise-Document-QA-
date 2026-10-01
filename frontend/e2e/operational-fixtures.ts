import type { Page, Route } from "@playwright/test";
import { API_ORIGIN, installApiFixtures } from "./fixtures";
import { configurationFixture, hiddenOperationalFields, jobLogFixture, logFixture, operationalCursor, operationalToken, seriesFixture, summaryFixture } from "../src/test/operationalFixtures";
import type { AnalyticsRange, AnalyticsInterval, AnalyticsMetric } from "../src/lib/operationalTypes";
const cors = { "access-control-allow-origin": "http://localhost:4173", "access-control-allow-headers": "Authorization, Content-Type", "access-control-allow-methods": "GET, OPTIONS" };
export async function installOperationalFixture(page: Page, options: { publicMode?: boolean; empty?: boolean; failure?: number; delayedRange?: boolean } = {}) {
  await installApiFixtures(page);
  const calls: Array<{ path: string; query: string; authorization: string | null }> = [];
  async function respond(route: Route, status: number, body: unknown) { await route.fulfill({ status, headers: { ...cors, "content-type": "application/json" }, body: JSON.stringify(body) }); }
  const handler = async (route: Route) => {
    const request = route.request(), url = new URL(request.url());
    if (request.method() === "OPTIONS") { await route.fulfill({ status: 204, headers: cors }); return; }
    calls.push({ path: url.pathname, query: url.search, authorization: request.headers().authorization ?? null });
    if (request.method() !== "GET") { await respond(route, 405, {}); return; }
    const privateRead = url.pathname !== "/system/info";
    if (privateRead && options.publicMode) { await respond(route, 404, hiddenOperationalFields); return; }
    if (privateRead && request.headers().authorization !== `Bearer ${operationalToken}`) { await respond(route, 401, hiddenOperationalFields); return; }
    if (url.pathname === "/system/configuration-status") { await respond(route, 200, { ...configurationFixture, ...hiddenOperationalFields }); return; }
    if (url.pathname === "/system/info") { await respond(route, 200, { api_version: "1.0", retrieval: { default: "balanced" }, ...hiddenOperationalFields }); return; }
    if (options.failure) { await respond(route, options.failure, hiddenOperationalFields); return; }
    const range = (url.searchParams.get("range") ?? "24h") as AnalyticsRange;
    if (options.delayedRange && range === "24h") await new Promise(resolve => setTimeout(resolve, 400));
    if (url.pathname === "/analytics/summary") {
      const data = summaryFixture(range, options.empty); if (options.delayedRange && range === "7d") data.requests.terminal_count = 77;
      await respond(route, 200, { ...data, ...hiddenOperationalFields }); return;
    }
    if (url.pathname === "/analytics/timeseries") {
      const interval = (url.searchParams.get("interval") ?? "hour") as AnalyticsInterval, metric = (url.searchParams.get("metric") ?? "request_count") as AnalyticsMetric;
      const data = seriesFixture(range, interval, metric, options.empty);
      const buckets = range === "30d" ? (interval === "hour" ? 720 : 30) : range === "7d" ? (interval === "hour" ? 168 : 7) : interval === "hour" ? 24 : 1;
      const end = Date.parse("2026-09-27T00:00:00Z"), step = (interval === "hour" ? 1 : 24) * 3600000, start = end - buckets * step;
      data.started_at = new Date(start).toISOString(); data.ended_at = new Date(end).toISOString();
      data.points = Array.from({ length: buckets }, (_, i) => ({ started_at: new Date(start + i * step).toISOString(), ended_at: new Date(start + (i + 1) * step).toISOString(), value: i === buckets - 1 && !options.empty ? (metric.includes("duration") ? 0 : 2) : metric.includes("duration") ? null : 0, denominator: i === buckets - 1 && !options.empty ? 2 : 0 }));
      await respond(route, 200, { ...data, ...hiddenOperationalFields }); return;
    }
    if (url.pathname === "/logs") {
      const next = url.searchParams.has("cursor");
      let items = options.empty ? [] : next ? [logFixture("tel_next")] : [logFixture(), jobLogFixture()];
      const category = url.searchParams.get("category"), level = url.searchParams.get("level");
      if (category) items = items.filter(item => item.category === category);
      if (level) items = items.filter(item => item.level === level);
      await respond(route, 200, { items: items.map(item => ({ ...item, ...hiddenOperationalFields, metadata: { ...item.metadata, ...hiddenOperationalFields } })), has_more: !next && items.length > 0, next_cursor: !next && items.length > 0 ? operationalCursor : null, limit: 50 }); return;
    }
    await respond(route, 404, {});
  };
  for (const path of ["/analytics/**", "/logs**", "/system/configuration-status", "/system/info"]) await page.route(`${API_ORIGIN}${path}`, handler);
  return { calls };
}
