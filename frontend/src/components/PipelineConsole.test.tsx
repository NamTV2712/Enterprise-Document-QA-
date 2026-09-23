import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { PipelineConsole } from "./PipelineConsole";
import { LocaleProvider } from "../lib/i18n";
import { LocalWorkspaceSessionProvider } from "../lib/localWorkspaceSession";
import { pipelineApi, PipelineApiError } from "../lib/pipelineApi";
import type { PipelineDefinition, PipelineRun, PipelineRunEvent } from "../types";

const stageIds = [
  "download_filings",
  "chunk_filings",
  "add_table_chunks",
  "embed_chunks",
  "index_chunks",
] as const;

function definition(): PipelineDefinition {
  return {
    pipeline_id: "sec_10k_ingestion",
    name: "SEC 10-K ingestion",
    input_kind: "ticker",
    registered_input_ids: ["AAPL", "MSFT"],
    staging_profiles: ["isolated"],
    stages: stageIds.map((stage_id, index) => ({ stage_id, order: index + 1, description: `Registered ${stage_id}` })),
    capabilities: {
      can_stage: true,
      can_cancel: true,
      event_transport: "sse",
      executes_during_staging: false,
      automatically_promotes_to_serving: false,
    },
  };
}

function run(id = "run-A", overrides: Partial<PipelineRun> = {}): PipelineRun {
  return {
    id,
    pipeline_id: "sec_10k_ingestion",
    state: "queued",
    revision: 1,
    configuration_fingerprint: "a".repeat(64),
    input_ids: ["AAPL"],
    staging_profile: "isolated",
    created_at: "2026-09-23T10:00:00Z",
    updated_at: "2026-09-23T10:00:00Z",
    started_at: null,
    finished_at: null,
    cancellation_requested_at: null,
    progress: { stage: null, current: null, total: null },
    steps: stageIds.map((stage_id, index) => ({
      step_id: `${id}-step-${index + 1}`,
      stage_id,
      state: "pending",
      revision: 1,
      started_at: null,
      finished_at: null,
    })),
    artifact_references: [],
    failure: null,
    ...overrides,
  };
}

function event(id: string, sequence: number): PipelineRunEvent {
  return {
    run_id: id,
    event_id: `${id}-event-${sequence}`,
    sequence,
    event_type: "created",
    state: "queued",
    reason_code: null,
    progress: { stage: null, current: null, total: null },
    occurred_at: "2026-09-23T10:00:00Z",
  };
}

function pendingEvents(): Promise<PipelineRunEvent[]> {
  return new Promise(() => {});
}

function Harness({ initialRunId = null }: { initialRunId?: string | null }) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(initialRunId);
  return (
    <LocaleProvider>
      <LocalWorkspaceSessionProvider>
        <button type="button" onClick={() => setSelectedRunId("run-A")}>Route A</button>
        <button type="button" onClick={() => setSelectedRunId("run-B")}>Route B</button>
        <PipelineConsole
          selectedRunId={selectedRunId}
          onSelectRun={setSelectedRunId}
          onClearSelectedRun={() => setSelectedRunId(null)}
        />
      </LocalWorkspaceSessionProvider>
    </LocaleProvider>
  );
}

async function connect() {
  fireEvent.click(screen.getAllByRole("button", { name: "Connect" })[0]);
  const dialog = screen.getByRole("dialog", { name: "Connect local workspace" });
  fireEvent.change(within(dialog).getByLabelText("Local workspace token"), { target: { value: "fixture-token" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Verify and connect" }));
  await waitFor(() => expect(screen.getByText("Connected · local")).toBeInTheDocument());
}

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(pipelineApi, "getDefinition").mockResolvedValue(definition());
  vi.spyOn(pipelineApi, "verifyLocalWorkspaceToken").mockResolvedValue({
    deployment_mode: "local",
    capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: true },
  });
  vi.spyOn(pipelineApi, "listRuns").mockResolvedValue({ items: [run()], total: 1, page: 1, page_size: 25 });
  vi.spyOn(pipelineApi, "getRun").mockResolvedValue(run());
  vi.spyOn(pipelineApi, "getRunEvents").mockImplementation(pendingEvents);
  vi.spyOn(pipelineApi, "stageRun").mockResolvedValue(run());
  vi.spyOn(pipelineApi, "cancelRun").mockResolvedValue(run("run-A", { state: "cancelled", revision: 2 }));
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("Pipeline workspace", () => {
  test("shows the public definition and a truthful private access gate", async () => {
    render(<Harness />);

    await waitFor(() => expect(screen.getByTestId("pipeline-stage-add_table_chunks")).toBeInTheDocument());
    expect(screen.getAllByTestId(/^pipeline-stage-/)).toHaveLength(5);
    expect(screen.getByRole("heading", { name: "Connect to view local runs" })).toBeInTheDocument();
    expect(pipelineApi.getDefinition).toHaveBeenCalledTimes(1);
    expect(pipelineApi.listRuns).not.toHaveBeenCalled();
    expect(pipelineApi.stageRun).not.toHaveBeenCalled();
  });

  test("renders a canonical selected queued run with five pending durable steps and unknown progress", async () => {
    render(<Harness initialRunId="run-A" />);
    await connect();

    const detail = screen.getByTestId("pipeline-run-detail");
    await waitFor(() => expect(detail.querySelector(".pipeline-detail-revision")).toHaveTextContent("r1"));
    expect(within(detail).getByText("Not reported")).toBeInTheDocument();
    expect(within(detail).getAllByText("Pending")).toHaveLength(5);
    expect(within(detail).getByText("No staged artifacts have been reported.")).toBeInTheDocument();
    expect(pipelineApi.getRun).toHaveBeenCalledWith("fixture-token", "run-A", expect.any(AbortSignal));
    expect(pipelineApi.stageRun).not.toHaveBeenCalled();
  });

  test("stages exactly once on double submit and selects the returned server job ID", async () => {
    vi.mocked(pipelineApi.listRuns).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 });
    let finish: ((result: PipelineRun) => void) | undefined;
    vi.mocked(pipelineApi.stageRun).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    render(<Harness />);
    await connect();

    fireEvent.click(screen.getByRole("button", { name: "Stage run" }));
    const dialog = screen.getByRole("dialog", { name: "Stage an isolated run" });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "AAPL" }));
    const submit = within(dialog).getByRole("button", { name: "Create staged run" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    expect(pipelineApi.stageRun).toHaveBeenCalledTimes(1);
    expect(pipelineApi.stageRun).toHaveBeenCalledWith("fixture-token", { input_ids: ["AAPL"], staging_profile: "isolated" }, expect.any(AbortSignal));

    await act(async () => { finish?.(run("server-issued-id")); });
    await waitFor(() => expect(screen.getByTestId("pipeline-run-detail")).toHaveTextContent("server-issued-id"));
    expect(screen.getByText("Staged record created. No ingestion work has run.")).toBeInTheDocument();
  });

  test("keeps cancellation requested distinct from acknowledged cancellation", async () => {
    const running = run("run-A", { state: "running", revision: 3 });
    vi.mocked(pipelineApi.getRun).mockResolvedValue(running);
    vi.mocked(pipelineApi.cancelRun).mockResolvedValue(run("run-A", { state: "cancelling", revision: 4 }));
    render(<Harness initialRunId="run-A" />);
    await connect();
    const detail = screen.getByTestId("pipeline-run-detail");
    await waitFor(() => expect(within(detail).getByRole("button", { name: "Request cancellation" })).toBeInTheDocument());

    fireEvent.click(within(detail).getByRole("button", { name: "Request cancellation" }));

    await waitFor(() => expect(within(detail).getByText("Cancellation requested. The run remains cancelling until the backend confirms it.")).toBeInTheDocument());
    expect(within(detail).getByText("Cancelling")).toBeInTheDocument();
    expect(within(detail).queryByRole("button", { name: "Request cancellation" })).not.toBeInTheDocument();
    expect(pipelineApi.cancelRun).toHaveBeenCalledWith("fixture-token", "run-A", 3, expect.any(AbortSignal));
  });

  test("applies an ordered SSE batch and resumes from its last sequence after finite close", async () => {
    vi.mocked(pipelineApi.getRunEvents).mockResolvedValueOnce([event("run-A", 7)]).mockImplementation(pendingEvents);
    render(<Harness initialRunId="run-A" />);
    await connect();

    const detail = screen.getByTestId("pipeline-run-detail");
    await waitFor(() => expect(within(detail).getByText("#7")).toBeInTheDocument());
    await waitFor(() => expect(pipelineApi.getRunEvents).toHaveBeenCalledTimes(2), { timeout: 3_500 });
    expect(vi.mocked(pipelineApi.getRunEvents).mock.calls[1]?.[2]).toBe(7);
    expect(detail).not.toHaveTextContent("Run details are retained; event updates will retry.");
  });

  test("keeps backend validation refusal visible without inventing a run", async () => {
    vi.mocked(pipelineApi.listRuns).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 });
    vi.mocked(pipelineApi.stageRun).mockRejectedValue(new PipelineApiError(422));
    render(<Harness />);
    await connect();
    fireEvent.click(screen.getByRole("button", { name: "Stage run" }));
    const dialog = screen.getByRole("dialog", { name: "Stage an isolated run" });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "AAPL" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Create staged run" }));

    await waitFor(() => expect(within(dialog).getByRole("alert")).toHaveTextContent("The staging request was not accepted"));
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "No staged runs yet" })).toBeInTheDocument();
    expect(pipelineApi.stageRun).toHaveBeenCalledTimes(1);
  });

  test("surfaces a revision conflict while refreshing server truth", async () => {
    vi.mocked(pipelineApi.getRun).mockResolvedValueOnce(run("run-A", { revision: 3 })).mockResolvedValue(run("run-A", { revision: 4 }));
    vi.mocked(pipelineApi.cancelRun).mockRejectedValue(new PipelineApiError(409));
    render(<Harness initialRunId="run-A" />);
    await connect();
    const detail = screen.getByTestId("pipeline-run-detail");
    await waitFor(() => expect(within(detail).getByRole("button", { name: "Request cancellation" })).toBeInTheDocument());

    fireEvent.click(within(detail).getByRole("button", { name: "Request cancellation" }));

    await waitFor(() => expect(detail.querySelector(".pipeline-detail-revision")).toHaveTextContent("r4"));
    expect(within(detail).getByRole("alert")).toHaveTextContent("This run changed. Refresh it before trying again.");
    expect(pipelineApi.cancelRun).toHaveBeenCalledTimes(1);
  });

  test("rejects late A#1 details after A→B→A#2 selection", async () => {
    let finishFirstA: ((result: PipelineRun) => void) | undefined;
    vi.mocked(pipelineApi.getRun).mockImplementationOnce(() => new Promise((resolve) => { finishFirstA = resolve; }))
      .mockResolvedValueOnce(run("run-B", { revision: 2 }))
      .mockResolvedValue(run("run-A", { revision: 3 }));
    render(<Harness initialRunId="run-A" />);
    await connect();
    await waitFor(() => expect(pipelineApi.getRun).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Route B" }));
    await waitFor(() => expect(screen.getByTestId("pipeline-run-detail")).toHaveTextContent("run-B"));
    fireEvent.click(screen.getByRole("button", { name: "Route A" }));
    await waitFor(() => expect(screen.getByTestId("pipeline-run-detail").querySelector(".pipeline-detail-revision")).toHaveTextContent("r3"));
    await act(async () => { finishFirstA?.(run("run-A", { revision: 1 })); });

    expect(screen.getByTestId("pipeline-run-detail").querySelector(".pipeline-detail-revision")).toHaveTextContent("r3");
  });

  test("ignores a stale A#1 event batch and subscribes once per selected lifetime", async () => {
    let finishOldA: ((events: PipelineRunEvent[]) => void) | undefined;
    vi.mocked(pipelineApi.getRun).mockImplementation(async (_token, id) => run(id));
    vi.mocked(pipelineApi.getRunEvents).mockImplementationOnce(() => new Promise((resolve) => { finishOldA = resolve; }))
      .mockImplementation(pendingEvents);
    render(<Harness initialRunId="run-A" />);
    await connect();
    await waitFor(() => expect(pipelineApi.getRunEvents).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Route B" }));
    await waitFor(() => expect(pipelineApi.getRunEvents).toHaveBeenCalledTimes(2));
    fireEvent.click(screen.getByRole("button", { name: "Route A" }));
    await waitFor(() => expect(pipelineApi.getRunEvents).toHaveBeenCalledTimes(3));
    await act(async () => { finishOldA?.([event("run-A", 9)]); });

    expect(screen.getByTestId("pipeline-run-detail")).not.toHaveTextContent("#9");
    expect(vi.mocked(pipelineApi.getRunEvents).mock.calls.map((call) => call[1])).toEqual(["run-A", "run-B", "run-A"]);
  });

  test("reports unavailable public definition without calling private routes", async () => {
    vi.mocked(pipelineApi.getDefinition).mockRejectedValue(new PipelineApiError(404));
    render(<Harness />);

    await waitFor(() => expect(screen.getByText("The pipeline definition is unavailable from this API.")).toBeInTheDocument());
    expect(pipelineApi.listRuns).not.toHaveBeenCalled();
    expect(pipelineApi.stageRun).not.toHaveBeenCalled();
  });
});
