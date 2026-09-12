import React from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { LocaleProvider, normalizeLocaleSearch, useLocale } from "./i18n";

function LocaleProbe() {
  const { locale, setLocale } = useLocale();
  return React.createElement(
    React.Fragment,
    null,
    React.createElement("output", null, locale),
    React.createElement("button", { type: "button", onClick: () => setLocale("en") }, "English"),
  );
}

afterEach(() => localStorage.clear());

describe("locale utilities", () => {
  test("normalizes Vietnamese accents and đ for literal search", () => {
    expect(normalizeLocaleSearch("Đám mây và Tỷ lệ")).toBe("dam may va ty le");
  });

  test("migrates a legacy answer-only language into the single locale preference", () => {
    localStorage.setItem("sec_qa_answer_language", "vi");

    render(React.createElement(LocaleProvider, null, React.createElement(LocaleProbe)));

    expect(screen.getByText("vi")).toBeInTheDocument();
    screen.getByRole("button", { name: "English" }).click();
    expect(localStorage.getItem("sec_qa_locale")).toBe("en");
    expect(localStorage.getItem("sec_qa_answer_language")).toBeNull();
  });
});
