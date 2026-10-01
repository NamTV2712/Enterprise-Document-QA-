import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import type { WorkbenchController } from "../../hooks/useWorkbenchController";
import type { WorkbenchPreferencesController } from "../../hooks/useWorkbenchPreferences";
import { WorkbenchContextProvider } from "./WorkbenchContext";
import { DocumentPane } from "./DocumentPane";
import type { DocumentWorkspaceProps } from "../DocumentWorkspace";
import type { CatalogWorkspaceTarget } from "../../types";

vi.mock("../DocumentWorkspace", () => ({
  DocumentWorkspace: (props: DocumentWorkspaceProps) => (
    <div data-testid="document-workspace-adapter" data-representation={props.representation} data-context-tab={props.activeContextTab} data-show-legacy={props.showLegacyTabs ? "true" : "false"}>
      <input aria-label="Document find" value={props.findQuery ?? ""} onChange={(event) => props.onFindQueryChange?.(event.target.value)} />
      <button type="button" onClick={() => props.onRepresentationChange?.("normalized")}>Switch normalized</button>
      <button type="button" onClick={() => props.onContextTabChange?.("metadata")}>Switch metadata</button>
    </div>
  ),
}));

describe("DocumentPane", () => {
  afterEach(cleanup);

  test("provides a local document surface when no workbench context is present", () => {
    render(
      <DocumentPane
        documentId="AAPL:fixture"
        indexedSource={{ citation: "AAPL 10-K · Risk Factors", document_id: "AAPL:fixture", text_preview: "Risk text." }}
        onBack={vi.fn()}
      />,
    );

    expect(screen.getByRole("region", { name: "Document pane" })).toHaveAttribute("data-workbench-region", "document");
    expect(screen.getByTestId("document-workspace-adapter")).toHaveAttribute("data-representation", "structured");
    expect(screen.getByTestId("document-workspace-adapter")).toHaveAttribute("data-show-legacy", "false");
    fireEvent.click(screen.getByRole("button", { name: "Switch normalized" }));
    expect(screen.getByTestId("document-workspace-adapter")).toHaveAttribute("data-representation", "normalized");
  });

  test("keeps explicit excerpt deep links on the compatibility view", () => {
    render(
      <DocumentPane documentId="MSFT:fixture" initialTab="excerpt" onBack={vi.fn()} />,
    );

    expect(screen.getByTestId("document-workspace-adapter")).toHaveAttribute("data-show-legacy", "true");
  });

  test("coordinates representation, context, and find state through the workbench controller", () => {
    const controller = {
      state: {
        activeRepresentation: "structured",
        documentContextTab: "evidence",
        documentFindQuery: "",
      },
      setActivePane: vi.fn(),
      setRepresentation: vi.fn(),
      setDocumentContextTab: vi.fn(),
      setDocumentFindQuery: vi.fn(),
    } as unknown as WorkbenchController;
    const preferences = {} as WorkbenchPreferencesController;

    render(
      <WorkbenchContextProvider value={{ controller, preferences }}>
        <DocumentPane documentId="MSFT:fixture" onBack={vi.fn()} />
      </WorkbenchContextProvider>,
    );

    expect(controller.setActivePane).toHaveBeenCalledWith("document");
    expect(controller.setRepresentation).not.toHaveBeenCalled();
    expect(controller.setDocumentContextTab).toHaveBeenCalledWith("evidence");
    fireEvent.click(screen.getByRole("button", { name: "Switch normalized" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch metadata" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Document find" }), { target: { value: "risk factors" } });
    expect(controller.setRepresentation).toHaveBeenCalledWith("normalized");
    expect(controller.setDocumentContextTab).toHaveBeenCalledWith("metadata");
    expect(controller.setDocumentFindQuery).toHaveBeenCalledWith("risk factors");
  });

  test("does not clear target-owned reader state when the same document pane remounts", () => {
    const target: CatalogWorkspaceTarget = {
      kind: "catalog",
      documentId: "MSFT:fixture",
      returnView: "documents",
      returnFocusId: "document-row",
    };
    const controller = {
      state: {
        target,
        activeRepresentation: "normalized",
        documentContextTab: "metadata",
        documentFindQuery: "risk factors",
      },
      setActivePane: vi.fn(),
      setRepresentation: vi.fn(),
      setDocumentContextTab: vi.fn(),
      setDocumentFindQuery: vi.fn(),
      clearEvidenceBinding: vi.fn(),
    } as unknown as WorkbenchController;
    const preferences = {} as WorkbenchPreferencesController;
    const surface = (
      <WorkbenchContextProvider value={{ controller, preferences }}>
        <DocumentPane documentId="MSFT:fixture" onBack={vi.fn()} />
      </WorkbenchContextProvider>
    );

    const first = render(surface);
    expect(screen.getByTestId("document-workspace-adapter")).toHaveAttribute("data-representation", "normalized");
    expect(screen.getByTestId("document-workspace-adapter")).toHaveAttribute("data-context-tab", "metadata");
    expect(screen.getByRole("textbox", { name: "Document find" })).toHaveValue("risk factors");
    first.unmount();

    render(surface);
    expect(screen.getByTestId("document-workspace-adapter")).toHaveAttribute("data-representation", "normalized");
    expect(screen.getByTestId("document-workspace-adapter")).toHaveAttribute("data-context-tab", "metadata");
    expect(screen.getByRole("textbox", { name: "Document find" })).toHaveValue("risk factors");
    expect(controller.setDocumentContextTab).not.toHaveBeenCalled();
    expect(controller.setDocumentFindQuery).not.toHaveBeenCalled();
    expect(controller.clearEvidenceBinding).not.toHaveBeenCalled();
  });
});
