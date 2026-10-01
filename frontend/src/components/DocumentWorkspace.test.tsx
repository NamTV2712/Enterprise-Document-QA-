import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { LocaleProvider } from "../lib/i18n";
import { DocumentWorkspace } from "./DocumentWorkspace";

vi.mock("./StructuredDocumentReader", () => ({
  StructuredDocumentReader: ({ embedded }: { embedded?: boolean }) => <div data-testid="structured-reader">{embedded ? "embedded reader" : "reader"}</div>,
}));

vi.mock("./OriginalDocumentReader", () => ({
  OriginalDocumentReader: () => <div data-testid="normalized-reader">normalized reader</div>,
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

  test("does not expose answer-inspector chrome for a direct catalog entry", () => {
    const props = {
      documentId: "AAPL:fixture",
      indexedSource: { citation: "AAPL 10-K", document_id: "AAPL:fixture", text_preview: "Company background." },
      indexedExcerpt: <p>Company background.</p>,
      metadata: <dl><div><dt>Document ID</dt><dd>AAPL:fixture</dd></div></dl>,
      onBack: vi.fn(),
      origin: "catalog" as const,
    };
    render(<LocaleProvider><DocumentWorkspace {...props} /></LocaleProvider>);

    expect(screen.queryByRole("button", { name: "Back to inspector" })).not.toBeInTheDocument();
    expect(screen.queryByText("Answer origin")).not.toBeInTheDocument();
  });

  test("adapts the existing readers into representation and context controls", () => {
    render(
      <LocaleProvider>
        <DocumentWorkspace
          documentId="AAPL:fixture"
          indexedSource={{ citation: "AAPL 10-K · Risk Factors", document_id: "AAPL:fixture", section: "Risk Factors", text_preview: "Risk text." }}
          indexedExcerpt={<p>Risk text.</p>}
          metadata={<dl><div><dt>Accession</dt><dd>0000320193</dd></div></dl>}
          notes={<p>Existing note</p>}
          onBack={vi.fn()}
          showLegacyTabs={false}
          showContextTabs
        />
      </LocaleProvider>,
    );

    expect(screen.getByRole("tab", { name: "Evidence" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Notes" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Normalized text" }));
    expect(screen.getByTestId("normalized-reader")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Normalized text" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("tab", { name: "Metadata" }));
    expect(screen.getByRole("tabpanel", { name: "Metadata" })).toHaveTextContent("0000320193");
  });

  test("collapse and expand while a reader load is pending keeps the reader mounted", () => {
    render(
      <LocaleProvider>
        <DocumentWorkspace
          documentId="AAPL:fixture"
          indexedSource={{ citation: "AAPL source", document_id: "AAPL:fixture", text_preview: "Pending reader source" }}
          onBack={vi.fn()}
          showContextTabs
        />
      </LocaleProvider>,
    );

    const reader = screen.getByTestId("structured-reader");
    fireEvent.click(screen.getByRole("button", { name: "Collapse document context" }));
    fireEvent.click(screen.getByRole("button", { name: "Expand document context" }));
    expect(screen.getByTestId("structured-reader")).toBe(reader);
  });
});
