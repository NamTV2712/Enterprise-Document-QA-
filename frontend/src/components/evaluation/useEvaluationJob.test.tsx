import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { evaluationApi, EvaluationApiError } from "../../lib/evaluationApi";
import { LocalWorkspaceSessionProvider, useLocalWorkspaceSession } from "../../lib/localWorkspaceSession";
import { pipelineApi } from "../../lib/pipelineApi";
import { evaluationJob, jobResults, nativeMetricIds } from "../../test/evaluationFixtures";
import type { EvaluationJob, EvaluationJobEvent, SafeJobResults } from "../../lib/evaluationTypes";
import { useEvaluationJob } from "./useEvaluationJob";
import { useEvaluationCreation } from "./useEvaluationCreation";

function deferred<T>() {
  let resolve!: (value: T) => void; let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function event(id: string, sequence: number): EvaluationJobEvent {
  return { event_id: `event-${sequence}`, job_id: id, sequence, event_type: "progress", state: "running", reason_code: null, progress: { stage: "execute_cases", current: 0, total: 2 }, occurred_at: "2026-09-26T00:00:00Z" };
}
function Harness({ initial = "job-a", interval = 100000 }: { initial?: string; interval?: number }) {
  const session = useLocalWorkspaceSession();
  const [selected, setSelected] = useState(initial);
  const read = useEvaluationJob(selected, 1, evaluationApi, interval);
  const create = useEvaluationCreation((job) => setSelected(job.id));
  return <>
    <button onClick={() => { void session.connect("synthetic-token"); }}>Connect</button>
    <button onClick={session.disconnect}>Disconnect</button>
    <button onClick={() => setSelected("job-a")}>A</button><button onClick={() => setSelected("job-b")}>B</button>
    <button onClick={() => { void read.cancel(); }}>Cancel</button><button onClick={read.reload}>Reload</button>
    <button onClick={() => { void create.submit({ artifact_id: "synthetic-phase1", engine: "native", metrics: nativeMetricIds, mode: "provider_backed", budget: 6 }); }}>Create</button>
    <output data-testid="view">{JSON.stringify({ job: read.job, results: read.results, events: read.events, loading: read.loading, error: read.errorStatus, eventError: read.eventErrorStatus, cancelError: read.cancelErrorStatus, cancelling: read.cancelling, createBusy: create.busy, createError: create.errorStatus })}</output>
  </>;
}
const view = () => JSON.parse(screen.getByTestId("view").textContent ?? "{}");
async function start(props: Parameters<typeof Harness>[0] = {}) {
  render(<LocalWorkspaceSessionProvider><Harness {...props} /></LocalWorkspaceSessionProvider>);
  fireEvent.click(screen.getByText("Connect"));
  await waitFor(() => expect(view().job?.id).toBe(props.initial ?? "job-a"));
}
beforeEach(() => {
  vi.spyOn(pipelineApi, "verifyLocalWorkspaceToken").mockResolvedValue({ deployment_mode: "local", capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: true } });
  vi.spyOn(evaluationApi, "getJob").mockImplementation(async (_token, id) => evaluationJob(id));
  vi.spyOn(evaluationApi, "getJobResults").mockImplementation(async (_token, id) => jobResults(id));
  vi.spyOn(evaluationApi, "getJobEvents").mockResolvedValue([]);
  vi.spyOn(evaluationApi, "cancelJob").mockResolvedValue(evaluationJob("job-a", { revision: 2, state: "cancelling" }));
  vi.spyOn(evaluationApi, "createJob").mockResolvedValue(evaluationJob("canonical-created"));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("selected evaluation job ownership", () => {
  test("does not issue private reads before connection", () => {
    render(<LocalWorkspaceSessionProvider><Harness /></LocalWorkspaceSessionProvider>);
    expect(evaluationApi.getJob).not.toHaveBeenCalled();
    expect(view().job).toBeNull();
    expect(view().loading).toBe(false);
  });
  test("keeps canonical queued state, unknown progress, two backend steps and empty results", async () => {
    await start();
    await waitFor(() => expect(view().loading).toBe(false));
    expect(view().job.state).toBe("queued");
    expect(view().job.progress.current).toBeNull();
    expect(view().job.steps.map(({ name }: { name: string }) => name)).toEqual(["execute_cases", "aggregate_report"]);
    expect(view().job.frozen.budget_unit).toBe("provider_attempt_slot");
    expect(view().results.total).toBe(0);
    expect(view().job.publication_status).toBe("not_published");
  });
  test("A#1-B-A#2 rejects late old detail/error/loading writes", async () => {
    const first = deferred<EvaluationJob>(); let a = 0;
    vi.mocked(evaluationApi.getJob).mockImplementation(async (_token, id) => id === "job-a" && ++a === 1 ? first.promise : evaluationJob(id, { revision: 3 }));
    render(<LocalWorkspaceSessionProvider><Harness /></LocalWorkspaceSessionProvider>);
    fireEvent.click(screen.getByText("Connect"));
    await waitFor(() => expect(evaluationApi.getJob).toHaveBeenCalledTimes(1));
    const oldSignal = vi.mocked(evaluationApi.getJob).mock.calls[0][2];
    fireEvent.click(screen.getByText("B")); await waitFor(() => expect(view().job?.id).toBe("job-b"));
    fireEvent.click(screen.getByText("A")); await waitFor(() => expect(view().job?.revision).toBe(3));
    await act(async () => first.reject(new EvaluationApiError(503)));
    expect(oldSignal?.aborted).toBe(true);
    expect(view().job.id).toBe("job-a"); expect(view().job.revision).toBe(3); expect(view().error).toBeNull();
  });
  test("A#1-B-A#2 rejects late old results and events", async () => {
    const oldResult = deferred<SafeJobResults>(); let reads = 0;
    vi.mocked(evaluationApi.getJobResults).mockImplementation(async (_token, id) => id === "job-a" && ++reads === 1 ? oldResult.promise : jobResults(id));
    await start();
    fireEvent.click(screen.getByText("B")); await waitFor(() => expect(view().results?.job_id).toBe("job-b"));
    fireEvent.click(screen.getByText("A")); await waitFor(() => expect(view().results?.job_id).toBe("job-a"));
    await act(async () => oldResult.resolve({ ...jobResults(), total: 999 }));
    expect(view().results.total).toBe(0);
    const oldEvents = deferred<EvaluationJobEvent[]>();
    vi.mocked(evaluationApi.getJobEvents).mockReturnValueOnce(oldEvents.promise);
    fireEvent.click(screen.getByText("Reload")); await waitFor(() => expect(evaluationApi.getJobEvents).toHaveBeenCalledTimes(3));
    fireEvent.click(screen.getByText("B")); await waitFor(() => expect(view().job?.id).toBe("job-b"));
    fireEvent.click(screen.getByText("A")); await waitFor(() => expect(view().results?.job_id).toBe("job-a"));
    await act(async () => oldEvents.resolve([event("job-a", 99)]));
    expect(view().events).toEqual([]);
  });
  test("disconnect clears private state and invalidates delayed reads", async () => {
    const pending = deferred<EvaluationJobEvent[]>();
    vi.mocked(evaluationApi.getJobEvents).mockReturnValue(pending.promise);
    await start();
    fireEvent.click(screen.getByText("Disconnect"));
    await act(async () => pending.resolve([event("job-a", 1)]));
    expect(view().job).toBeNull(); expect(view().results).toBeNull(); expect(view().events).toEqual([]);
  });
  test("finite close and event network failure do not imply failed/succeeded", async () => {
    vi.mocked(evaluationApi.getJobEvents).mockRejectedValue(new EvaluationApiError(0));
    await start(); await waitFor(() => expect(view().eventError).toBe(0));
    expect(view().job.state).toBe("queued"); expect(view().results.total).toBe(0);
  });
  test("event replay resumes from the last sequence and does not duplicate rows", async () => {
    vi.mocked(evaluationApi.getJobEvents).mockResolvedValueOnce([event("job-a", 1)]).mockResolvedValue([event("job-a", 1), event("job-a", 2)]);
    await start({ interval: 20 });
    await waitFor(() => expect(view().events).toHaveLength(2));
    expect(view().events.map(({ sequence }: { sequence: number }) => sequence)).toEqual([1, 2]);
    expect(vi.mocked(evaluationApi.getJobEvents).mock.calls[1][2]).toBe(1);
  });
  test.each(["cancelled", "succeeded", "failed", "interrupted"] as const)("terminal %s retains completed results and stops polling", async (state) => {
    vi.mocked(evaluationApi.getJob).mockResolvedValue(evaluationJob("job-a", { state, failure: state === "failed" ? { code: "budget_exhausted", message: "Budget exhausted" } : null }));
    vi.mocked(evaluationApi.getJobResults).mockResolvedValue({ ...jobResults(), total: 1 });
    await start({ interval: 5 }); await waitFor(() => expect(view().loading).toBe(false));
    const calls = vi.mocked(evaluationApi.getJob).mock.calls.length;
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 25)); });
    expect(evaluationApi.getJob).toHaveBeenCalledTimes(calls);
    expect(view().results.total).toBe(1); expect(view().job.state).toBe(state);
  });
});
describe("revision-bound cancellation", () => {
  test("blocks duplicate cancellation and preserves requested/cancelling vs cancelled", async () => {
    const pending = deferred<EvaluationJob>(); vi.mocked(evaluationApi.cancelJob).mockReturnValue(pending.promise);
    await start();
    fireEvent.click(screen.getByText("Cancel")); fireEvent.click(screen.getByText("Cancel"));
    expect(evaluationApi.cancelJob).toHaveBeenCalledTimes(1);
    expect(vi.mocked(evaluationApi.cancelJob).mock.calls[0].slice(0, 3)).toEqual(["synthetic-token", "job-a", 1]);
    expect(view().job.state).toBe("queued"); expect(view().cancelling).toBe(true);
    await act(async () => pending.resolve(evaluationJob("job-a", { revision: 2, state: "cancelling" })));
    expect(view().job.state).toBe("cancelling"); expect(view().results).not.toBeNull();
  });
  test("409 remains visible while a non-forcing read reconciles revision", async () => {
    vi.mocked(evaluationApi.cancelJob).mockRejectedValue(new EvaluationApiError(409));
    await start();
    vi.mocked(evaluationApi.getJob).mockResolvedValue(evaluationJob("job-a", { revision: 4, state: "running" }));
    fireEvent.click(screen.getByText("Cancel"));
    await waitFor(() => expect(view().job?.revision).toBe(4));
    expect(view().cancelError).toBe(409); expect(evaluationApi.cancelJob).toHaveBeenCalledTimes(1);
  });
  test("old cancel completion cannot overwrite A#2 after A-B-A", async () => {
    const pending = deferred<EvaluationJob>(); vi.mocked(evaluationApi.cancelJob).mockReturnValue(pending.promise);
    await start(); fireEvent.click(screen.getByText("Cancel"));
    fireEvent.click(screen.getByText("B")); await waitFor(() => expect(view().job?.id).toBe("job-b"));
    fireEvent.click(screen.getByText("A")); await waitFor(() => expect(view().job?.id).toBe("job-a"));
    await act(async () => pending.resolve(evaluationJob("job-a", { revision: 99, state: "cancelled" })));
    expect(view().job.state).toBe("queued"); expect(view().job.revision).toBe(1); expect(view().cancelling).toBe(false);
  });
});
describe("creation lifetime and logical idempotency", () => {
  test("one submit attempt uses one POST and the returned canonical queued ID", async () => {
    const pending = deferred<EvaluationJob>(); vi.mocked(evaluationApi.createJob).mockReturnValue(pending.promise);
    await start(); fireEvent.click(screen.getByText("Create")); fireEvent.click(screen.getByText("Create"));
    expect(evaluationApi.createJob).toHaveBeenCalledTimes(1);
    expect(view().job.id).toBe("job-a");
    await act(async () => pending.resolve(evaluationJob("canonical-created")));
    await waitFor(() => expect(view().job?.id).toBe("canonical-created"));
    expect(view().job.state).toBe("queued");
  });
  test("an ambiguous transport outcome retains the same key on explicit resubmission", async () => {
    vi.mocked(evaluationApi.createJob).mockRejectedValueOnce(new EvaluationApiError(0)).mockResolvedValue(evaluationJob("canonical-created"));
    await start(); fireEvent.click(screen.getByText("Create"));
    await waitFor(() => expect(view().createError).toBe(0));
    fireEvent.click(screen.getByText("Create"));
    await waitFor(() => expect(evaluationApi.createJob).toHaveBeenCalledTimes(2));
    expect(vi.mocked(evaluationApi.createJob).mock.calls[0][2]).toBe(vi.mocked(evaluationApi.createJob).mock.calls[1][2]);
  });
  test("a delayed creation cannot select a job after disconnect", async () => {
    const pending = deferred<EvaluationJob>(); vi.mocked(evaluationApi.createJob).mockReturnValue(pending.promise);
    await start(); fireEvent.click(screen.getByText("Create")); fireEvent.click(screen.getByText("Disconnect"));
    await act(async () => pending.resolve(evaluationJob("late-created")));
    expect(view().job).toBeNull(); expect(view().createBusy).toBe(false);
  });
});
