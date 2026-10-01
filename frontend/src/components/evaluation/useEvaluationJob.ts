import { useCallback, useEffect, useRef, useState } from "react";
import { evaluationApi, EvaluationApiError, type EvaluationApiClient } from "../../lib/evaluationApi";
import type { EvaluationJob, EvaluationJobEvent, SafeJobResults } from "../../lib/evaluationTypes";
import { useLocalWorkspaceSession } from "../../lib/localWorkspaceSession";

const terminal = new Set(["cancelled", "succeeded", "failed", "interrupted"]);
function status(error: unknown): number { return error instanceof EvaluationApiError ? error.status : 0; }

/** A selection/session/page successor invalidates all writes, including A -> B -> A. */
export function useEvaluationJob(
  jobId: string | null,
  page = 1,
  api: EvaluationApiClient = evaluationApi,
  pollInterval = 1500,
) {
  const session = useLocalWorkspaceSession();
  const { getToken, generation, invalidateIfCurrent, status: sessionStatus } = session;
  const [job, setJob] = useState<EvaluationJob | null>(null);
  const [results, setResults] = useState<SafeJobResults | null>(null);
  const [events, setEvents] = useState<EvaluationJobEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [eventErrorStatus, setEventErrorStatus] = useState<number | null>(null);
  const [cancelErrorStatus, setCancelErrorStatus] = useState<number | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [reloadEpoch, setReloadEpoch] = useState(0);
  const lifetime = useRef(0);
  const active = useRef<{ epoch: number; jobId: string; token: string; generation: number; controller: AbortController } | null>(null);
  const jobRef = useRef<EvaluationJob | null>(null);
  const cancelOwner = useRef<number | null>(null);
  const reload = useCallback(() => setReloadEpoch((value) => value + 1), []);

  useEffect(() => {
    const epoch = ++lifetime.current;
    const controller = new AbortController();
    const token = getToken();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let cursor = 0;
    const current = () => lifetime.current === epoch && !controller.signal.aborted;
    const acceptJob = (next: EvaluationJob) => {
      if (!current()) return;
      if (next.id !== jobId) throw new EvaluationApiError(502);
      if (jobRef.current && next.revision < jobRef.current.revision) return;
      jobRef.current = next;
      setJob(next);
    };
    const refuse = (error: unknown) => {
      if (!current()) return;
      const code = status(error);
      setErrorStatus(code);
      if (code === 401 && token) invalidateIfCurrent(token, generation);
    };
    jobRef.current = null;
    cancelOwner.current = null;
    active.current = null;
    setJob(null); setResults(null); setEvents([]);
    setErrorStatus(null); setEventErrorStatus(null); setCancelErrorStatus(null); setCancelling(false);
    setLoading(Boolean(jobId && token && sessionStatus === "connected"));
    if (!jobId || !token || sessionStatus !== "connected") return () => { controller.abort(); if (lifetime.current === epoch) lifetime.current += 1; };
    active.current = { epoch, jobId, token, generation, controller };
    async function poll() {
      if (!current()) return;
      try {
        const detail = await api.getJob(token, jobId, controller.signal);
        acceptJob(detail);
        if (!current()) return;
        const pageResult = await api.getJobResults(token, jobId, { page }, controller.signal);
        if (!current()) return;
        if (pageResult.job_id !== jobId) throw new EvaluationApiError(502);
        setResults(pageResult); setErrorStatus(null);
        try {
          const batch = await api.getJobEvents(token, jobId, cursor, controller.signal);
          if (!current()) return;
          // API validates identity/order; the owner also deduplicates replay.
          const fresh = batch.filter((event) => event.job_id === jobId && event.sequence > cursor);
          if (fresh.length) {
            cursor = fresh[fresh.length - 1].sequence;
            setEvents((previous) => [...previous, ...fresh].slice(-100));
          }
          setEventErrorStatus(null);
        } catch (error) {
          if (!current()) return;
          setEventErrorStatus(status(error));
          if (status(error) === 401) invalidateIfCurrent(token, generation);
        }
      } catch (error) { refuse(error); }
      finally { if (current()) setLoading(false); }
      // Neither a finite SSE close nor a network error changes durable state.
      if (current() && !terminal.has(jobRef.current?.state ?? "")) timer = setTimeout(() => { void poll(); }, pollInterval);
    }
    void poll();
    return () => {
      controller.abort();
      if (timer !== undefined) clearTimeout(timer);
      if (lifetime.current === epoch) lifetime.current += 1;
      if (active.current?.epoch === epoch) active.current = null;
    };
  }, [api, generation, getToken, invalidateIfCurrent, jobId, page, pollInterval, reloadEpoch, sessionStatus]);

  const cancel = useCallback(async () => {
    const owner = active.current;
    const selected = jobRef.current;
    if (!owner || !selected || selected.id !== owner.jobId || cancelOwner.current !== null
      || !["queued", "running"].includes(selected.state) || !session.canExecute) return;
    const current = () => lifetime.current === owner.epoch && !owner.controller.signal.aborted;
    cancelOwner.current = owner.epoch;
    setCancelling(true); setCancelErrorStatus(null);
    try {
      const next = await api.cancelJob(owner.token, owner.jobId, selected.revision, owner.controller.signal);
      if (!current()) return;
      if (next.id !== owner.jobId) throw new EvaluationApiError(502);
      if (next.revision >= (jobRef.current?.revision ?? 0)) { jobRef.current = next; setJob(next); }
    } catch (error) {
      if (!current()) return;
      const code = status(error);
      setCancelErrorStatus(code);
      if (code === 401) invalidateIfCurrent(owner.token, owner.generation);
      if (code === 409) {
        try {
          const next = await api.getJob(owner.token, owner.jobId, owner.controller.signal);
          if (current() && next.id === owner.jobId && next.revision >= (jobRef.current?.revision ?? 0)) {
            jobRef.current = next; setJob(next);
          }
        } catch (reconcileError) { if (current()) setErrorStatus(status(reconcileError)); }
      }
    } finally {
      if (current() && cancelOwner.current === owner.epoch) { cancelOwner.current = null; setCancelling(false); }
    }
  }, [api, session.canExecute, invalidateIfCurrent]);
  return { job, results, events, loading, errorStatus, eventErrorStatus, cancelErrorStatus, cancelling, cancel, reload };
}
