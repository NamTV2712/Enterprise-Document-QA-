import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import {
  Badge,
  ChartCard,
  DataTable,
  DetailRail,
  Drawer,
  EmptyState,
  EvidenceCard,
  FilterBar,
  IconButton,
  LoadingSkeleton,
  MetricCard,
  Modal,
  PageHeader,
  Pagination,
  Panel,
  ScoreBadge,
  SearchField,
  Select,
  SplitPane,
  StatusBadge,
  Tabs,
} from ".";

afterEach(() => cleanup());

describe("UI foundation", () => {
  test("exports the complete semantic primitive vocabulary", () => {
    render(
      <main>
        <PageHeader title="Documents" description="Review filings" actions={<button type="button">Import</button>} />
        <Panel aria-label="Summary panel"><MetricCard label="Filings" value="42" detail="Current scope" /></Panel>
        <SearchField id="filing-search" label="Search filings" value="annual" readOnly />
        <FilterBar label="Document filters"><Select label="Filing type" value="10-k" options={[{ value: "10-k", label: "10-K" }]} onValueChange={() => {}} /></FilterBar>
        <Tabs label="Document views" value="overview" options={[{ id: "overview", label: "Overview", panelId: "overview-panel" }]} onValueChange={() => {}} />
        <Badge>Draft</Badge>
        <StatusBadge status="success">Ready</StatusBadge>
        <IconButton label="Open details"><span aria-hidden="true">+</span></IconButton>
        <EmptyState title="No filings" description="Change the active filters." />
        <LoadingSkeleton label="Loading filings" lines={2} />
        <ScoreBadge label="Rerank" score={0.91} />
        <Pagination page={2} pageCount={4} onPageChange={() => {}} />
        <ChartCard title="Coverage" tableAlternative={<table aria-label="Coverage data"><tbody><tr><td>100%</td></tr></tbody></table>}><svg role="img" aria-label="Coverage chart" /></ChartCard>
        <DataTable caption="Filing inventory"><tbody><tr><td>Apple 10-K</td></tr></tbody></DataTable>
        <DetailRail title="Filing details">Metadata</DetailRail>
        <SplitPane primary="Results" secondary="Facets" primaryLabel="Search results" secondaryLabel="Search facets" />
        <EvidenceCard title="Revenue" excerpt="Net sales increased." metadata="AAPL · 10-K" />
      </main>,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Documents" })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search filings" })).toHaveAttribute("id", "filing-search");
    expect(screen.getByRole("region", { name: "Filing inventory" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("table", { name: "Filing inventory" })).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Loading filings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open details" })).toHaveAttribute("title", "Open details");
    expect(screen.getByText("Ready").parentElement).toHaveClass("ui-status-badge");
    expect(screen.getByLabelText("Rerank: 0.91")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Coverage chart" })).toBeInTheDocument();
  });

  test("uses keyboard and explicit selection semantics for tabs", () => {
    const onValueChange = vi.fn();
    render(<Tabs label="Evidence views" value="answer" options={[{ id: "answer", label: "Answer" }, { id: "sources", label: "Sources" }, { id: "disabled", label: "Disabled", disabled: true }]} onValueChange={onValueChange} />);

    const answer = screen.getByRole("tab", { name: "Answer" });
    expect(answer).toHaveAttribute("aria-selected", "true");
    expect(answer.querySelector("svg")).toBeInTheDocument();
    fireEvent.keyDown(answer, { key: "ArrowRight" });
    expect(onValueChange).toHaveBeenCalledWith("sources");
  });

  test("keeps search clearing and pagination controlled by callers", () => {
    const onClear = vi.fn();
    const onPageChange = vi.fn();
    render(<><SearchField label="Search evidence" value="revenue" readOnly onClear={onClear} /><Pagination page={3} pageCount={5} onPageChange={onPageChange} /></>);

    fireEvent.click(screen.getByRole("button", { name: "Clear Search evidence" }));
    fireEvent.click(screen.getByRole("button", { name: "Previous page" }));
    fireEvent.click(screen.getByRole("button", { name: "5" }));
    expect(onClear).toHaveBeenCalledTimes(1);
    expect(onPageChange).toHaveBeenNthCalledWith(1, 2);
    expect(onPageChange).toHaveBeenNthCalledWith(2, 5);
  });

  test("communicates evidence selection without relying on color", () => {
    const onSelect = vi.fn();
    render(<EvidenceCard title="Selected source" excerpt="Bound excerpt" selected onSelect={onSelect} />);

    const card = screen.getByRole("button", { name: /Selected source/ });
    expect(card).toHaveAttribute("aria-pressed", "true");
    expect(card.querySelector("svg")).toBeInTheDocument();
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  test("builds modal and drawer shells on the proven focus boundary", () => {
    const closeModal = vi.fn();
    const closeDrawer = vi.fn();
    const { rerender } = render(<Modal open onClose={closeModal} title="Save collection" description="Choose a name."><input aria-label="Collection name" /></Modal>);

    expect(screen.getByRole("dialog", { name: "Save collection" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(closeModal).toHaveBeenCalledTimes(1);

    rerender(<Drawer open onClose={closeDrawer} title="Filters" side="right">Filter controls</Drawer>);
    expect(screen.getByRole("dialog", { name: "Filters" })).toHaveClass("ui-overlay__surface--drawer", "ui-overlay__surface--right");
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(closeDrawer).toHaveBeenCalledTimes(1);
  });
});
