import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

import { LocaleProvider, useLocale } from "./i18n";

function LocaleProbe() {
  const { locale, t } = useLocale();
  return <p>{locale}:{t("input.ask")}</p>;
}

afterEach(() => localStorage.clear());

describe("LocaleProvider", () => {
  test("adopts a valid cross-tab locale update without reintroducing answer-language state", () => {
    render(<LocaleProvider><LocaleProbe /></LocaleProvider>);
    expect(screen.getByText(/:Ask$/)).toBeInTheDocument();

    fireEvent(window, new StorageEvent("storage", { key: "sec_qa_locale", newValue: "vi" }));
    expect(screen.getByText("vi:Hỏi")).toBeInTheDocument();
    expect(localStorage.getItem("sec_qa_answer_language")).toBeNull();
  });
});
