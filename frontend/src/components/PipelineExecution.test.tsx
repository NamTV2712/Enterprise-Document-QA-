import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { PipelineExecution } from "./PipelineExecution";
import { LocaleProvider } from "../lib/i18n";
import type { ExecutionTrace, StageEvent } from "../types";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

function stage(overrides: Partial<StageEvent> = {}): StageEvent {
  return {
    version: 1,
    request_id: "request-1",
    sequence: 1,
    stage_id: "retrieval",
    status: "success",
    ...overrides,
  };
}

function renderPipeline(props: ComponentProps<typeof PipelineExecution>) {
  return render(
    <LocaleProvider>
      <PipelineExecution {...props} />
    </LocaleProvider>,
  );
}

describe("PipelineExecution", () => {
  test("labels reported counters and keeps server duration provenance visible", () => {
    renderPipeline({
      events: [
        stage({ stage_id: "query_preparation", sequence: 1, elapsed_ms: 4.2 }),
        stage({ stage_id: "retrieval", sequence: 2, elapsed_ms: 42.4, counters: { source_count: 2, candidate_count: 8 } }),
        stage({ stage_id: "cache_replay", sequence: 3, status: "skipped", metadata: { reason: "cache_hit" } }),
      ],
      trace: { elapsed_ms: 1234, stages: [] },
    });

    fireEvent.click(screen.getByText("Execution stages", { exact: true }));
    expect(screen.getByText("2 sources")).toBeInTheDocument();
    expect(screen.getByText("8 candidates")).toBeInTheDocument();
    expect(screen.getByText("Server · 42 ms")).toBeInTheDocument();
    expect(screen.getByText("Cache replay · skipped")).toBeInTheDocument();
    expect(screen.getByText("Server duration · 1.23s")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Execution stages" })).toHaveAttribute("aria-live", "polite");
  });

  test("uses a local elapsed-in-this-view timer only while a stage is running", () => {
    vi.useFakeTimers();
    vi.setSystemTime(1000);
    renderPipeline({
      events: [stage({ stage_id: "generation", status: "running" })],
      isStreaming: true,
    });

    act(() => {
      vi.advanceTimersByTime(250);
    });

    expect(screen.getByText("Elapsed in this view · 250 ms")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Execution stages" })).toHaveTextContent("Generation · running");
  });

  test("indents only children with a real same-request parent", () => {
    renderPipeline({
      events: [
        stage({ stage_id: "retrieval", sequence: 1 }),
        stage({ stage_id: "subquery_1_retrieval", sequence: 2, parent_stage_id: "retrieval" }),
        stage({ stage_id: "post_process", sequence: 3, parent_stage_id: "missing_parent" }),
      ],
    });

    expect(document.querySelector('[data-stage-id="subquery_1_retrieval"]')).toHaveAttribute("data-stage-depth", "1");
    expect(document.querySelector('[data-stage-id="post_process"]')).toHaveAttribute("data-stage-depth", "0");
    expect(screen.getByText("Unknown stage · post process")).toBeInTheDocument();
  });

  test("renders legacy trace-only timings as server measurements", () => {
    const trace: ExecutionTrace = {
      elapsed_ms: 987.6,
      stages: [
        { name: "cache_lookup", elapsed_ms: 12.4, status: "hit" },
        { name: "legacy_unknown", elapsed_ms: 3.2, status: "completed" },
      ],
    };
    renderPipeline({ trace });

    fireEvent.click(screen.getByText("Execution stages", { exact: true }));
    expect(screen.getByText("Server duration · 0.99s")).toBeInTheDocument();
    expect(screen.getByText("Server · 12 ms")).toBeInTheDocument();
    expect(screen.getByText("Unknown stage · legacy unknown")).toBeInTheDocument();
  });
});
