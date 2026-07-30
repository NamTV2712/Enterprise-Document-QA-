import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { Tooltip } from "./Tooltip";

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
});
