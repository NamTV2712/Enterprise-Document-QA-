import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { agentApi, AgentApiError } from "../../lib/agentApi";
import type { AgentEvent, AgentRun, AgentRunResult } from "../../lib/agentTypes";
import { agentEvaluation, agentResearchRun, agentRunPage } from "../../test/agentFixtures";
import { useAgentWorkspace } from "./useAgentWorkspace";

const session = vi.hoisted(() => ({
  status: "connected" as const, getToken: () => "synthetic-local-token", canExecute: true, generation: 1,
  connect: vi.fn(), disconnect: vi.fn(), invalidateIfCurrent: vi.fn(),
}));
vi.mock("../../lib/localWorkspaceSession", () => ({ useLocalWorkspaceSession: () => session }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
function resultFor(run: AgentRun): AgentRunResult {
  return { run_id: run.run_id, state: run.state, revision: run.revision, result: run.result, failure: run.failure };
}
function Harness({ id }: { id: string | null }) {
  const model = useAgentWorkspace(id);
  return <div>
    <output data-testid="goal">{model.run?.frozen.goal ?? "none"}</output>
    <output data-testid="answer">{model.result?.result?.answer ?? "none"}</output>
    <output data-testid="evaluation">{model.evaluation?.run_id ?? "none"}</output>
    <output data-testid="evaluation-digest">{model.evaluation?.digest ?? "none"}</output>
    <output data-testid="events">{model.events.map((item) => item.event_id).join(",")}</output>
    <output data-testid="notice">{model.cancelNotice ?? "none"}</output>
    <output data-testid="state">{model.run?.state ?? "none"}</output>
    <button onClick={() => { void model.cancel(); void model.cancel(); }}>Cancel twice</button>
  </div>;
}

beforeEach(() => {
  vi.spyOn(agentApi, "listRuns").mockResolvedValue(agentRunPage);
  vi.spyOn(agentApi, "getRun").mockResolvedValue(agentResearchRun);
  vi.spyOn(agentApi, "getResult").mockResolvedValue(resultFor(agentResearchRun));
  vi.spyOn(agentApi, "getEvaluation").mockResolvedValue(agentEvaluation);
  vi.spyOn(agentApi, "getEvents").mockResolvedValue([]);
  vi.spyOn(agentApi, "cancelRun").mockResolvedValue(agentResearchRun);
  session.invalidateIfCurrent.mockClear();
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Agent selected-run lifetimes", () => {
  it("rejects A#1 detail after B and A#2 select the same canonical ID", async () => {
    const oldA = deferred<AgentRun>();
    let aCalls = 0;
    const b = { ...agentResearchRun, run_id: "agent_beta", frozen: { ...agentResearchRun.frozen, goal: "B selected goal." } };
    const a2 = { ...agentResearchRun, frozen: { ...agentResearchRun.frozen, goal: "A second lifetime." } };
    vi.mocked(agentApi.getRun).mockImplementation(async (_token, id) => {
      if (id === "agent_beta") return b;
      aCalls += 1;
      return aCalls === 1 ? oldA.promise : a2;
    });
    vi.mocked(agentApi.getResult).mockImplementation(async (_token, id) => resultFor(id === "agent_beta" ? b : a2));
    vi.mocked(agentApi.getEvaluation).mockImplementation(async (_token, id) => ({ ...agentEvaluation, run_id: id }));
    const view = render(<Harness id="agent_alpha" />);
    await waitFor(() => expect(agentApi.getRun).toHaveBeenCalledTimes(1));
    view.rerender(<Harness id="agent_beta" />);
    await waitFor(() => expect(screen.getByTestId("goal")).toHaveTextContent("B selected goal."));
    view.rerender(<Harness id="agent_alpha" />);
    await waitFor(() => expect(screen.getByTestId("goal")).toHaveTextContent("A second lifetime."));
    await act(async () => oldA.resolve({ ...agentResearchRun, frozen: { ...agentResearchRun.frozen, goal: "A obsolete lifetime." } }));
    expect(screen.getByTestId("goal")).toHaveTextContent("A second lifetime.");
    expect(screen.getByTestId("answer")).toHaveTextContent(agentResearchRun.result!.answer!);
    expect(screen.getByTestId("evaluation")).toHaveTextContent("agent_alpha");
  });

  it("rejects old result and evaluation after A#1 → B → A#2", async () => {
    const oldResult = deferred<AgentRunResult>();
    const oldEvaluation = deferred<typeof agentEvaluation>();
    let aResults = 0, aEvaluations = 0;
    vi.mocked(agentApi.getRun).mockImplementation(async (_token, id) => ({ ...agentResearchRun, run_id: id }));
    vi.mocked(agentApi.getResult).mockImplementation(async (_token, id) => {
      if (id === "agent_alpha" && ++aResults === 1) return oldResult.promise;
      return resultFor({ ...agentResearchRun, run_id: id, result: { ...agentResearchRun.result!, answer: id === "agent_alpha" ? "A2 answer." : "B answer." } });
    });
    vi.mocked(agentApi.getEvaluation).mockImplementation(async (_token, id) => {
      if (id === "agent_alpha" && ++aEvaluations === 1) return oldEvaluation.promise;
      return { ...agentEvaluation, run_id: id };
    });
    const view = render(<Harness id="agent_alpha" />);
    await waitFor(() => expect(aResults).toBe(1));
    view.rerender(<Harness id="agent_beta" />);
    await waitFor(() => expect(screen.getByTestId("answer")).toHaveTextContent("B answer."));
    view.rerender(<Harness id="agent_alpha" />);
    await waitFor(() => expect(screen.getByTestId("answer")).toHaveTextContent("A2 answer."));
    await act(async () => {
      oldResult.resolve(resultFor({ ...agentResearchRun, result: { ...agentResearchRun.result!, answer: "A1 obsolete answer." } }));
      oldEvaluation.resolve({ ...agentEvaluation, digest: "obsolete" });
    });
    expect(screen.getByTestId("answer")).toHaveTextContent("A2 answer.");
    expect(screen.getByTestId("evaluation")).toHaveTextContent("agent_alpha");
    expect(screen.getByTestId("evaluation-digest")).toHaveTextContent(agentEvaluation.digest);
  });

  it("aborts an old finite event batch when returning to A in a new lifetime", async () => {
    const oldEvents = deferred<AgentEvent[]>();
    let aEvents = 0;
    vi.mocked(agentApi.getRun).mockImplementation(async (_token, id) => ({ ...agentResearchRun, run_id: id }));
    vi.mocked(agentApi.getResult).mockImplementation(async (_token, id) => resultFor({ ...agentResearchRun, run_id: id }));
    vi.mocked(agentApi.getEvaluation).mockImplementation(async (_token, id) => ({ ...agentEvaluation, run_id: id }));
    vi.mocked(agentApi.getEvents).mockImplementation(async (_token, id) => {
      if (id === "agent_alpha" && ++aEvents === 1) return oldEvents.promise;
      return [];
    });
    const view = render(<Harness id="agent_alpha" />);
    await waitFor(() => expect(aEvents).toBe(1));
    view.rerender(<Harness id="agent_beta" />);
    await waitFor(() => expect(screen.getByTestId("goal")).toHaveTextContent(agentResearchRun.frozen.goal));
    view.rerender(<Harness id="agent_alpha" />);
    await waitFor(() => expect(aEvents).toBe(2));
    await act(async () => oldEvents.resolve([{ run_id: "agent_alpha", event_id: "obsolete-event", sequence: 1, event_type: "created", state: "queued", reason_code: null, occurred_at: "2026-09-30T00:00:00Z", summary: null }]));
    expect(screen.getByTestId("events")).not.toHaveTextContent("obsolete-event");
  });

  it("uses one current revision, reconciles 409, and never force retries", async () => {
    const running = { ...agentResearchRun, state: "running" as const, revision: 3, result: null, finished_at: null };
    const changed = { ...running, state: "cancelling" as const, revision: 4 };
    vi.mocked(agentApi.getRun).mockResolvedValueOnce(running).mockResolvedValue(changed);
    vi.mocked(agentApi.getResult).mockResolvedValue(resultFor(running));
    vi.mocked(agentApi.cancelRun).mockRejectedValue(new AgentApiError(409));
    const view = render(<Harness id="agent_alpha" />);
    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("running"));
    fireEvent.click(screen.getByRole("button", { name: "Cancel twice" }));
    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("cancelling"));
    expect(agentApi.cancelRun).toHaveBeenCalledTimes(1);
    expect(agentApi.cancelRun).toHaveBeenCalledWith("synthetic-local-token", "agent_alpha", 3);
    expect(screen.getByTestId("notice")).toHaveTextContent("conflict");
    view.unmount();
  });
});
