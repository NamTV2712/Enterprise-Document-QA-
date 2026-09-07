import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { CommandPalette } from "./CommandPalette";
import { LocaleProvider } from "../lib/i18n";

describe("CommandPalette", () => {
  test("filters templates and never auto-sends them", () => {
    const onTemplate = vi.fn();
    render(<LocaleProvider><CommandPalette open onClose={vi.fn()} onNavigate={vi.fn()} onTemplate={onTemplate} onHelp={vi.fn()} onNewConversation={vi.fn()} /></LocaleProvider>);

    fireEvent.change(screen.getByRole("textbox", { name: "Search command palette" }), { target: { value: "risk groups" } });
    expect(screen.getByRole("button", { name: /Risk groups/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Risk groups/ }));
    expect(onTemplate).toHaveBeenCalledTimes(1);
  });
});
