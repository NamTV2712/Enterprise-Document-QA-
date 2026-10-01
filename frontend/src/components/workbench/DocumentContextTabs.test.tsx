import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { LocaleProvider } from "../../lib/i18n";
import { DocumentContextTabs } from "./DocumentContextTabs";

describe("DocumentContextTabs", () => {
  afterEach(cleanup);

  test("keeps Notes conditional and supports roving keyboard selection", () => {
    const onTabChange = vi.fn();
    render(
      <LocaleProvider>
        <DocumentContextTabs activeTab="evidence" onTabChange={onTabChange} />
      </LocaleProvider>,
    );

    expect(screen.getByRole("tab", { name: "Evidence" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("tab", { name: "Notes" })).not.toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole("tab", { name: "Evidence" }), { key: "ArrowRight" });
    expect(onTabChange).toHaveBeenCalledWith("metadata");
  });

  test("exposes Notes only when an existing notes relationship is supplied", () => {
    render(
      <LocaleProvider>
        <DocumentContextTabs activeTab="notes" onTabChange={vi.fn()} hasNotes />
      </LocaleProvider>,
    );

    expect(screen.getByRole("tab", { name: "Notes" })).toHaveAttribute("aria-selected", "true");
  });
});
