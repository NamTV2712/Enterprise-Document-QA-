import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { CommandPalette } from "./CommandPalette";
import { LocaleProvider } from "../lib/i18n";
import type { ContextualCommandDefinition } from "../lib/commandRegistry";

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("CommandPalette", () => {
  test("filters templates and never auto-sends them", () => {
    const onTemplate = vi.fn();
    render(<LocaleProvider><CommandPalette open onClose={vi.fn()} onNavigate={vi.fn()} onTemplate={onTemplate} onHelp={vi.fn()} onNewConversation={vi.fn()} /></LocaleProvider>);

    fireEvent.change(screen.getByRole("combobox", { name: "Search command palette" }), { target: { value: "risk groups" } });
    expect(screen.getByRole("option", { name: /Risk groups/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("option", { name: /Risk groups/ }));
    expect(onTemplate).toHaveBeenCalledTimes(1);
  });

  test("shows only the active locale and executes the active row with Enter", () => {
    localStorage.setItem("sec_qa_locale", "vi");
    const onTemplate = vi.fn();
    const onClose = vi.fn();
    render(<LocaleProvider><CommandPalette open onClose={onClose} onNavigate={vi.fn()} onTemplate={onTemplate} onHelp={vi.fn()} onNewConversation={vi.fn()} /></LocaleProvider>);

    const input = screen.getByRole("combobox", { name: "Tìm trong bảng lệnh" });
    fireEvent.change(input, { target: { value: "rủi ro" } });
    expect(screen.getByRole("option", { name: /Nhóm rủi ro/ })).toBeInTheDocument();
    expect(screen.queryByText("Risk groups")).not.toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onTemplate).toHaveBeenCalledTimes(1);
    expect(onTemplate.mock.calls[0][0].id).toBe("risk-groups");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test("keeps pointer and keyboard activation on the same navigation command", () => {
    const onNavigate = vi.fn();
    render(<LocaleProvider><CommandPalette open onClose={vi.fn()} onNavigate={onNavigate} onTemplate={vi.fn()} onHelp={vi.fn()} onNewConversation={vi.fn()} /></LocaleProvider>);

    const input = screen.getByRole("combobox", { name: "Search command palette" });
    fireEvent.change(input, { target: { value: "Documents" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onNavigate).toHaveBeenCalledWith("documents");
  });

  test("executes runtime-bound contextual commands without owning their effects", () => {
    const run = vi.fn();
    const command: ContextualCommandDefinition = {
      id: "copy-current-answer",
      labelKey: "palette.copyAnswer",
      descriptionKey: "palette.copyAnswerDescription",
      icon: "copy",
      run,
    };
    render(<LocaleProvider><CommandPalette open onClose={vi.fn()} onNavigate={vi.fn()} onTemplate={vi.fn()} onHelp={vi.fn()} onNewConversation={vi.fn()} contextualCommands={[command]} /></LocaleProvider>);

    fireEvent.change(screen.getByRole("combobox", { name: "Search command palette" }), { target: { value: "copy current answer" } });
    fireEvent.click(screen.getByRole("option", { name: /Copy current answer/ }));
    expect(run).toHaveBeenCalledTimes(1);
  });
});
