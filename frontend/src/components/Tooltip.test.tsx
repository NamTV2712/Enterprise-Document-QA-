import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { Tooltip } from "./Tooltip";

afterEach(() => cleanup());

describe("Tooltip", () => {
  test("renders outside overflow containers through a fixed portal", async () => {
    render(
      <div className="overflow-hidden">
        <Tooltip content="Viewport-aware help">
          <button type="button">Show help</button>
        </Tooltip>
      </div>,
    );

    fireEvent.mouseEnter(screen.getByRole("button", { name: "Show help" }));

    const tooltip = await screen.findByRole("tooltip", undefined, {
      timeout: 1000,
    });
    expect(tooltip.parentElement).toBe(document.body);
    expect(tooltip).toHaveClass("fixed");
  });

  test("keeps a focused tooltip available to assistive technology", async () => {
    render(
      <Tooltip content="Keyboard help">
        <button type="button">Focused help</button>
      </Tooltip>,
    );

    const trigger = screen.getByRole("button", { name: "Focused help" });
    fireEvent.focus(trigger);
    const tooltip = await screen.findByRole("tooltip");

    expect(trigger).toHaveAttribute("aria-describedby", tooltip.id);
    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});
