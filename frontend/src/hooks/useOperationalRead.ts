import { useEffect, useRef, useState } from "react";
import { OperationalApiError } from "../lib/operationalApi";
import { useLocalWorkspaceSession } from "../lib/localWorkspaceSession";

// Identity is checked during render as well as completion, so an old population
// cannot flash beneath a newly selected range, filter, or credential generation.
export function useOperationalRead<T>(key: string, load: (signal: AbortSignal) => Promise<T>, enabled = true, privateRead = true) {
  const session = useLocalWorkspaceSession();
  const token = session.getToken();
  const selectedKey = `${key}:${privateRead ? session.generation : "public"}:${enabled}`;
  const selection = useRef({ key: selectedKey, lifetime: 0 });
  if (selection.current.key !== selectedKey) selection.current = { key: selectedKey, lifetime: selection.current.lifetime + 1 };
  const identity = `${selectedKey}:${selection.current.lifetime}`;
  const epoch = useRef(0);
  const [result, setResult] = useState<{ identity: string; data?: T; error?: unknown } | null>(null);
  useEffect(() => {
    const current = ++epoch.current;
    const controller = new AbortController();
    if (!enabled || (privateRead && !token)) return () => { epoch.current++; controller.abort(); };
    void load(controller.signal).then(data => {
      if (!controller.signal.aborted && epoch.current === current) setResult({ identity, data });
    }).catch(error => {
      if (controller.signal.aborted || epoch.current !== current) return;
      setResult({ identity, error });
      if (privateRead && token && error instanceof OperationalApiError && error.status === 401) session.invalidateIfCurrent(token, session.generation);
    });
    return () => { epoch.current++; controller.abort(); };
  }, [identity, enabled, load, privateRead, session.generation, session.invalidateIfCurrent, token]);
  const visible = result?.identity === identity ? result : null;
  if (privateRead && !token && result?.identity.startsWith(`${key}:`) && result.error instanceof OperationalApiError && result.error.status === 401) {
    return { data: undefined, error: result.error, loading: false, disconnected: false };
  }
  return { data: visible?.data, error: visible?.error, loading: enabled && (!privateRead || !!token) && !visible, disconnected: privateRead && !token };
}
