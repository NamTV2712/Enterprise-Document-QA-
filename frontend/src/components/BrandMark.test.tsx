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
        <BrandMark size="lg" />
      </>,
    );

    expect(container.querySelectorAll(".brand-mark")).toHaveLength(4);
    expect(container.querySelector(".brand-mark--xs")).toBeInTheDocument();
    expect(container.querySelector(".brand-mark--sm")).toBeInTheDocument();
    expect(container.querySelector(".brand-mark--md")).toBeInTheDocument();
    expect(container.querySelector(".brand-mark--lg")).toBeInTheDocument();
    expect(container.querySelectorAll("svg")).toHaveLength(4);
  });

  test("uses a static decorative filing/search silhouette without a glow layer", () => {
    const { container } = render(<BrandMark size="xs" />);
    const mark = container.querySelector<HTMLElement>(".brand-mark");
    const svg = container.querySelector<SVGElement>("svg");

    expect(mark).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelector(".brand-mark__glow")).not.toBeInTheDocument();
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).not.toHaveAttribute("filter");
    expect(svg?.querySelector("animate, animateTransform, filter")).not.toBeInTheDocument();
    expect(svg?.querySelectorAll('[stroke="currentColor"]')).toHaveLength(4);
  });
});
