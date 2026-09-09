import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { HelpDialog } from "./HelpDialog";
import { LocaleProvider } from "../lib/i18n";

describe("HelpDialog", () => {
  afterEach(() => {
    document.body.style.overflow = "";
    document.body.style.paddingRight = "";
    document.getElementById("root")?.remove();
  });

  test("locks the page, moves focus into the dialog, and closes with Escape", () => {
    const onClose = vi.fn();
    const appRoot = document.createElement("div");
    appRoot.id = "root";
    document.body.append(appRoot);
    const trigger = document.createElement("button");
    document.body.append(trigger);
    trigger.focus();

    const { unmount } = render(
      <LocaleProvider>
        <HelpDialog open onClose={onClose} />
      </LocaleProvider>,
    );

    expect(document.body.style.overflow).toBe("hidden");
    expect(appRoot).toHaveAttribute("inert");
    expect(screen.getByRole("button", { name: "Close help" })).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);

    unmount();
    expect(document.body.style.overflow).toBe("");
    expect(appRoot).not.toHaveAttribute("inert");
    expect(trigger).toHaveFocus();
    trigger.remove();
  });

  test("keeps the header outside the single scrollable dialog body", () => {
    render(<LocaleProvider><HelpDialog open onClose={vi.fn()} /></LocaleProvider>);

    const panel = document.querySelector<HTMLElement>(".help-dialog-panel");
    const header = document.querySelector<HTMLElement>(".help-dialog-panel__header");
    const body = document.querySelector<HTMLElement>(".help-dialog-panel__body");

    expect(panel).toContainElement(header);
    expect(panel).toContainElement(body);
    expect(body).not.toContainElement(header);
  });
});
