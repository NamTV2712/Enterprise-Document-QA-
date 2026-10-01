import { describe, expect, test, vi } from "vitest";
import { createOperationalApi, OperationalApiError, projectLog, projectLogPage, projectSummary, projectTimeseries } from "./operationalApi";
import { analyticsMetrics, analyticsRanges } from "./operationalTypes";
import { summaryFixture, seriesFixture, logPageFixture, logFixture, hiddenOperationalFields, operationalCursor, configurationFixture } from "../test/operationalFixtures";

describe("UI-012 operational transport", () => {
  test("provider status projects descriptive flags only and uses no bearer", async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ items: [{ role: "generator", provider: "groq", configuration_status: "configured", credential_status: "configured", availability_status: "unknown", ...hiddenOperationalFields }], ...hiddenOperationalFields })));
    const signal = new AbortController().signal;
    const result = await createOperationalApi({ baseUrl: "http://fixture", fetchImpl }).providerStatus(signal);
    expect(result).toEqual({ provider: "groq", configuration_status: "configured", credential_status: "configured", availability_status: "unknown" }); expect(fetchImpl.mock.calls[0][0]).toBe("http://fixture/models"); expect(fetchImpl.mock.calls[0][1]?.signal).toBe(signal); expect(new Headers(fetchImpl.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  });
  test.each(analyticsRanges)("summary %s uses protected GET, signal and exact null/count populations", async range => {
    const data = summaryFixture(range, true), fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ ...data, ...hiddenOperationalFields })));
    const api = createOperationalApi({ baseUrl: "http://fixture", fetchImpl }), controller = new AbortController();
    expect(await api.summary("synthetic", range, controller.signal)).toEqual(data);
    const [url, init] = fetchImpl.mock.calls[0]; expect(url).toBe(`http://fixture/analytics/summary?range=${range}`); expect(init?.signal).toBe(controller.signal); expect(init?.method).toBe("GET"); expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic");
  });
  test.each(analyticsMetrics)("timeseries %s preserves bucket values and parameters", async metric => {
    const data = seriesFixture("30d", "day", metric), fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(data)));
    const controller = new AbortController(), result = await createOperationalApi({ baseUrl: "http://fixture", fetchImpl }).timeseries("synthetic", "30d", "day", metric, controller.signal);
    expect(result).toEqual(data); expect(String(fetchImpl.mock.calls[0][0])).toContain(`range=30d&interval=day&metric=${metric}`); expect(fetchImpl.mock.calls[0][1]?.signal).toBe(controller.signal);
  });
  test.each(["request", "job"] as const)("logs %s passes opaque cursor and filters unchanged", async category => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(logPageFixture()))), controller = new AbortController();
    const result = await createOperationalApi({ baseUrl: "http://fixture", fetchImpl }).logs("synthetic", { category, level: "warning", cursor: operationalCursor, limit: 100 }, controller.signal);
    const query = new URL(String(fetchImpl.mock.calls[0][0])).searchParams;
    expect(query.get("cursor")).toBe(operationalCursor); expect(query.get("category")).toBe(category); expect(query.get("level")).toBe("warning"); expect(query.get("limit")).toBe("100"); expect(result.next_cursor).toBe(operationalCursor); expect(fetchImpl.mock.calls[0][1]?.signal).toBe(controller.signal);
  });
  test("projects every hidden field out before page state, including metadata", () => {
    const row = projectLog({ ...logFixture(), ...hiddenOperationalFields, metadata: { ...logFixture().metadata, ...hiddenOperationalFields } });
    expect(row).toEqual(logFixture()); expect(JSON.stringify(row)).not.toContain("HIDDEN_");
    expect(projectSummary({ ...summaryFixture(), ...hiddenOperationalFields })).toEqual(summaryFixture());
  });
  test("keeps severity/outcome separate and preserves returned order and null/zero", () => {
    const result = projectLogPage(logPageFixture()); expect(result.items[0]).toMatchObject({ level: "info", outcome: "cancelled", duration_ms: 0 }); expect(result.items[1]).toMatchObject({ level: "warning", outcome: "failed", error_code: "budget_exhausted", duration_ms: null }); expect(result.items.map(x => x.record_id)).toEqual(logPageFixture().items.map(x => x.record_id));
  });
  test.each([401, 403, 404, 422, 503, 500])("maps HTTP %s without reading sensitive bodies", async status => {
    const api = createOperationalApi({ fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(hiddenOperationalFields), { status })) });
    await expect(api.logs("synthetic")).rejects.toMatchObject({ status });
    try { await api.logs("synthetic"); } catch (error) { expect(String(error)).not.toContain("HIDDEN_"); }
  });
  test("private credentials required before fetch", async () => { const fetchImpl = vi.fn<typeof fetch>(); await expect(createOperationalApi({ fetchImpl }).summary("", "24h")).rejects.toBeInstanceOf(OperationalApiError); expect(fetchImpl).not.toHaveBeenCalled(); });
  test("settings projects safe facts, public read has no bearer, protected flags have bearer", async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValueOnce(new Response(JSON.stringify({ api_version: "1.0", retrieval: { default: "balanced", ...hiddenOperationalFields }, ...hiddenOperationalFields }))).mockResolvedValueOnce(new Response(JSON.stringify({ ...configurationFixture, ...hiddenOperationalFields })));
    const controller = new AbortController(), api = createOperationalApi({ baseUrl: "http://fixture", fetchImpl });
    expect(await api.settingsFacts(controller.signal)).toEqual({ api_version: "1.0", default_retrieval: "balanced" }); expect(new Headers(fetchImpl.mock.calls[0][1]?.headers).has("Authorization")).toBe(false); expect(fetchImpl.mock.calls[0][1]?.signal).toBe(controller.signal);
    expect(await api.configuration("synthetic", controller.signal)).toEqual(configurationFixture); expect(new Headers(fetchImpl.mock.calls[1][1]?.headers).get("Authorization")).toBe("Bearer synthetic");
  });
  test("accepts 720 buckets but refuses 721 and reversed ordering", () => {
    const data = seriesFixture(); data.points = Array.from({ length: 720 }, (_, i) => ({ started_at: new Date(Date.UTC(2026, 8, 1, i)).toISOString(), ended_at: new Date(Date.UTC(2026, 8, 1, i + 1)).toISOString(), value: 0, denominator: 0 }));
    expect(projectTimeseries(data).points).toHaveLength(720); expect(() => projectTimeseries({ ...data, points: [...data.points, data.points[0]] })).toThrow(); expect(() => projectTimeseries({ ...seriesFixture(), points: seriesFixture().points.reverse() })).toThrow();
  });
  test.each(["Bearer synthetic-secret", "C:\\Users\\Private\\file", "/home/private/file", "unsafe\ntext"])("rejects unsafe returned identifier %s", text => { expect(() => projectLog({ ...logFixture(), correlation_id: text })).toThrow(); });
  test("rejects invalid schema rather than displaying a false empty", async () => { const api = createOperationalApi({ fetchImpl: vi.fn<typeof fetch>().mockResolvedValue(new Response("{}")) }); await expect(api.summary("synthetic", "24h")).rejects.toMatchObject({ status: 502 }); });
});
