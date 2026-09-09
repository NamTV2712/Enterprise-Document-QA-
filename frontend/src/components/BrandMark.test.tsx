import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { BrandMark } from "./BrandMark";

describe("BrandMark", () => {
  test("exposes the three semantic size hooks used by the shell", () => {
    const { container } = render(
      <>
        <BrandMark size="xs" />
        <BrandMark size="sm" />
        <BrandMark size="md" />
      </>,
    );

    expect(container.querySelectorAll(".brand-mark")).toHaveLength(3);
    expect(container.querySelector(".brand-mark--xs")).toBeInTheDocument();
    expect(container.querySelector(".brand-mark--sm")).toBeInTheDocument();
    expect(container.querySelector(".brand-mark--md")).toBeInTheDocument();
    expect(container.querySelectorAll("svg")).toHaveLength(3);
  });
});
