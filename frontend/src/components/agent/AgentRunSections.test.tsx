import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { agentCopy } from "./agentCopy";
import { AgentEvaluation, AgentFinalResult, AgentResearch, AgentTrace } from "./AgentRunSections";
import { agentEvaluation, agentEvents, agentProviderRun, agentResearchRun } from "../../test/agentFixtures";

afterEach(cleanup);

describe("Agent structural presentation", () => {
  it("renders only safe operational fields, in backend order", () => {
    render(<AgentTrace events={agentEvents} copy={agentCopy.en} locale="en" />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(9);
    expect(items[0]).toHaveTextContent("Queued");
    expect(items[3]).toHaveTextContent("Read document");
    expect(items[3]).toHaveTextContent("1 evidence IDs recorded");
    expect(screen.queryByText(/agent thoughts|chain of thought|scratchpad/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/argument_names|raw provider/i)).not.toBeInTheDocument();
  });

  it("preserves objective association, gap code meaning and canonical reader identity", () => {
    const openDocument = vi.fn();
    render(<AgentResearch run={agentResearchRun} summary={agentResearchRun.result!.research} copy={agentCopy.en} onOpenDocument={openDocument} />);
    expect(screen.getByText("Find Microsoft's AI risk evidence")).toBeInTheDocument();
    expect(screen.getByText("Find Alphabet's AI risk evidence")).toBeInTheDocument();
    expect(screen.getByText("Evidence threshold met")).toBeInTheDocument();
    expect(screen.getAllByText("Search attempts exhausted")).toHaveLength(2);
    expect(screen.getByText("MSFT:10-K:2025:chunk-1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open document" }));
    expect(openDocument).toHaveBeenCalledWith("MSFT:10-K:2025");
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
  });

  it("renders recorded answer only for completion and distinct provider unavailability", () => {
    const { rerender } = render(<AgentFinalResult run={agentResearchRun} result={null} copy={agentCopy.en} />);
    expect(screen.getByText(agentResearchRun.result!.answer!)).toBeInTheDocument();
    rerender(<AgentFinalResult run={agentProviderRun} result={null} copy={agentCopy.en} />);
    expect(screen.getByText(agentCopy.en.providerUnavailable)).toBeInTheDocument();
    expect(screen.queryByText(agentResearchRun.result!.answer!)).not.toBeInTheDocument();
    expect(screen.getByText(agentCopy.en.noAnswer)).toBeInTheDocument();
  });

  it("distinguishes computed zero, unavailable and not applicable without a score", () => {
    const metrics = agentEvaluation.metrics.map((item) => item.metric_id === "native_agent.objective_coverage"
      ? { ...item, status: "not_applicable" as const, value: null, numerator: null, denominator: null, reason_code: "nonresearch" }
      : item);
    render(<AgentEvaluation report={{ ...agentEvaluation, metrics }} copy={agentCopy.en} locale="en" />);
    expect(screen.getAllByText("0").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not applicable").length).toBeGreaterThan(0);
    expect(screen.getByText("0.6000")).toBeInTheDocument();
    expect(screen.getByText(agentCopy.en.limitation)).toBeInTheDocument();
    expect(screen.queryByText(/overall agent score|quality grade/i)).not.toBeInTheDocument();
  });

  it("uses Vietnamese labels for metrics, objectives and gap semantics", () => {
    render(<><AgentEvaluation report={agentEvaluation} copy={agentCopy.vi} locale="vi" />
      <AgentResearch run={agentResearchRun} summary={agentResearchRun.result!.research} copy={agentCopy.vi} onOpenDocument={vi.fn()} /></>);
    expect(screen.getByText("Mức dùng ngân sách công cụ")).toBeInTheDocument();
    expect(screen.getByText("Đạt ngưỡng bằng chứng")).toBeInTheDocument();
    expect(screen.getAllByText("Hết lượt tìm kiếm")).toHaveLength(2);
  });
});
