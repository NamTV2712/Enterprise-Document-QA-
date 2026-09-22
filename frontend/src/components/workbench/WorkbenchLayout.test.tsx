import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { useWorkbenchController } from "../../hooks/useWorkbenchController";
import { useWorkbenchPreferences } from "../../hooks/useWorkbenchPreferences";
import { WorkbenchLayout } from "./WorkbenchLayout";

function Harness() {
  const controller = useWorkbenchController();
  const preferences = useWorkbenchPreferences();
  return (
    <WorkbenchLayout controller={controller} preferences={preferences}>
      <div data-testid="route-content">Existing route content</div>
    </WorkbenchLayout>
  );
}

describe("WorkbenchLayout", () => {
  test("mounts the presentation seams without taking ownership of route content", () => {
    render(<Harness />);

    expect(screen.getByTestId("route-content")).toHaveTextContent("Existing route content");
    const layout = screen.getByLabelText("Research workbench layout");
    expect(layout).toHaveAttribute("data-workbench-layout-mode", "four-pane");
    expect(layout).toHaveAttribute("data-workbench-measured", "false");
    expect(layout).toHaveAttribute("data-workbench-navigation-width", "0");
    expect(layout).toHaveStyle({
      "--workbench-sources-width": "332px",
      "--workbench-document-width": "400px",
    });
  });
});
