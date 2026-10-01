import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { LocalWorkspaceSessionProvider, useLocalWorkspaceSession } from "./localWorkspaceSession";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

function Probe() {
  const session = useLocalWorkspaceSession();
  return (
    <div>
      <output data-testid="session-state">{session.status}:{session.canExecute ? "execution" : "read-only"}</output>
      <button type="button" onClick={() => void session.connect("fixture-only-token").catch(() => {})}>Connect</button>
      <button type="button" onClick={session.disconnect}>Disconnect</button>
    </div>
  );
}

function renderProbe() {
  return render(<LocalWorkspaceSessionProvider><Probe /></LocalWorkspaceSessionProvider>);
}

describe("Local workspace session owner", () => {
  test("accepts only a verified token and keeps the bearer out of browser storage", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      deployment_mode: "local",
      capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: true },
    }), { status: 200 })));
    const { unmount } = renderProbe();

    fireEvent.click(screen.getByRole("button", { name: "Connect" }));

    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("connected:execution"));
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(String(vi.mocked(fetch).mock.calls[0]?.[0])).toContain("/system/configuration-status");
    expect(new Headers(vi.mocked(fetch).mock.calls[0]?.[1]?.headers).get("Authorization")).toBe("Bearer fixture-only-token");
    expect(JSON.stringify(localStorage)).not.toContain("fixture-only-token");

    unmount();
    renderProbe();
    expect(screen.getByTestId("session-state")).toHaveTextContent("disconnected:read-only");
  });

  test("does not establish a session after a rejected credential", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("secret must not be reflected", { status: 401 })));
    renderProbe();

    fireEvent.click(screen.getByRole("button", { name: "Connect" }));

    await waitFor(() => expect(screen.getByTestId("session-state")).toHaveTextContent("disconnected:read-only"));
    expect(localStorage.length).toBe(0);
  });

  test("a late connection response cannot restore a session after disconnect", async () => {
    let complete: ((response: Response) => void) | undefined;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { complete = resolve; })));
    renderProbe();

    fireEvent.click(screen.getByRole("button", { name: "Connect" }));
    fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
    await act(async () => {
      complete?.(new Response(JSON.stringify({
        deployment_mode: "local",
        capabilities: { public_provider_free: true, local_workspace: true, execution_jobs: true },
      }), { status: 200 }));
    });

    expect(screen.getByTestId("session-state")).toHaveTextContent("disconnected:read-only");
  });
});
