import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";

import { agentApi, AgentApiError } from "../../lib/agentApi";
import { LocaleProvider } from "../../lib/i18n";
import { LocalWorkspaceSessionProvider } from "../../lib/localWorkspaceSession";
import { pipelineApi } from "../../lib/pipelineApi";
import { agentEvaluation, agentEvents, agentProviderRun, agentResearchRun, agentRunPage, agentRunningRun } from "../../test/agentFixtures";
import { AgentWorkspace } from "./AgentWorkspace";

const TOKEN = "synthetic-secret-token-0123456789";

function Harness({ initial = null }: { initial?: string | null }) {
  const [selected, setSelected] = useState<string | null>(initial);
  return <LocaleProvider><LocalWorkspaceSessionProvider><AgentWorkspace selectedRunId={selected} onSelectRun={setSelected} onClearSelectedRun={() => setSelected(null)} onOpenDocument={vi.fn()} /></LocalWorkspaceSessionProvider></LocaleProvider>;
}

async function connect() {
  fireEvent.click(screen.getAllByRole("button", { name: "Connect local workspace" })[0]);
  fireEvent.change(screen.getByLabelText("Local workspace token"), { target: { value: TOKEN } });
  fireEvent.click(screen.getByRole("button", { name: "Verify and connect" }));
  await screen.findByText("Run history");
}

beforeEach(() => {
  localStorage.setItem("sec_qa_locale", "en");
  vi.spyOn(pipelineApi, "verifyLocalWorkspaceToken").mockResolvedValue({ deployment_mode: "local", capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: true } });
  vi.spyOn(agentApi, "listRuns").mockResolvedValue(agentRunPage);
  vi.spyOn(agentApi, "getRun").mockImplementation(async (_token, id) => id === agentResearchRun.run_id ? agentResearchRun : id === agentProviderRun.run_id ? agentProviderRun : agentRunningRun);
  vi.spyOn(agentApi, "getResult").mockImplementation(async (_token, id) => {
    const run = id === agentResearchRun.run_id ? agentResearchRun : id === agentProviderRun.run_id ? agentProviderRun : agentRunningRun;
    return { run_id: id, state: run.state, revision: run.revision, result: run.result, failure: run.failure };
  });
  vi.spyOn(agentApi, "getEvaluation").mockImplementation(async (_token, id) => ({ ...agentEvaluation, run_id: id }));
  vi.spyOn(agentApi, "getEvents").mockImplementation(async (_token, id) => id === agentResearchRun.run_id ? agentEvents : []);
  vi.spyOn(agentApi, "cancelRun").mockResolvedValue({ ...agentRunningRun, state: "cancelling", revision: 4 });
  vi.spyOn(agentApi, "createRun").mockResolvedValue(agentProviderRun);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.removeItem("sec_qa_locale"); });

describe("private Agent workspace", () => {
  it("uses backend capability and submits decision permission only after explicit consent", async () => {
    vi.mocked(pipelineApi.verifyLocalWorkspaceToken).mockResolvedValue({ deployment_mode: "local",
      capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: true },
      agent_decision_provider: { available: true } });
    render(<Harness />);
    await connect();
    expect(screen.getByText(/A supported structured decision provider is configured/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create recorded run" }));
    const consent = screen.getByRole("checkbox", { name: "Allow bounded decision-provider calls for this run" });
    expect(consent).not.toBeChecked();
    expect(consent).toBeEnabled();
    fireEvent.click(consent);
    fireEvent.change(screen.getByLabelText("Goal"), { target: { value: "Find current filing evidence." } });
    fireEvent.click(screen.getByRole("button", { name: "Create run" }));
    await waitFor(() => expect(agentApi.createRun).toHaveBeenCalledWith(TOKEN, {
      goal: "Find current filing evidence.", locale: "en", allow_decision_provider_execution: true,
    }, expect.any(String)));
    expect(document.body.textContent).not.toContain(TOKEN);
  });

  it("fails closed for missing capability and cannot enable provider consent", async () => {
    render(<Harness />);
    await connect();
    fireEvent.click(screen.getByRole("button", { name: "Create recorded run" }));
    expect(screen.getByRole("checkbox", { name: "Allow bounded decision-provider calls for this run" })).toBeDisabled();
  });

  it("does not turn configured decision capability into workspace execution permission", async () => {
    vi.mocked(pipelineApi.verifyLocalWorkspaceToken).mockResolvedValue({ deployment_mode: "local",
      capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: false },
      agent_decision_provider: { available: true } });
    render(<Harness />);
    await connect();
    expect(screen.getByText("Local access · execution disabled")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create recorded run" })).not.toBeInTheDocument();
  });
  it("does not fetch private run history while disconnected and clears the synthetic bearer after connection", async () => {
    const view = render(<Harness />);
    expect(screen.getByRole("heading", { name: "Private workspace disconnected" })).toBeInTheDocument();
    expect(agentApi.listRuns).not.toHaveBeenCalled();
    await connect();
    await screen.findByText(agentResearchRun.frozen.goal);
    expect(agentApi.listRuns).toHaveBeenCalledWith(TOKEN, 1, expect.any(AbortSignal));
    expect(document.body.textContent).not.toContain(TOKEN);
    expect(JSON.stringify(localStorage)).not.toContain(TOKEN);
    expect(JSON.stringify(sessionStorage)).not.toContain(TOKEN);
    expect(document.cookie).not.toContain(TOKEN);
    expect(window.location.href).not.toContain(TOKEN);
    fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
    expect(screen.getByRole("heading", { name: "Private workspace disconnected" })).toBeInTheDocument();
    expect(screen.queryByText(agentResearchRun.frozen.goal)).not.toBeInTheDocument();
    view.unmount();
    render(<Harness />);
    expect(screen.getByRole("heading", { name: "Private workspace disconnected" })).toBeInTheDocument();
  });

  it("shows recorded research, safe trace, result and native metrics without inventing a score", async () => {
    render(<Harness initial={agentResearchRun.run_id} />);
    await connect();
    expect(await screen.findByText("Research objectives")).toBeInTheDocument();
    expect(screen.getAllByText("Search attempts exhausted")).toHaveLength(2);
    expect(screen.getByText(agentResearchRun.result!.answer!)).toBeInTheDocument();
    await screen.findByText("0.6000");
    expect(screen.getByText("0.6000")).toBeInTheDocument();
    expect(screen.getAllByText("1 evidence IDs recorded")).toHaveLength(2);
    expect(screen.queryByText(/overall agent score|chain of thought|agent thoughts/i)).not.toBeInTheDocument();
  });

  it("separates the unconfigured structured decision provider from local access and recorded failure", async () => {
    render(<Harness initial={agentProviderRun.run_id} />);
    await connect();
    expect(await screen.findByText("Structured Agent decision provider is not configured for production execution.")).toBeInTheDocument();
    expect(screen.getByText("No final answer was recorded for this outcome.")).toBeInTheDocument();
    expect(screen.queryByText(agentResearchRun.result!.answer!)).not.toBeInTheDocument();
  });

  it("distinguishes an unknown run from an empty list", async () => {
    vi.mocked(agentApi.getRun).mockRejectedValue(new AgentApiError(404));
    render(<Harness initial="agent_missing" />);
    await connect();
    expect(await screen.findByText(/This Agent run was not found/)).toBeInTheDocument();
    expect(screen.queryByText("No Agent runs recorded in this local workspace.")).not.toBeInTheDocument();
  });

  it("validates explicit research objectives and creates only a real backend run", async () => {
    render(<Harness />);
    await connect();
    fireEvent.click(screen.getByRole("button", { name: "Create recorded run" }));
    const dialog = screen.getByRole("dialog", { name: "Create a recorded Agent run" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create run" }));
    expect(within(dialog).getByText(/Enter a goal of 5–500 characters/)).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Goal"), { target: { value: "Compare two issuers' AI risk evidence." } });
    fireEvent.change(within(dialog).getByLabelText("Mode"), { target: { value: "research" } });
    fireEvent.change(within(dialog).getByLabelText("Question"), { target: { value: "Find Microsoft AI risk evidence" } });
    fireEvent.change(within(dialog).getByLabelText("Ticker scope (optional)"), { target: { value: "MSFT" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create run" }));
    await waitFor(() => expect(agentApi.createRun).toHaveBeenCalledWith(TOKEN, {
      goal: "Compare two issuers' AI risk evidence.", locale: "en", research: { version: "agent_research_v1", objectives: [
        { objective_id: "objective_1", question: "Find Microsoft AI risk evidence", ticker_scope: "MSFT" },
      ] },
    }, expect.any(String)));
    expect(screen.queryByRole("dialog", { name: "Create a recorded Agent run" })).not.toBeInTheDocument();
  });

  it("shows running cancellation without claiming the run is already cancelled", async () => {
    vi.mocked(agentApi.getRun).mockResolvedValueOnce(agentRunningRun)
      .mockResolvedValue({ ...agentRunningRun, state: "cancelling", revision: 4 });
    render(<Harness initial={agentRunningRun.run_id} />);
    await connect();
    const cancel = await screen.findByRole("button", { name: "Request cancellation" });
    fireEvent.click(cancel);
    await waitFor(() => expect(agentApi.cancelRun).toHaveBeenCalledWith(TOKEN, agentRunningRun.run_id, 3));
    expect(await screen.findByText(/An in-flight call may continue/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request cancellation" })).not.toBeInTheDocument();
  });
});
