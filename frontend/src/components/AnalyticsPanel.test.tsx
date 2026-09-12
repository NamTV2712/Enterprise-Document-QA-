import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { AnalyticsPanel } from "./AnalyticsPanel";
import { clearAnalytics, recordAnalyticsEvent } from "../lib/analyticsStore";
import { LocaleProvider } from "../lib/i18n";

describe("AnalyticsPanel", () => {
  afterEach(() => clearAnalytics());

  test("uses a segmented time range and keeps the visible list in range", () => {
    recordAnalyticsEvent({ kind: "query_completed", at: Date.now() - 60 * 60 * 1000 });
    recordAnalyticsEvent({ kind: "query_error", at: Date.now() - 26 * 60 * 60 * 1000 });

    render(<LocaleProvider><AnalyticsPanel /></LocaleProvider>);
    fireEvent.click(screen.getByRole("radio", { name: "24 hours" }));

    expect(screen.getByRole("radio", { name: "24 hours" })).toHaveAttribute("aria-checked", "true");
    const activity = screen.getByRole("list", { name: "Activity in selected time range" });
    expect(activity).toHaveTextContent("query completed");
    expect(activity).not.toHaveTextContent("query error");
  });
});
