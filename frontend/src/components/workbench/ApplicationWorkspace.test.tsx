import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { CatalogWorkspaceTarget } from "../../types";
import { ApplicationWorkspace } from "./ApplicationWorkspace";
import { useWorkbenchContext } from "./WorkbenchContext";

function ControllerProbe() {
  const { controller } = useWorkbenchContext();
  return (
    <div
      data-testid="controller-probe"
      data-representation={controller.state.activeRepresentation}
      data-context-tab={controller.state.documentContextTab}
      data-find-query={controller.state.documentFindQuery}
    >
      <button
        type="button"
        onClick={() => {
          controller.setRepresentation("pdf");
          controller.setDocumentContextTab("notes");
          controller.setDocumentFindQuery("risk factors");
        }}
      >
        Change reader state
      </button>
    </div>
  );
}

const firstDocumentTarget: CatalogWorkspaceTarget = {
  kind: "catalog",
  documentId: "AAPL:fixture",
  returnView: "documents",
  returnFocusId: "aapl-row",
};

const secondDocumentTarget: CatalogWorkspaceTarget = {
  kind: "catalog",
  documentId: "MSFT:fixture",
  initialTab: "metadata",
  returnView: "documents",
  returnFocusId: "msft-row",
};

describe("ApplicationWorkspace", () => {
  test("keeps navigation/header/main/footer as separate shell regions", () => {
    render(
      <ApplicationWorkspace
        navigation={<aside aria-label="Test navigation" data-testid="navigation-slot" />}
        header={<header aria-label="Test header" data-testid="header-slot" />}
        footer={<footer data-testid="footer-slot">Composer</footer>}
        overlays={<div data-testid="overlay-slot">Overlay</div>}
      >
        <main aria-label="Test research">Route content</main>
      </ApplicationWorkspace>,
    );

    expect(screen.getByTestId("navigation-slot")).toHaveAttribute(
      "data-testid",
      "navigation-slot",
    );
    expect(screen.getByTestId("header-slot")).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Test research" })).toHaveTextContent("Route content");
    expect(screen.getByTestId("footer-slot")).toHaveTextContent("Composer");
    expect(screen.getByTestId("overlay-slot")).toHaveTextContent("Overlay");
    expect(screen.getByRole("region", { name: "Research" })).toBeInTheDocument();
    expect(screen.getByTestId("header-slot").closest("[data-workbench-app]")).not.toBeNull();
  });

  test("resets document-owned reader state before rendering a different target", () => {
    const renderWorkspace = (target: CatalogWorkspaceTarget) => (
      <ApplicationWorkspace
        navigation={<aside aria-label="Test navigation" />}
        header={<header aria-label="Test header" />}
        target={target}
      >
        <ControllerProbe />
      </ApplicationWorkspace>
    );
    const { rerender } = render(renderWorkspace(firstDocumentTarget));

    fireEvent.click(screen.getByRole("button", { name: "Change reader state" }));
    expect(screen.getByTestId("controller-probe")).toHaveAttribute("data-representation", "pdf");
    expect(screen.getByTestId("controller-probe")).toHaveAttribute("data-context-tab", "notes");
    expect(screen.getByTestId("controller-probe")).toHaveAttribute("data-find-query", "risk factors");

    rerender(renderWorkspace(secondDocumentTarget));
    expect(screen.getByTestId("controller-probe")).toHaveAttribute("data-representation", "structured");
    expect(screen.getByTestId("controller-probe")).toHaveAttribute("data-context-tab", "metadata");
    expect(screen.getByTestId("controller-probe")).toHaveAttribute("data-find-query", "");
  });
});
