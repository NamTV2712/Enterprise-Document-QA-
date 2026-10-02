import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { ConversationLibraryController } from "../../hooks/useConversationLibrary";
import { agentApi } from "../../lib/agentApi";
import { agentResearchRun } from "../../test/agentFixtures";
import { useConversationAgent } from "./useConversationAgent";

const session = vi.hoisted(() => ({ status: "connected", getToken: () => "synthetic-local-token", canExecute: true, generation: 1,
  decisionProviderAvailable: true, connect: vi.fn(), disconnect: vi.fn(), invalidateIfCurrent: vi.fn() }));
vi.mock("../../lib/localWorkspaceSession", () => ({ useLocalWorkspaceSession: () => session }));
const identity = { conversationId: "conversation-a", sessionId: "session-a", epoch: 1 };
let library: ConversationLibraryController;
beforeEach(() => {
  session.generation = 1; session.canExecute = true; session.decisionProviderAvailable = true;
  library = { activeConversationId: "conversation-a", activeRecord: null, isLegacyExample: false, writerStatus: { owned: true }, isLibraryReady: true,
    beginSend: vi.fn(() => identity), finishSend: vi.fn(), prepareAgentSend: vi.fn(async () => true), linkAgentRun: vi.fn(async () => {}),
    isIdentityActive: vi.fn(() => true), ensureSendable: vi.fn(), inputText: "Review filing risks" } as unknown as ConversationLibraryController;
  vi.spyOn(agentApi, "createRun").mockResolvedValue(agentResearchRun);
  vi.spyOn(agentApi, "listRuns").mockRejectedValue(new Error("Conversation creation must not list runs"));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
function enabled() {
  const hook = renderHook(() => useConversationAgent(library, "vi"));
  act(() => hook.result.current.setMode("deep")); act(() => hook.result.current.setConsent(true)); return hook;
}
test("defaults to Quick and cannot create an Agent run", async () => {
  const hook = renderHook(() => useConversationAgent(library, "en"));
  expect(hook.result.current.mode).toBe("quick");
  await act(async () => { expect(await hook.result.current.send("Review filing risks")).toBe(false); });
  expect(agentApi.createRun).not.toHaveBeenCalled();
});
test("Deep mode alone grants no provider permission", async () => {
  const hook = renderHook(() => useConversationAgent(library, "en")); act(() => hook.result.current.setMode("deep"));
  await act(async () => { await hook.result.current.send("Review filing risks"); });
  expect(agentApi.createRun).not.toHaveBeenCalled();
});
test("creates one generic run from the explicit goal and links it once, without Quick preflight or hidden history", async () => {
  const hook = enabled();
  await act(async () => { await Promise.all([hook.result.current.send(" Review filing risks "), hook.result.current.send("Review filing risks")]); });
  expect(agentApi.createRun).toHaveBeenCalledTimes(1);
  expect(agentApi.createRun).toHaveBeenCalledWith("synthetic-local-token", { goal: "Review filing risks", locale: "vi", allow_decision_provider_execution: true }, expect.any(String));
  expect(library.linkAgentRun).toHaveBeenCalledTimes(1); expect(library.ensureSendable).not.toHaveBeenCalled();
  expect(agentApi.listRuns).not.toHaveBeenCalled(); expect(hook.result.current.consent).toBe(false);
});
test("permission resets when switching mode", () => {
  const hook = enabled(); act(() => hook.result.current.setMode("quick")); act(() => hook.result.current.setMode("deep")); expect(hook.result.current.consent).toBe(false);
});
test("permission is revoked on a new connection lifetime", () => {
  const hook = enabled(); session.generation++; hook.rerender(); expect(hook.result.current.consent).toBe(false);
});
test("conversation navigation resets mode and consent", () => {
  const hook = enabled(); library.activeConversationId = "conversation-b"; hook.rerender(); expect(hook.result.current.mode).toBe("quick"); expect(hook.result.current.consent).toBe(false);
});
test("retains an accepted reference in its original conversation after navigation", async () => {
  let resolve!: (value: typeof agentResearchRun) => void;
  vi.mocked(agentApi.createRun).mockReturnValue(new Promise(done => { resolve = done; }));
  const hook = enabled(); let pending!: Promise<boolean>;
  await act(async () => { pending = hook.result.current.send("Review filing risks"); });
  library.activeConversationId = "conversation-b"; vi.mocked(library.isIdentityActive).mockReturnValue(false); hook.rerender();
  await act(async () => { resolve(agentResearchRun); expect(await pending).toBe(false); });
  expect(library.linkAgentRun).toHaveBeenCalledWith(identity, "Review filing risks", { runId: agentResearchRun.run_id, createdAt: Date.parse(agentResearchRun.created_at) });
});
test("revoking the connection while reserving the origin blocks the later POST", async () => {
  let resolve!: (value: boolean) => void;
  vi.mocked(library.prepareAgentSend).mockReturnValue(new Promise(done => { resolve = done; }));
  const hook = enabled(); let pending!: Promise<boolean>;
  await act(async () => { pending = hook.result.current.send("Review filing risks"); });
  session.generation++; hook.rerender();
  await act(async () => { resolve(true); expect(await pending).toBe(false); });
  expect(agentApi.createRun).not.toHaveBeenCalled();
});

test("read only execution capability blocks creation", async () => {
  session.canExecute = false; const hook = enabled(); await act(async () => { await hook.result.current.send("Review filing risks"); }); expect(agentApi.createRun).not.toHaveBeenCalled();
});
test("provider unavailable creates the existing truthful unavailable run without permission", async () => {
  session.decisionProviderAvailable = false; const hook = enabled();
  await act(async () => { await hook.result.current.send("Review filing risks"); });
  expect(agentApi.createRun).toHaveBeenCalledWith(expect.any(String), { goal: "Review filing risks", locale: "vi" }, expect.any(String));
});
