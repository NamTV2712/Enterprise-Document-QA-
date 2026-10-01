import { useCallback, useEffect, useRef, useState } from "react";

import { agentApi, AgentApiError } from "../../lib/agentApi";
import type { AgentEvaluationReport, AgentEvent, AgentRun, AgentRunPage, AgentRunResult } from "../../lib/agentTypes";
import { useLocalWorkspaceSession } from "../../lib/localWorkspaceSession";

type LoadState = "idle" | "loading" | "ready" | "error";
type EvaluationState = "idle" | "loading" | "ready" | "not_applicable" | "error";
type EventState = "idle" | "loading" | "current" | "closed" | "error";

export function isTerminalAgentState(state: AgentRun["state"]): boolean {
  return state === "succeeded" || state === "failed" || state === "cancelled" || state === "interrupted";
}

function waitForNextBatch(signal: AbortSignal, ms: number): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) { resolve(); return; }
    const timeout = window.setTimeout(done, ms);
    function done() { window.clearTimeout(timeout); signal.removeEventListener("abort", done); resolve(); }
    signal.addEventListener("abort", done, { once: true });
  });
}

export function useAgentWorkspace(selectedRunId: string | null) {
  const session = useLocalWorkspaceSession();
  const token = session.getToken();
  const [page, setPage] = useState(1);
  const [listRefresh, setListRefresh] = useState(0);
  const [detailRefresh, setDetailRefresh] = useState(0);
  const [list, setList] = useState<AgentRunPage | null>(null);
  const [listGeneration, setListGeneration] = useState(-1);
  const [listState, setListState] = useState<LoadState>("idle");
  const [listError, setListError] = useState<number | null>(null);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [dataSerial, setDataSerial] = useState(-1);
  const [dataGeneration, setDataGeneration] = useState(-1);
  const [detailState, setDetailState] = useState<LoadState>("idle");
  const [detailError, setDetailError] = useState<number | null>(null);
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [resultState, setResultState] = useState<LoadState>("idle");
  const [evaluation, setEvaluation] = useState<AgentEvaluationReport | null>(null);
  const [evaluationState, setEvaluationState] = useState<EvaluationState>("idle");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [eventState, setEventState] = useState<EventState>("idle");
  const [eventCursor, setEventCursor] = useState(0);
  const [eventError, setEventError] = useState<number | null>(null);
  const [cancelPending, setCancelPending] = useState(false);
  const [cancelNotice, setCancelNotice] = useState<"requested" | "cancelled" | "conflict" | "error" | null>(null);
  const [createPending, setCreatePending] = useState(false);
  const [createError, setCreateError] = useState<number | null>(null);
  const listEpoch = useRef(0);
  const detailEpoch = useRef(0);
  const selection = useRef({ id: selectedRunId, serial: 0 });
  if (selection.current.id !== selectedRunId) selection.current = { id: selectedRunId, serial: selection.current.serial + 1 };
  const selectionSerial = selection.current.serial;
  const currentRun = useRef<AgentRun | null>(null);
  const noticeSerial = useRef(-1);
  const generationRef = useRef(session.generation);
  generationRef.current = session.generation;
  const cancelLock = useRef(false);
  const createLock = useRef(false);

  useEffect(() => {
    const epoch = ++listEpoch.current;
    const controller = new AbortController();
    if (!token) {
      setList(null);
      setListState("idle");
      setListError(null);
      return () => controller.abort();
    }
    setListState("loading");
    setListError(null);
    void agentApi.listRuns(token, page, controller.signal).then((response) => {
      if (controller.signal.aborted || epoch !== listEpoch.current) return;
      setList(response);
      setListGeneration(session.generation);
      setListState("ready");
    }).catch((error: unknown) => {
      if (controller.signal.aborted || epoch !== listEpoch.current) return;
      if (error instanceof AgentApiError && error.status === 401) session.invalidateIfCurrent(token, session.generation);
      setListError(error instanceof AgentApiError ? error.status : 0);
      setListState("error");
    });
    return () => controller.abort();
  }, [token, session.generation, session.invalidateIfCurrent, page, listRefresh]);

  useEffect(() => {
    const epoch = ++detailEpoch.current;
    const controller = new AbortController();
    const generation = session.generation;
    const isCurrent = () => !controller.signal.aborted && epoch === detailEpoch.current
      && selection.current.serial === selectionSerial;
    currentRun.current = null;
    setDataSerial(selectionSerial);
    setDataGeneration(generation);
    setRun(null);
    setResult(null);
    setEvaluation(null);
    setEvents([]);
    setEventCursor(0);
    if (noticeSerial.current !== selectionSerial) {
      setCancelNotice(null);
      noticeSerial.current = selectionSerial;
    }
    setDetailError(null);
    setEventError(null);
    setResultState("idle");
    setEvaluationState("idle");
    setEventState("idle");
    setDetailState(selectedRunId && token ? "loading" : "idle");
    if (!selectedRunId || !token) return () => controller.abort();

    async function refreshRelated(latest: AgentRun): Promise<void> {
      if (!token || !selectedRunId) return;
      setResultState("loading");
      setEvaluationState(isTerminalAgentState(latest.state) ? "loading" : "not_applicable");
      const resultPromise = agentApi.getResult(token, selectedRunId, controller.signal);
      const evaluationPromise = isTerminalAgentState(latest.state)
        ? agentApi.getEvaluation(token, selectedRunId, controller.signal) : Promise.resolve(null);
      const [resultOutcome, evaluationOutcome] = await Promise.allSettled([resultPromise, evaluationPromise]);
      if (!isCurrent()) return;
      if (resultOutcome.status === "fulfilled") { setResult(resultOutcome.value); setResultState("ready"); }
      else {
        if (resultOutcome.reason instanceof AgentApiError && resultOutcome.reason.status === 401) session.invalidateIfCurrent(token, generation);
        setResultState("error");
      }
      if (evaluationOutcome.status === "fulfilled") {
        setEvaluation(evaluationOutcome.value);
        setEvaluationState(evaluationOutcome.value ? "ready" : "not_applicable");
      } else {
        if (evaluationOutcome.reason instanceof AgentApiError && evaluationOutcome.reason.status === 401) session.invalidateIfCurrent(token, generation);
        setEvaluationState("error");
      }
    }

    async function refreshRun(): Promise<AgentRun> {
      if (!token || !selectedRunId) throw new AgentApiError(401);
      const latest = await agentApi.getRun(token, selectedRunId, controller.signal);
      if (isCurrent()) {
        currentRun.current = latest;
        setRun(latest);
        setDetailState("ready");
        setList((existing) => existing ? { ...existing, items: existing.items.map((item) =>
          item.run_id === latest.run_id ? latest : item) } : existing);
        await refreshRelated(latest);
      }
      return latest;
    }

    async function load(): Promise<void> {
      let latest: AgentRun;
      try { latest = await refreshRun(); }
      catch (error) {
        if (!isCurrent()) return;
        if (error instanceof AgentApiError && error.status === 401) session.invalidateIfCurrent(token!, generation);
        setDetailError(error instanceof AgentApiError ? error.status : 0);
        setDetailState("error");
        return;
      }
      if (!isCurrent()) return;
      let cursor = 0;
      setEventState("loading");
      while (isCurrent()) {
        try {
          const batch = await agentApi.getEvents(token!, selectedRunId!, cursor, controller.signal);
          if (!isCurrent()) return;
          if (batch.length) {
            cursor = batch[batch.length - 1].sequence;
            setEventCursor(cursor);
            setEvents((existing) => {
              const seen = new Set(existing.map((item) => item.sequence));
              return [...existing, ...batch.filter((item) => !seen.has(item.sequence))];
            });
            latest = await refreshRun();
            if (!isCurrent()) return;
          }
          setEventError(null);
          if (isTerminalAgentState(latest.state) && batch.length === 0) {
            setEventState("closed");
            return;
          }
          setEventState("current");
          await waitForNextBatch(controller.signal, 4_000);
        } catch (error) {
          if (!isCurrent()) return;
          const status = error instanceof AgentApiError ? error.status : 0;
          if (status === 401) session.invalidateIfCurrent(token!, generation);
          setEventError(status);
          setEventState("error");
          return;
        }
      }
    }
    void load();
    return () => controller.abort();
  }, [selectedRunId, selectionSerial, token, session.generation, session.invalidateIfCurrent, detailRefresh]);

  const refreshList = useCallback(() => setListRefresh((value) => value + 1), []);
  const refreshDetail = useCallback(() => setDetailRefresh((value) => value + 1), []);

  const cancel = useCallback(async () => {
    const latest = currentRun.current;
    const credential = session.getToken();
    if (!latest || latest.run_id !== selectedRunId || !credential || !session.canExecute || cancelLock.current
      || (latest.state !== "queued" && latest.state !== "running")) return;
    cancelLock.current = true;
    setCancelPending(true);
    setCancelNotice(null);
    const serial = selection.current.serial;
    const generation = session.generation;
    try {
      const response = await agentApi.cancelRun(credential, latest.run_id, latest.revision);
      if (selection.current.serial !== serial || session.getToken() !== credential) return;
      currentRun.current = response;
      setRun(response);
      setCancelNotice(response.state === "cancelled" ? "cancelled" : "requested");
      refreshList();
      refreshDetail();
    } catch (error) {
      if (selection.current.serial !== serial || session.getToken() !== credential) return;
      if (error instanceof AgentApiError && error.status === 401) session.invalidateIfCurrent(credential, generation);
      setCancelNotice(error instanceof AgentApiError && error.status === 409 ? "conflict" : "error");
      refreshDetail();
    } finally {
      cancelLock.current = false;
      if (selection.current.serial === serial) setCancelPending(false);
    }
  }, [selectedRunId, session, refreshList, refreshDetail]);

  const create = useCallback(async (body: Parameters<typeof agentApi.createRun>[1]): Promise<AgentRun | null> => {
    const credential = session.getToken();
    if (!credential || !session.canExecute || createLock.current) return null;
    createLock.current = true;
    setCreatePending(true);
    setCreateError(null);
    const generation = session.generation;
    try {
      const created = await agentApi.createRun(credential, body, crypto.randomUUID());
      if (session.getToken() !== credential || generationRef.current !== generation) return null;
      refreshList();
      return created;
    } catch (error) {
      if (session.getToken() === credential) {
        if (error instanceof AgentApiError && error.status === 401) session.invalidateIfCurrent(credential, generation);
        setCreateError(error instanceof AgentApiError ? error.status : 0);
      }
      return null;
    } finally {
      createLock.current = false;
      setCreatePending(false);
    }
  }, [session, refreshList]);

  return {
    session, token, page, setPage,
    list: token && listGeneration === session.generation ? list : null,
    listState: token && listGeneration !== session.generation ? "loading" as const : listState,
    listError, refreshList,
    run: token && dataSerial === selectionSerial && dataGeneration === session.generation && run?.run_id === selectedRunId ? run : null,
    detailState: token && selectedRunId && (dataSerial !== selectionSerial || dataGeneration !== session.generation) ? "loading" as const : detailState, detailError, refreshDetail,
    result: token && dataSerial === selectionSerial && dataGeneration === session.generation && result?.run_id === selectedRunId ? result : null, resultState,
    evaluation: token && dataSerial === selectionSerial && dataGeneration === session.generation && evaluation?.run_id === selectedRunId ? evaluation : null,
    evaluationState: dataSerial === selectionSerial && dataGeneration === session.generation ? evaluationState : "idle" as const,
    events: token && dataSerial === selectionSerial && dataGeneration === session.generation ? events.filter((item) => item.run_id === selectedRunId) : [],
    eventState: dataSerial === selectionSerial && dataGeneration === session.generation ? eventState : "idle" as const, eventCursor, eventError,
    cancel, cancelPending, cancelNotice, create, createPending, createError,
  };
}
