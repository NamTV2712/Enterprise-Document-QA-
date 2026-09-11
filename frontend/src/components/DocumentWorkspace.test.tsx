import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { LocaleProvider } from "../lib/i18n";
import { DocumentWorkspace } from "./DocumentWorkspace";

vi.mock("./StructuredDocumentReader", () => ({
  StructuredDocumentReader: ({ embedded }: { embedded?: boolean }) => <div data-testid="structured-reader">{embedded ? "embedded reader" : "reader"}</div>,
}));

describe("DocumentWorkspace", () => {
  afterEach(cleanup);

  test("keeps document, excerpt, and metadata as explicit synchronized views", () => {
    const onBack = vi.fn();
    render(
      <LocaleProvider>
        <DocumentWorkspace
          documentId="AAPL:fixture"
          indexedSource={{ citation: "AAPL 10-K · Risk Factors", document_id: "AAPL:fixture", text_preview: "Competition remains intense." }}
          indexedExcerpt={<p>Competition remains intense.</p>}
          metadata={<dl><div><dt>Document ID</dt><dd>AAPL:fixture</dd></div></dl>}
          onBack={onBack}
        />
      </LocaleProvider>,
    );

    expect(screen.getByRole("tab", { name: "Document" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("structured-reader")).toHaveTextContent("embedded reader");

    fireEvent.click(screen.getByRole("tab", { name: "Indexed excerpt" }));
    expect(screen.getByRole("tabpanel", { name: "Indexed excerpt" })).toHaveTextContent("Competition remains intense.");
    expect(screen.queryByTestId("structured-reader")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Metadata" }));
    expect(screen.getByRole("tabpanel", { name: "Document metadata" })).toHaveTextContent("AAPL:fixture");
    fireEvent.click(screen.getByRole("button", { name: "Close document workspace" }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
