import { useCallback, useEffect, useRef, useState } from "react";
import { evaluationApi, EvaluationApiError, type EvaluationApiClient } from "../../lib/evaluationApi";
import type {
  EvaluationMetrics, FailureCategory, NativeComparison, NativeFailures, NativeMetricId,
  NativeResultsPage, NativeTrends, PublishedDetail, PublishedSummary,
} from "../../lib/evaluationTypes";

function code(error: unknown): number { return error instanceof EvaluationApiError ? error.status : 0; }

export function useEvaluationCatalog(selectedRunId: string | null, resultsPage = 1, api: EvaluationApiClient = evaluationApi) {
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const [reports, setReports] = useState<PublishedSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [detail, setDetail] = useState<PublishedDetail | null>(null);
  const [results, setResults] = useState<NativeResultsPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [detailErrorStatus, setDetailErrorStatus] = useState<number | null>(null);
  const [refresh, setRefresh] = useState(0);
  const refreshCatalog = useCallback(() => setRefresh((value) => value + 1), []);
  useEffect(() => {
    const controller = new AbortController(); let live = true;
    setLoading(true); setErrorStatus(null);
    void Promise.all([api.getMetrics(controller.signal), api.listReports({}, controller.signal)]).then(([catalog, list]) => {
      if (!live) return;
      setMetrics(catalog); setReports(list.items); setTotal(list.total);
    }).catch((error) => { if (live && !controller.signal.aborted) { setErrorStatus(code(error)); setMetrics(null); setReports([]); setTotal(0); } })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; controller.abort(); };
  }, [api, refresh]);
  useEffect(() => {
    const controller = new AbortController(); let live = true;
    setDetail(null); setResults(null); setDetailErrorStatus(null); setDetailLoading(Boolean(selectedRunId));
    if (!selectedRunId) return () => { live = false; controller.abort(); };
    void api.getReport(selectedRunId, controller.signal).then(async (next) => {
      if (!live) return;
      setDetail(next);
      if ("protocol" in next && next.protocol === "native-evaluation") {
        const resultPage = await api.getResults(selectedRunId, { page: resultsPage }, controller.signal);
        if (live) setResults(resultPage);
      }
    }).catch((error) => { if (live && !controller.signal.aborted) setDetailErrorStatus(code(error)); })
      .finally(() => { if (live) setDetailLoading(false); });
    return () => { live = false; controller.abort(); };
  }, [api, selectedRunId, resultsPage, refresh]);
  return { metrics, reports, total, detail, results, loading, detailLoading, errorStatus, detailErrorStatus, refreshCatalog };
}

export function useEvaluationCompare(api: EvaluationApiClient = evaluationApi) {
  const [comparison, setComparison] = useState<NativeComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const epoch = useRef(0); const controller = useRef<AbortController | null>(null);
  const compare = useCallback((baseline: string, candidate: string, metricIds?: NativeMetricId[]) => {
    const id = ++epoch.current; controller.current?.abort(); const next = new AbortController(); controller.current = next;
    setComparison(null); setLoading(true); setErrorStatus(null);
    void api.compare({ baseline_run_id: baseline, candidate_run_id: candidate, metric_ids: metricIds }, next.signal)
      .then((value) => { if (id === epoch.current) setComparison(value); })
      .catch((error) => { if (id === epoch.current && !next.signal.aborted) setErrorStatus(code(error)); })
      .finally(() => { if (id === epoch.current) setLoading(false); });
  }, [api]);
  const clear = useCallback(() => { epoch.current += 1; controller.current?.abort(); setComparison(null); setLoading(false); setErrorStatus(null); }, []);
  useEffect(() => clear, [clear]);
  return { comparison, loading, errorStatus, compare, clear };
}

export function useEvaluationTrends(api: EvaluationApiClient = evaluationApi) {
  const [trends, setTrends] = useState<NativeTrends | null>(null);
  const [loading, setLoading] = useState(false); const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const epoch = useRef(0); const controller = useRef<AbortController | null>(null);
  const load = useCallback((metricId: NativeMetricId) => {
    const id = ++epoch.current; controller.current?.abort(); const next = new AbortController(); controller.current = next;
    setTrends(null); setLoading(true); setErrorStatus(null);
    void api.getTrends({ metric_id: metricId }, next.signal).then((value) => { if (id === epoch.current) setTrends(value); })
      .catch((error) => { if (id === epoch.current && !next.signal.aborted) setErrorStatus(code(error)); })
      .finally(() => { if (id === epoch.current) setLoading(false); });
  }, [api]);
  useEffect(() => () => { epoch.current += 1; controller.current?.abort(); }, []);
  return { trends, loading, errorStatus, load };
}

export function useEvaluationFailures(api: EvaluationApiClient = evaluationApi) {
  const [failures, setFailures] = useState<NativeFailures | null>(null);
  const [loading, setLoading] = useState(false); const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const epoch = useRef(0); const controller = useRef<AbortController | null>(null);
  const load = useCallback((runId: string, category?: FailureCategory) => {
    const id = ++epoch.current; controller.current?.abort(); const next = new AbortController(); controller.current = next;
    setFailures(null); setLoading(true); setErrorStatus(null);
    void api.getFailures({ run_id: runId, category }, next.signal).then((value) => { if (id === epoch.current) setFailures(value); })
      .catch((error) => { if (id === epoch.current && !next.signal.aborted) setErrorStatus(code(error)); })
      .finally(() => { if (id === epoch.current) setLoading(false); });
  }, [api]);
  const clear = useCallback(() => { epoch.current += 1; controller.current?.abort(); setFailures(null); setLoading(false); setErrorStatus(null); }, []);
  useEffect(() => clear, [clear]);
  return { failures, loading, errorStatus, load, clear };
}
