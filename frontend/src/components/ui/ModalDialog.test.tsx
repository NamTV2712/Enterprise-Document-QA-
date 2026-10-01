import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ModalDialog } from "./ModalDialog";

afterEach(() => cleanup());

describe("ModalDialog", () => {
  test("keeps Escape on the topmost nested dialog", () => {
    const outerClose = vi.fn();
    const innerClose = vi.fn();

    render(
      <>
        <ModalDialog open onClose={outerClose} ariaLabel="Outer" className="outer">
          <button type="button">Outer action</button>
        </ModalDialog>
        <ModalDialog open onClose={innerClose} ariaLabel="Inner" className="inner">
          <textarea aria-label="Inner text" />
        </ModalDialog>
      </>,
    );

    fireEvent.keyDown(document, { key: "Escape" });
    expect(innerClose).toHaveBeenCalledTimes(1);
    expect(outerClose).not.toHaveBeenCalled();
  });

  test("includes textarea in the focus trap", () => {
    render(
      <ModalDialog open onClose={() => {}} ariaLabel="Text dialog" className="dialog">
        <textarea aria-label="Notes" />
        <button type="button">Save</button>
      </ModalDialog>,
    );

    const textarea = screen.getByRole("textbox", { name: "Notes" });
    const save = screen.getByRole("button", { name: "Save" });
    save.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(textarea).toHaveFocus();
  });
});
