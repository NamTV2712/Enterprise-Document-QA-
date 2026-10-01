import { useCallback, useEffect, useRef, useState } from "react";
import { evaluationApi, EvaluationApiError, type EvaluationApiClient } from "../../lib/evaluationApi";
import type { EvaluationJob, EvaluationJobCreate } from "../../lib/evaluationTypes";
import { useLocalWorkspaceSession } from "../../lib/localWorkspaceSession";

/** One key per logical creation attempt; ambiguous transport outcomes keep it. */
export function useEvaluationCreation(onCreated: (job: EvaluationJob) => void, api: EvaluationApiClient = evaluationApi) {
  const session = useLocalWorkspaceSession();
  const { generation, getToken, invalidateIfCurrent } = session;
  const [busy, setBusy] = useState(false);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const attempt = useRef<{ fingerprint: string; key: string } | null>(null);
  const owner = useRef<AbortController | null>(null);
  const epoch = useRef(0);
  const callback = useRef(onCreated); callback.current = onCreated;
  useEffect(() => {
    epoch.current += 1;
    owner.current?.abort(); owner.current = null;
    attempt.current = null; setBusy(false); setErrorStatus(null);
    return () => { epoch.current += 1; owner.current?.abort(); owner.current = null; };
  }, [generation]);
  const submit = useCallback(async (body: EvaluationJobCreate) => {
    const token = getToken();
    if (owner.current || !token || !session.canExecute || session.status !== "connected") return;
    const fingerprint = JSON.stringify(body);
    if (!attempt.current || attempt.current.fingerprint !== fingerprint) attempt.current = { fingerprint, key: `evaluation-${crypto.randomUUID()}` };
    const logical = attempt.current;
    const controller = new AbortController();
    const requestEpoch = ++epoch.current;
    owner.current = controller; setBusy(true); setErrorStatus(null);
    const current = () => requestEpoch === epoch.current && !controller.signal.aborted;
    try {
      const job = await api.createJob(token, body, logical.key, controller.signal);
      if (!current()) return;
      attempt.current = null;
      callback.current(job);
    } catch (error) {
      if (!current()) return;
      const code = error instanceof EvaluationApiError ? error.status : 0;
      setErrorStatus(code);
      if (code === 401) invalidateIfCurrent(token, generation);
      // A definitive validation/access refusal permits a corrected new attempt.
      // 0/502/5xx can be an unknown committed outcome: keep the same binding.
      if (code >= 400 && code < 500 && code !== 409) attempt.current = null;
    } finally { if (current()) { owner.current = null; setBusy(false); } }
  }, [api, generation, getToken, invalidateIfCurrent, session.canExecute, session.status]);
  return { submit, busy, errorStatus };
}
