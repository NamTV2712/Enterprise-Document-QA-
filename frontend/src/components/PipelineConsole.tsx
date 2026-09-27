import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  ArrowRight,
  Check,
  CircleHelp,
  Database,
  FileStack,
  Layers3,
  LoaderCircle,
  LockKeyhole,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  Square,
  TableProperties,
  Workflow,
  X,
} from "lucide-react";

import { ModalDialog } from "./ui/ModalDialog";
import { useLocale } from "../lib/i18n";
import { useLocalWorkspaceSession } from "../lib/localWorkspaceSession";
import {
  PipelineApiError,
  pipelineApi,
  pipelineErrorMessage,
  type PipelineRunListParams,
} from "../lib/pipelineApi";
import type {
  PipelineDefinition,
  PipelineRun,
  PipelineRunEvent,
  PipelineRunState,
  PipelineStep,
} from "../types";

interface PipelineConsoleProps {
  selectedRunId?: string | null;
  onSelectRun?: (runId: string) => void;
  onClearSelectedRun?: () => void;
}

type Locale = "en" | "vi";
type RequestState = "idle" | "loading" | "ready" | "error" | "disconnected";
type PipelineFilter = PipelineRunState | "all";

const PAGE_SIZE = 25;
const POLL_DELAY_MS = 1_500;
const EXPECTED_STAGES = [
  "download_filings",
  "chunk_filings",
  "add_table_chunks",
  "embed_chunks",
  "index_chunks",
] as const;
const RUN_STATES: PipelineRunState[] = [
  "queued",
  "running",
  "cancelling",
  "cancelled",
  "succeeded",
  "failed",
  "interrupted",
];

const COPY = {
  en: {
    title: "Pipeline",
    subtitle: "Stage SEC 10-K ingestion in isolation. Queued records do not execute or promote.",
    connect: "Connect",
    connecting: "Verifying…",
    disconnect: "Disconnect",
    connected: "Connected · local",
    connectedFull: "Local workspace connected",
    readOnly: "Connected · read only",
    notConnected: "Not connected",
    notConnectedFull: "Local workspace not connected",
    stageRun: "Stage run",
    executionDisabled: "Run staging and cancellation are disabled by the local workspace policy.",
    definitionLoading: "Loading the registered pipeline definition…",
    definitionUnavailable: "The pipeline definition is unavailable from this API.",
    invalidDefinition: "The API returned a pipeline definition this page cannot safely display.",
    metrics: ["Registered inputs", "Pipeline steps", "Staging profiles", "Staged runs"],
    stages: "Pipeline stages",
    stagesSubtitle: "The registered order for an isolated staging request.",
    stagingOnly: "Staging only",
    stageSafeNote: "This creates a queued record only. No worker, provider, canonical corpus, or serving index is touched.",
    history: "Run history",
    historySubtitle: "Durable local staging records · newest first",
    allStates: "All states",
    searchRuns: "Search run ID or ticker",
    colRun: "Run ID",
    colInput: "Input",
    colCreated: "Created",
    colState: "State",
    loadingRuns: "Loading local run history…",
    connectForRuns: "Connect to view local runs",
    connectForRunsBody: "Run history is private to this local workspace. The public pipeline definition remains available without a token.",
    emptyRuns: "No staged runs yet",
    emptyRunsBody: "Stage a request to create an auditable queued record. It will not execute by itself.",
    noSearchMatch: "No runs match this search.",
    listUnavailable: "Run history could not be loaded.",
    retry: "Retry",
    refresh: "Refresh",
    previous: "Previous",
    next: "Next",
    pageOf: "Page {page} of {pages}",
    resultCount: "{count} runs",
    details: "Run details",
    detailsPrompt: "Select a run to inspect its current server state.",
    detailDisconnected: "Connect to the local workspace to open this private run.",
    loadingDetail: "Loading run details…",
    detailUnavailable: "This run could not be loaded.",
    runNotFound: "This run was not found. It may have been removed or the link may be stale.",
    selectRun: "Select a run",
    state: "State",
    created: "Created",
    updated: "Updated",
    started: "Started",
    finished: "Finished",
    stagingProfile: "Staging profile",
    configuration: "Configuration fingerprint",
    progress: "Progress",
    progressUnknown: "Not reported",
    steps: "Steps",
    noArtifacts: "No staged artifacts have been reported.",
    artifactReferences: "Staged artifact references",
    stageDoesNotRun: "A staged run does not execute ingestion or change the serving corpus.",
    cancel: "Request cancellation",
    cancelling: "Requesting…",
    cancelUnavailable: "Cancellation is disabled by the local execution policy.",
    cancelQueued: "Queued run cancelled.",
    cancelRequested: "Cancellation requested. The run remains cancelling until the backend confirms it.",
    updatesWaiting: "SSE batch closed · reconnecting from event {sequence}.",
    updatesConnecting: "Connecting to run events…",
    updatesUnavailable: "Run details are retained; event updates will retry.",
    updatesComplete: "Event history is up to date.",
    recentEvents: "Recent events",
    noEvents: "No run events have been received in this view yet.",
    connectTitle: "Connect local workspace",
    connectDescription: "Enter the local API bearer token. It is verified once and kept in memory for this tab only.",
    tokenLabel: "Local workspace token",
    tokenPlaceholder: "Bearer token",
    tokenSafety: "The token is not saved to browser storage, URL, or application settings.",
    verifyConnect: "Verify and connect",
    close: "Close",
    stageTitle: "Stage an isolated run",
    stageDescription: "Choose one or more registered ticker inputs. This only creates a queued staging record.",
    tickerSearch: "Filter registered tickers",
    selectedInputs: "{count} selected",
    selectVisible: "Select visible",
    clearSelection: "Clear selection",
    inputRequired: "Select at least one ticker.",
    profile: "Staging profile",
    isolated: "Isolated",
    submitStage: "Create staged run",
    submittingStage: "Creating…",
    stageAccepted: "Staged record created. No ingestion work has run.",
    reason: "Reason",
    eventCreated: "Created",
    eventState: "State changed",
    eventProgress: "Progress updated",
    eventStep: "Step changed",
    eventCancelRequested: "Cancellation requested",
    eventCancelled: "Cancelled",
    eventInterrupted: "Interrupted",
    stageNames: {
      download_filings: "Download filings",
      chunk_filings: "Chunk filings",
      add_table_chunks: "Add table chunks",
      embed_chunks: "Embed chunks",
      index_chunks: "Index chunks",
    },
    runStates: {
      queued: "Queued",
      running: "Running",
      cancelling: "Cancelling",
      cancelled: "Cancelled",
      succeeded: "Succeeded",
      failed: "Failed",
      interrupted: "Interrupted",
      pending: "Pending",
      skipped: "Skipped",
    },
    unknownError: "The local workspace request could not be completed. Check the connection and retry.",
  },
  vi: {
    title: "Pipeline",
    subtitle: "Tạo yêu cầu nạp SEC 10-K cô lập. Bản ghi đang chờ không thực thi hoặc đưa dữ liệu vào phục vụ.",
    connect: "Kết nối",
    connecting: "Đang xác minh…",
    disconnect: "Ngắt kết nối",
    connected: "Đã kết nối · cục bộ",
    connectedFull: "Đã kết nối workspace cục bộ",
    readOnly: "Đã kết nối · chỉ đọc",
    notConnected: "Chưa kết nối",
    notConnectedFull: "Chưa kết nối workspace cục bộ",
    stageRun: "Tạo bản ghi staging",
    executionDisabled: "Chính sách workspace cục bộ đã tắt staging và hủy run.",
    definitionLoading: "Đang tải định nghĩa pipeline đã đăng ký…",
    definitionUnavailable: "API này không cung cấp định nghĩa pipeline.",
    invalidDefinition: "API trả về định nghĩa pipeline mà trang không thể hiển thị an toàn.",
    metrics: ["Ticker đã đăng ký", "Bước pipeline", "Hồ sơ staging", "Run đã staging"],
    stages: "Các bước pipeline",
    stagesSubtitle: "Thứ tự đã đăng ký cho một yêu cầu staging cô lập.",
    stagingOnly: "Chỉ staging",
    stageSafeNote: "Chỉ tạo bản ghi đang chờ. Không gọi worker/provider và không sửa corpus hoặc serving index.",
    history: "Lịch sử run",
    historySubtitle: "Bản ghi staging cục bộ đã lưu · mới nhất trước",
    allStates: "Tất cả trạng thái",
    searchRuns: "Tìm mã run hoặc ticker",
    colRun: "Mã run",
    colInput: "Đầu vào",
    colCreated: "Ngày tạo",
    colState: "Trạng thái",
    loadingRuns: "Đang tải lịch sử run cục bộ…",
    connectForRuns: "Kết nối để xem run cục bộ",
    connectForRunsBody: "Lịch sử run thuộc workspace cục bộ. Định nghĩa pipeline công khai vẫn xem được mà không cần token.",
    emptyRuns: "Chưa có run staging",
    emptyRunsBody: "Tạo một yêu cầu để lưu bản ghi đang chờ. Yêu cầu không tự chạy.",
    noSearchMatch: "Không có run phù hợp với tìm kiếm.",
    listUnavailable: "Không thể tải lịch sử run.",
    retry: "Thử lại",
    refresh: "Làm mới",
    previous: "Trước",
    next: "Tiếp",
    pageOf: "Trang {page} / {pages}",
    resultCount: "{count} run",
    details: "Chi tiết run",
    detailsPrompt: "Chọn một run để xem trạng thái hiện tại từ máy chủ.",
    detailDisconnected: "Kết nối workspace cục bộ để mở run riêng tư này.",
    loadingDetail: "Đang tải chi tiết run…",
    detailUnavailable: "Không thể tải run này.",
    runNotFound: "Không tìm thấy run. Run có thể đã bị xóa hoặc liên kết đã cũ.",
    selectRun: "Chọn một run",
    state: "Trạng thái",
    created: "Đã tạo",
    updated: "Cập nhật",
    started: "Bắt đầu",
    finished: "Kết thúc",
    stagingProfile: "Hồ sơ staging",
    configuration: "Dấu vân tay cấu hình",
    progress: "Tiến độ",
    progressUnknown: "Chưa được báo cáo",
    steps: "Các bước",
    noArtifacts: "Chưa có artifact staging nào được báo cáo.",
    artifactReferences: "Tham chiếu artifact staging",
    stageDoesNotRun: "Run staging không thực thi ingestion và không thay đổi corpus đang phục vụ.",
    cancel: "Yêu cầu hủy",
    cancelling: "Đang yêu cầu…",
    cancelUnavailable: "Chính sách thực thi cục bộ đã tắt chức năng hủy.",
    cancelQueued: "Run đang chờ đã được hủy.",
    cancelRequested: "Đã yêu cầu hủy. Run vẫn ở trạng thái đang hủy cho đến khi backend xác nhận.",
    updatesWaiting: "Batch SSE đã đóng · đang kết nối lại từ sự kiện {sequence}.",
    updatesConnecting: "Đang kết nối sự kiện run…",
    updatesUnavailable: "Chi tiết run được giữ nguyên; sự kiện sẽ tự thử lại.",
    updatesComplete: "Lịch sử sự kiện đã cập nhật.",
    recentEvents: "Sự kiện gần đây",
    noEvents: "Chưa nhận sự kiện run trong chế độ xem này.",
    connectTitle: "Kết nối workspace cục bộ",
    connectDescription: "Nhập bearer token của API cục bộ. Token được xác minh một lần và chỉ giữ trong bộ nhớ của tab này.",
    tokenLabel: "Token workspace cục bộ",
    tokenPlaceholder: "Bearer token",
    tokenSafety: "Token không được lưu vào browser storage, URL hoặc cài đặt ứng dụng.",
    verifyConnect: "Xác minh và kết nối",
    close: "Đóng",
    stageTitle: "Tạo run staging cô lập",
    stageDescription: "Chọn một hoặc nhiều ticker đã đăng ký. Thao tác chỉ lưu một bản ghi staging đang chờ.",
    tickerSearch: "Lọc ticker đã đăng ký",
    selectedInputs: "Đã chọn {count}",
    selectVisible: "Chọn mục đang thấy",
    clearSelection: "Bỏ chọn",
    inputRequired: "Hãy chọn ít nhất một ticker.",
    profile: "Hồ sơ staging",
    isolated: "Cô lập",
    submitStage: "Tạo bản ghi staging",
    submittingStage: "Đang tạo…",
    stageAccepted: "Đã tạo bản ghi staging. Chưa có công việc ingestion nào chạy.",
    reason: "Lý do",
    eventCreated: "Đã tạo",
    eventState: "Trạng thái thay đổi",
    eventProgress: "Đã cập nhật tiến độ",
    eventStep: "Bước đã thay đổi",
    eventCancelRequested: "Đã yêu cầu hủy",
    eventCancelled: "Đã hủy",
    eventInterrupted: "Đã gián đoạn",
    stageNames: {
      download_filings: "Tải hồ sơ",
      chunk_filings: "Chia đoạn",
      add_table_chunks: "Thêm đoạn bảng tài chính",
      embed_chunks: "Tạo embedding",
      index_chunks: "Lập chỉ mục staging",
    },
    runStates: {
      queued: "Đang chờ",
      running: "Đang chạy",
      cancelling: "Đang hủy",
      cancelled: "Đã hủy",
      succeeded: "Thành công",
      failed: "Thất bại",
      interrupted: "Bị gián đoạn",
      pending: "Chờ xử lý",
      skipped: "Đã bỏ qua",
    },
    unknownError: "Không thể hoàn tất yêu cầu workspace cục bộ. Hãy kiểm tra kết nối và thử lại.",
  },
} as const;

function interpolate(value: string, values: Record<string, string | number>): string {
  return value.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? ""));
}

function isTerminalState(state: PipelineRunState): boolean {
  return state === "cancelled" || state === "succeeded" || state === "failed" || state === "interrupted";
}

function validDefinition(definition: PipelineDefinition): boolean {
  return definition.pipeline_id === "sec_10k_ingestion"
    && definition.input_kind === "ticker"
    && definition.staging_profiles.includes("isolated")
    && definition.stages.length === EXPECTED_STAGES.length
    && definition.stages.every((stage, index) => stage.stage_id === EXPECTED_STAGES[index] && stage.order === index + 1)
    && definition.capabilities.executes_during_staging === false
    && definition.capabilities.automatically_promotes_to_serving === false;
}

function errorMessage(error: unknown, locale: Locale, fallback: string): string {
  if (error instanceof PipelineApiError) return pipelineErrorMessage(error.status, locale);
  return fallback;
}

function formatDate(value: string | null, locale: Locale): string {
  if (!value || !Number.isFinite(Date.parse(value))) return "—";
  return new Intl.DateTimeFormat(locale === "vi" ? "vi-VN" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function stateTone(state: string): string {
  if (state === "succeeded") return "console-pill--high";
  if (state === "failed" || state === "interrupted") return "console-pill--low";
  if (state === "running" || state === "cancelling") return "console-pill--mid";
  if (state === "queued") return "console-pill--info";
  return "console-pill--neutral";
}

function sleepUntilNextPoll(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) {
      resolve();
      return;
    }
    const finish = () => {
      window.clearTimeout(timer);
      signal.removeEventListener("abort", finish);
      resolve();
    };
    const timer = window.setTimeout(finish, ms);
    signal.addEventListener("abort", finish, { once: true });
  });
}

function updateRunInList(runs: PipelineRun[], updated: PipelineRun): PipelineRun[] {
  return runs.map((run) => run.id === updated.id ? updated : run);
}

export function PipelineConsole({
  selectedRunId = null,
  onSelectRun = () => {},
  onClearSelectedRun = () => {},
}: PipelineConsoleProps) {
  const { locale: appLocale } = useLocale();
  const locale: Locale = appLocale;
  const copy = COPY[locale];
  const session = useLocalWorkspaceSession();
  const token = session.getToken();
  const [definition, setDefinition] = useState<PipelineDefinition | null>(null);
  const [definitionState, setDefinitionState] = useState<RequestState>("loading");
  const [definitionError, setDefinitionError] = useState("");
  const [definitionRefresh, setDefinitionRefresh] = useState(0);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [totalRuns, setTotalRuns] = useState<number | null>(null);
  const [listState, setListState] = useState<RequestState>("idle");
  const [listError, setListError] = useState("");
  const [listRefresh, setListRefresh] = useState(0);
  const [page, setPage] = useState(1);
  const [stateFilter, setStateFilter] = useState<PipelineFilter>("all");
  const [search, setSearch] = useState("");
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null);
  const [detailState, setDetailState] = useState<RequestState>("idle");
  const [detailError, setDetailError] = useState("");
  const [detailRefresh, setDetailRefresh] = useState(0);
  const [streamStatus, setStreamStatus] = useState<"idle" | "connecting" | "reconnecting" | "error" | "complete">("idle");
  const [streamError, setStreamError] = useState("");
  const [events, setEvents] = useState<PipelineRunEvent[]>([]);
  const [eventCursor, setEventCursor] = useState(0);
  const [connectDialogOpen, setConnectDialogOpen] = useState(false);
  const [tokenDraft, setTokenDraft] = useState("");
  const [connectError, setConnectError] = useState("");
  const [stageDialogOpen, setStageDialogOpen] = useState(false);
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [tickerSearch, setTickerSearch] = useState("");
  const [stageError, setStageError] = useState("");
  const [stagePending, setStagePending] = useState(false);
  const [cancelPending, setCancelPending] = useState(false);
  const [cancelError, setCancelError] = useState("");
  const [notice, setNotice] = useState("");
  const [cancelNotice, setCancelNotice] = useState("");
  const tokenInputRef = useRef<HTMLInputElement>(null);
  const stageInputRef = useRef<HTMLInputElement>(null);
  const listRequestRef = useRef(0);
  const detailRequestRef = useRef(0);
  const stagePendingRef = useRef(false);
  const stageControllerRef = useRef<AbortController | null>(null);
  const cancelControllerRef = useRef<AbortController | null>(null);

  const selectRun = useCallback((runId: string) => {
    setNotice("");
    setCancelNotice("");
    onSelectRun(runId);
  }, [onSelectRun]);

  useEffect(() => {
    setCancelError("");
  }, [selectedRunId]);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setDefinitionState("loading");
    setDefinitionError("");
    void pipelineApi.getDefinition(controller.signal).then((result) => {
      if (!current) return;
      if (!validDefinition(result)) {
        setDefinition(null);
        setDefinitionState("error");
        setDefinitionError(copy.invalidDefinition);
        return;
      }
      setDefinition(result);
      setDefinitionState("ready");
    }).catch((error: unknown) => {
      if (!current || controller.signal.aborted) return;
      setDefinition(null);
      setDefinitionState("error");
      setDefinitionError(error instanceof PipelineApiError && error.status === 404
        ? copy.definitionUnavailable
        : copy.unknownError);
    });
    return () => {
      current = false;
      controller.abort();
    };
  }, [copy.definitionUnavailable, copy.invalidDefinition, copy.unknownError, definitionRefresh]);

  useEffect(() => {
    const requestId = ++listRequestRef.current;
    const controller = new AbortController();
    let current = true;
    setListError("");
    if (!token) {
      setRuns([]);
      setTotalRuns(null);
      setListState("idle");
      return () => {
        current = false;
        controller.abort();
      };
    }
    setListState("loading");
    const params: PipelineRunListParams = { page, page_size: PAGE_SIZE, state: stateFilter };
    void pipelineApi.listRuns(token, params, controller.signal).then((result) => {
      if (!current || requestId !== listRequestRef.current) return;
      setRuns(result.items);
      setTotalRuns(result.total);
      setListState("ready");
    }).catch((error: unknown) => {
      if (!current || controller.signal.aborted || requestId !== listRequestRef.current) return;
      if (error instanceof PipelineApiError && error.status === 401) {
        session.invalidateIfCurrent(token, session.generation);
        return;
      }
      setListState("error");
      setListError(errorMessage(error, locale, copy.unknownError));
    });
    return () => {
      current = false;
      controller.abort();
    };
  }, [copy.unknownError, locale, page, session.generation, session.invalidateIfCurrent, token, stateFilter, listRefresh]);

  useEffect(() => {
    const runId = selectedRunId;
    const requestId = ++detailRequestRef.current;
    const controller = new AbortController();
    let current = true;
    let run: PipelineRun | null = null;
    let cursor = 0;
    let retryDelay = POLL_DELAY_MS;
    setSelectedRun(null);
    setEvents([]);
    setEventCursor(0);
    setStreamError("");
    setCancelNotice("");
    setCancelPending(false);
    setDetailError("");
    if (runId) setDetailState(token ? "loading" : "disconnected");
    else {
      setDetailState("idle");
      setStreamStatus("idle");
    }
    if (!runId || !token) {
      return () => {
        current = false;
        controller.abort();
        cancelControllerRef.current?.abort();
      };
    }
    const generation = session.generation;
    const isCurrent = () => current && !controller.signal.aborted && requestId === detailRequestRef.current;
    const refreshDetail = async (): Promise<PipelineRun> => {
      const latest = await pipelineApi.getRun(token, runId, controller.signal);
      if (isCurrent()) {
        run = latest;
        setSelectedRun(latest);
        setRuns((existing) => updateRunInList(existing, latest));
        setDetailState("ready");
      }
      return latest;
    };
    const start = async () => {
      try {
        run = await refreshDetail();
      } catch (error) {
        if (!isCurrent()) return;
        if (error instanceof PipelineApiError && error.status === 401) {
          session.invalidateIfCurrent(token, generation);
          return;
        }
        setDetailState("error");
        setDetailError(error instanceof PipelineApiError && error.status === 404
          ? copy.runNotFound
          : errorMessage(error, locale, copy.unknownError));
        return;
      }
      setStreamStatus("connecting");
      while (isCurrent() && run) {
        let batch: PipelineRunEvent[];
        try {
          batch = await pipelineApi.getRunEvents(token, runId, cursor, controller.signal);
          if (!isCurrent()) return;
          retryDelay = POLL_DELAY_MS;
          if (batch.length > 0) {
            cursor = batch[batch.length - 1].sequence;
            setEventCursor(cursor);
            setEvents((currentEvents) => [...currentEvents, ...batch].slice(-20));
            run = await refreshDetail();
          }
          setStreamError("");
          setStreamStatus("reconnecting");
          if (isTerminalState(run.state) && batch.length === 0) {
            setStreamStatus("complete");
            return;
          }
          await sleepUntilNextPoll(POLL_DELAY_MS, controller.signal);
        } catch (error) {
          if (!isCurrent()) return;
          if (error instanceof PipelineApiError && [401, 403, 404, 422].includes(error.status)) {
            if (error.status === 401) session.invalidateIfCurrent(token, generation);
            if (error.status === 404) {
              setDetailState("error");
              setDetailError(copy.runNotFound);
            } else {
              setStreamError(errorMessage(error, locale, copy.unknownError));
            }
            setStreamStatus("error");
            return;
          }
          setStreamError(copy.updatesUnavailable);
          setStreamStatus("error");
          await sleepUntilNextPoll(retryDelay, controller.signal);
          retryDelay = Math.min(retryDelay * 2, 12_000);
          setStreamStatus("reconnecting");
        }
      }
    };
    void start();
    return () => {
      current = false;
      controller.abort();
      cancelControllerRef.current?.abort();
    };
  }, [copy.runNotFound, copy.unknownError, copy.updatesUnavailable, locale, selectedRunId, session.generation, session.invalidateIfCurrent, token, detailRefresh]);

  useEffect(() => () => {
    stageControllerRef.current?.abort();
    cancelControllerRef.current?.abort();
  }, []);

  const registeredInputs = definition?.registered_input_ids ?? [];
  const filteredTickers = useMemo(() => {
    const needle = tickerSearch.trim().toLocaleUpperCase();
    return registeredInputs.filter((ticker) => ticker.includes(needle));
  }, [registeredInputs, tickerSearch]);
  const visibleRuns = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase();
    if (!needle) return runs;
    return runs.filter((run) => run.id.toLocaleLowerCase().includes(needle)
      || run.input_ids.some((ticker) => ticker.toLocaleLowerCase().includes(needle)));
  }, [runs, search]);
  const totalPages = Math.max(1, Math.ceil((totalRuns ?? 0) / PAGE_SIZE));
  const showCancel = Boolean(selectedRun && session.canExecute
    && (selectedRun.state === "queued" || selectedRun.state === "running"));
  const canCancel = showCancel && !cancelPending;

  const refresh = useCallback(() => {
    setDefinitionRefresh((value) => value + 1);
    setListRefresh((value) => value + 1);
    if (selectedRunId) setDetailRefresh((value) => value + 1);
  }, [selectedRunId]);

  const handleConnect = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setConnectError("");
    try {
      await session.connect(tokenDraft);
      setTokenDraft("");
      setConnectDialogOpen(false);
      setPage(1);
      setListRefresh((value) => value + 1);
    } catch (error) {
      setTokenDraft("");
      setConnectError(errorMessage(error, locale, copy.unknownError));
      requestAnimationFrame(() => tokenInputRef.current?.focus());
    }
  };

  const handleDisconnect = () => {
    session.disconnect();
    setConnectError("");
    setTokenDraft("");
    setNotice("");
    setCancelNotice("");
  };

  const handleStage = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !session.canExecute || selectedTickers.length === 0 || stagePendingRef.current) return;
    stagePendingRef.current = true;
    setStagePending(true);
    setStageError("");
    setNotice("");
    const controller = new AbortController();
    stageControllerRef.current = controller;
    try {
      const staged = await pipelineApi.stageRun(token, {
        input_ids: [...selectedTickers],
        staging_profile: "isolated",
      }, controller.signal);
      if (controller.signal.aborted) return;
      setNotice(copy.stageAccepted);
      setStageDialogOpen(false);
      setSelectedTickers([]);
      setTickerSearch("");
      setPage(1);
      setStateFilter("all");
      setListRefresh((value) => value + 1);
      onSelectRun(staged.id);
    } catch (error) {
      if (controller.signal.aborted) return;
      if (error instanceof PipelineApiError && error.status === 401) {
        session.invalidateIfCurrent(token, session.generation);
      }
      setStageError(errorMessage(error, locale, copy.unknownError));
    } finally {
      stagePendingRef.current = false;
      stageControllerRef.current = null;
      setStagePending(false);
    }
  };

  const handleCancel = async () => {
    if (!selectedRun || !token || !session.canExecute || !canCancel) return;
    const generation = session.generation;
    const selectionEpoch = detailRequestRef.current;
    const controller = new AbortController();
    cancelControllerRef.current = controller;
    setCancelPending(true);
    setCancelNotice("");
    setCancelError("");
    try {
      const response = await pipelineApi.cancelRun(token, selectedRun.id, selectedRun.revision, controller.signal);
      if (controller.signal.aborted || selectionEpoch !== detailRequestRef.current) return;
      setSelectedRun(response);
      setRuns((existing) => updateRunInList(existing, response));
      setCancelNotice(response.state === "cancelled" ? copy.cancelQueued : copy.cancelRequested);
    } catch (error) {
      if (controller.signal.aborted || selectionEpoch !== detailRequestRef.current) return;
      if (error instanceof PipelineApiError && error.status === 401) {
        session.invalidateIfCurrent(token, generation);
      }
      setCancelError(errorMessage(error, locale, copy.unknownError));
      if (error instanceof PipelineApiError && error.status === 409) {
        setDetailRefresh((value) => value + 1);
      }
    } finally {
      if (cancelControllerRef.current === controller) cancelControllerRef.current = null;
      if (selectionEpoch === detailRequestRef.current) setCancelPending(false);
    }
  };

  const stateLabel = (state: string): string => (copy.runStates as Record<string, string>)[state] ?? state;
  const statePill = (state: string, compact = false) => (
    <span className={`console-pill ${stateTone(state)} ${compact ? "pipeline-state-pill--compact" : ""}`}>
      <span className="pipeline-state-pill__dot" aria-hidden="true" />
      {stateLabel(state)}
    </span>
  );

  const eventLabel = (event: PipelineRunEvent): string => {
    const labels: Record<PipelineRunEvent["event_type"], string> = {
      created: copy.eventCreated,
      state_changed: copy.eventState,
      progress: copy.eventProgress,
      step_changed: copy.eventStep,
      cancellation_requested: copy.eventCancelRequested,
      cancelled: copy.eventCancelled,
      interrupted: copy.eventInterrupted,
    };
    return labels[event.event_type];
  };

  return (
    <section className="workspace-page workspace-page--wide console-view-enter pipeline-workspace" aria-labelledby="pipeline-title" data-testid="pipeline-workspace">
      <header className="console-page-header pipeline-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><Workflow aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="pipeline-title" className="console-page-header__title">{copy.title}</h1>
            <p className="console-page-header__subtitle">{copy.subtitle}</p>
          </div>
        </div>
        <div className="console-page-header__actions pipeline-page-header__actions">
          <span
            className={`console-chip pipeline-connection-chip ${session.status === "connected" ? "is-connected" : ""}`}
            role="status"
            aria-label={session.status === "connected" ? (session.canExecute ? copy.connectedFull : copy.readOnly) : copy.notConnectedFull}
          >
            {session.status === "connecting" ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : session.status === "connected" ? <ShieldCheck aria-hidden="true" /> : <LockKeyhole aria-hidden="true" />}
            {session.status === "connecting" ? copy.connecting : session.status === "connected" ? (session.canExecute ? copy.connected : copy.readOnly) : copy.notConnected}
          </span>
          {token ? (
            <button type="button" className="console-btn pipeline-control-button" onClick={handleDisconnect}>
              <LockKeyhole aria-hidden="true" />{copy.disconnect}
            </button>
          ) : (
            <button type="button" className="console-btn pipeline-control-button" onClick={() => { setConnectError(""); setConnectDialogOpen(true); }}>
              <LockKeyhole aria-hidden="true" />{copy.connect}
            </button>
          )}
          <button
            type="button"
            className="console-btn console-btn--primary pipeline-control-button"
            onClick={() => { setStageError(""); setSelectedTickers([]); setStageDialogOpen(true); }}
            disabled={!definition || !token || !session.canExecute || stagePending}
            title={!session.canExecute ? copy.executionDisabled : undefined}
          >
            <Play aria-hidden="true" />{copy.stageRun}
          </button>
        </div>
      </header>

      {!session.canExecute && token && (
        <div className="pipeline-policy-note" role="status"><LockKeyhole aria-hidden="true" />{copy.executionDisabled}</div>
      )}
      {notice && <div className="workspace-alert pipeline-notice" role="status"><Check aria-hidden="true" />{notice}</div>}

      <div className="console-layout console-layout--pipeline pipeline-console-layout">
        <div className="console-layout__main pipeline-main-column">
          <div className="console-stats pipeline-metrics" aria-label={locale === "vi" ? "Số liệu pipeline" : "Pipeline metrics"}>
            {[
              { icon: <FileStack aria-hidden="true" />, value: definition ? definition.registered_input_ids.length.toLocaleString(locale === "vi" ? "vi-VN" : "en-US") : "—", label: copy.metrics[0], hint: "GET /pipeline" },
              { icon: <Workflow aria-hidden="true" />, value: definition ? String(definition.stages.length) : "—", label: copy.metrics[1], hint: "GET /pipeline" },
              { icon: <Layers3 aria-hidden="true" />, value: definition ? String(definition.staging_profiles.length) : "—", label: copy.metrics[2], hint: "GET /pipeline" },
              { icon: <Activity aria-hidden="true" />, value: totalRuns === null ? "—" : totalRuns.toLocaleString(locale === "vi" ? "vi-VN" : "en-US"), label: copy.metrics[3], hint: token ? "GET /pipeline/runs · total" : copy.connectForRuns },
            ].map((metric) => (
              <div className="console-stat pipeline-metric" key={metric.label}>
                <div className="console-stat__icon">{metric.icon}</div>
                <div className="min-w-0">
                  <div className="console-stat__value">{metric.value}</div>
                  <div className="console-stat__label">{metric.label}</div>
                  <div className="console-stat__hint">{metric.hint}</div>
                </div>
              </div>
            ))}
          </div>

          <section className="console-card pipeline-flow-card" aria-labelledby="pipeline-stages-title">
            <div className="console-card__header">
              <div className="min-w-0">
                <h2 id="pipeline-stages-title" className="console-card__title">{copy.stages}</h2>
                <p className="console-card__subtitle">{copy.stagesSubtitle}</p>
              </div>
              <span className="console-pill console-pill--info"><ShieldCheck aria-hidden="true" />{copy.stagingOnly}</span>
            </div>
            {definitionState === "loading" && !definition && (
              <div className="pipeline-inline-state" role="status"><LoaderCircle className="animate-spin" aria-hidden="true" />{copy.definitionLoading}</div>
            )}
            {definitionState === "error" && (
              <div className="pipeline-inline-state pipeline-inline-state--error" role="alert"><AlertTriangle aria-hidden="true" />{definitionError}</div>
            )}
            {definition && (
              <div className="console-card__body pipeline-flow-body">
                <div className="pipeline-flow-track" role="region" tabIndex={0} aria-label={locale === "vi" ? "Thứ tự các bước staging" : "Staging step order"}>
                  {definition.stages.map((stage, index) => {
                    const step = selectedRun?.steps.find((candidate) => candidate.stage_id === stage.stage_id);
                    const stageName = (copy.stageNames as Record<string, string>)[stage.stage_id] ?? stage.stage_id;
                    const Icon = stage.stage_id === "download_filings" ? ArrowDownToLine
                      : stage.stage_id === "chunk_filings" ? FileStack
                        : stage.stage_id === "add_table_chunks" ? TableProperties
                          : stage.stage_id === "embed_chunks" ? Layers3
                            : Database;
                    return (
                      <div className="pipeline-flow-item" key={stage.stage_id}>
                        <article className={`pipeline-stage-node ${step ? `is-${step.state}` : ""}`} data-testid={`pipeline-stage-${stage.stage_id}`}>
                          <div className="pipeline-stage-node__top">
                            <span className="pipeline-stage-node__icon"><Icon aria-hidden="true" /></span>
                            <span className="pipeline-stage-node__order">{String(index + 1).padStart(2, "0")}</span>
                          </div>
                          <h3>{stageName}</h3>
                          <p>{stage.description}</p>
                          {step ? statePill(step.state, true) : <span className="pipeline-stage-node__order-label">{locale === "vi" ? `Bước ${index + 1}` : `Step ${index + 1}`}</span>}
                        </article>
                        {index < definition.stages.length - 1 && <ArrowRight className="pipeline-flow-arrow" aria-hidden="true" />}
                      </div>
                    );
                  })}
                </div>
                <p className="pipeline-flow-note"><ShieldCheck aria-hidden="true" />{copy.stageSafeNote}</p>
              </div>
            )}
          </section>

          <section className="console-card pipeline-history-card" aria-labelledby="pipeline-history-title">
            <div className="console-card__header pipeline-history-header">
              <div className="min-w-0">
                <h2 id="pipeline-history-title" className="console-card__title">{copy.history}</h2>
                <p className="console-card__subtitle">{copy.historySubtitle}</p>
              </div>
              <div className="pipeline-history-controls">
                <label className="pipeline-search-field">
                  <Search aria-hidden="true" />
                  <span className="sr-only">{copy.searchRuns}</span>
                  <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={copy.searchRuns} aria-label={copy.searchRuns} />
                </label>
                <label className="pipeline-filter-field">
                  <span className="sr-only">{copy.colState}</span>
                  <select
                    value={stateFilter}
                    aria-label={copy.colState}
                    onChange={(event) => { setPage(1); setStateFilter(event.target.value as PipelineFilter); }}
                  >
                    <option value="all">{copy.allStates}</option>
                    {RUN_STATES.map((state) => <option key={state} value={state}>{stateLabel(state)}</option>)}
                  </select>
                </label>
                <button type="button" className="console-btn console-btn--icon pipeline-control-button" aria-label={copy.refresh} title={copy.refresh} onClick={refresh} disabled={listState === "loading" || definitionState === "loading"}>
                  <RefreshCw className={listState === "loading" || definitionState === "loading" ? "animate-spin" : ""} aria-hidden="true" />
                </button>
              </div>
            </div>

            {token && listState === "loading" && <div className="pipeline-inline-state" role="status"><LoaderCircle className="animate-spin" aria-hidden="true" />{copy.loadingRuns}</div>}
            {token && listState === "error" && (
              <div className="pipeline-inline-state pipeline-inline-state--error" role="alert">
                <AlertTriangle aria-hidden="true" /><span>{listError || copy.listUnavailable}</span>
                <button type="button" className="console-btn pipeline-control-button" onClick={() => setListRefresh((value) => value + 1)}>{copy.retry}</button>
              </div>
            )}
            {!token && (
              <div className="pipeline-history-empty pipeline-history-empty--connect">
                <div className="pipeline-empty-icon"><LockKeyhole aria-hidden="true" /></div>
                <h3>{copy.connectForRuns}</h3>
                <p>{copy.connectForRunsBody}</p>
                <button type="button" className="console-btn console-btn--accent pipeline-control-button" onClick={() => { setConnectError(""); setConnectDialogOpen(true); }}>
                  <LockKeyhole aria-hidden="true" />{copy.connect}
                </button>
              </div>
            )}
            {token && listState === "ready" && totalRuns === 0 && !search && (
              <div className="pipeline-history-empty">
                <div className="pipeline-empty-icon"><Workflow aria-hidden="true" /></div>
                <h3>{copy.emptyRuns}</h3>
                <p>{copy.emptyRunsBody}</p>
                <button type="button" className="console-btn console-btn--primary pipeline-control-button" disabled={!session.canExecute} onClick={() => setStageDialogOpen(true)}>
                  <Play aria-hidden="true" />{copy.stageRun}
                </button>
              </div>
            )}
            {token && listState === "ready" && totalRuns !== 0 && (
              <>
                <div className="console-table-wrap pipeline-table-wrap" role="region" aria-label={copy.history} tabIndex={0}>
                  <table className="console-table pipeline-table">
                    <thead>
                      <tr><th scope="col">{copy.colRun}</th><th scope="col">{copy.colInput}</th><th scope="col">{copy.colCreated}</th><th scope="col">{copy.colState}</th></tr>
                    </thead>
                    <tbody>
                      {visibleRuns.map((run) => (
                        <tr key={run.id} className={selectedRunId === run.id ? "is-selected" : ""}>
                          <td className="pipeline-table__run" data-label={copy.colRun}>
                            <button type="button" className="pipeline-run-link" onClick={() => selectRun(run.id)} aria-current={selectedRunId === run.id ? "true" : undefined} aria-label={`${copy.selectRun} ${run.id}`}>
                              <span className="pipeline-run-link__icon"><Workflow aria-hidden="true" /></span>
                              <span>{run.id}</span>
                            </button>
                          </td>
                          <td data-label={copy.colInput}><div className="pipeline-input-pills">{run.input_ids.map((ticker) => <span className="pipeline-input-chip" key={ticker}>{ticker}</span>)}</div></td>
                          <td data-label={copy.colCreated}><time dateTime={run.created_at}>{formatDate(run.created_at, locale)}</time></td>
                          <td data-label={copy.colState}>{statePill(run.state)}</td>
                        </tr>
                      ))}
                      {visibleRuns.length === 0 && <tr><td className="pipeline-no-results" colSpan={4}>{copy.noSearchMatch}</td></tr>}
                    </tbody>
                  </table>
                </div>
                <div className="console-card__footer pipeline-history-footer">
                  <span>{interpolate(copy.resultCount, { count: totalRuns ?? 0 })}</span>
                  <div className="pipeline-pagination">
                    <button type="button" className="console-btn pipeline-control-button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1}>{copy.previous}</button>
                    <span aria-live="polite">{interpolate(copy.pageOf, { page, pages: totalPages })}</span>
                    <button type="button" className="console-btn pipeline-control-button" onClick={() => setPage((current) => Math.min(totalPages, current + 1))} disabled={page >= totalPages}>{copy.next}</button>
                  </div>
                </div>
              </>
            )}
          </section>
        </div>

        <aside className="console-layout__aside pipeline-detail-rail" aria-label={copy.details}>
          <section className="console-card pipeline-detail-card" aria-labelledby="pipeline-detail-title" data-testid="pipeline-run-detail">
            <div className="console-card__header pipeline-detail-header">
              <div className="min-w-0">
                <h2 id="pipeline-detail-title" className="console-card__title">{copy.details}</h2>
                <p className="console-card__subtitle">{selectedRunId ?? copy.selectRun}</p>
              </div>
              {selectedRunId && <button type="button" className="console-btn console-btn--ghost console-btn--icon pipeline-control-button" aria-label={copy.close} title={copy.close} onClick={onClearSelectedRun}><X aria-hidden="true" /></button>}
            </div>
            {!selectedRunId && (
              <div className="pipeline-detail-empty">
                <div className="pipeline-empty-icon"><CircleHelp aria-hidden="true" /></div>
                <p>{copy.detailsPrompt}</p>
              </div>
            )}
            {selectedRunId && !token && (
              <div className="pipeline-detail-empty">
                <div className="pipeline-empty-icon"><LockKeyhole aria-hidden="true" /></div>
                <p>{copy.detailDisconnected}</p>
                <button type="button" className="console-btn console-btn--accent pipeline-control-button" onClick={() => setConnectDialogOpen(true)}>{copy.connect}</button>
              </div>
            )}
            {selectedRunId && token && detailState === "loading" && (
              <div className="pipeline-inline-state" role="status"><LoaderCircle className="animate-spin" aria-hidden="true" />{copy.loadingDetail}</div>
            )}
            {selectedRunId && token && detailState === "error" && (
              <div className="pipeline-inline-state pipeline-inline-state--error" role="alert">
                <AlertTriangle aria-hidden="true" /><span>{detailError || copy.detailUnavailable}</span>
                <button type="button" className="console-btn pipeline-control-button" onClick={() => setDetailRefresh((value) => value + 1)}>{copy.retry}</button>
              </div>
            )}
            {selectedRun && detailState === "ready" && (
              <div className="pipeline-detail-content">
                <div className="pipeline-detail-summary">
                  <div>{statePill(selectedRun.state)}<span className="pipeline-detail-revision">r{selectedRun.revision}</span></div>
                  <div className="pipeline-detail-inputs">
                    <FileStack aria-hidden="true" />
                    <span>{selectedRun.input_ids.join(", ") || "—"}</span>
                  </div>
                </div>

                <dl className="pipeline-detail-meta">
                  <div><dt>{copy.created}</dt><dd><time dateTime={selectedRun.created_at}>{formatDate(selectedRun.created_at, locale)}</time></dd></div>
                  <div><dt>{copy.updated}</dt><dd><time dateTime={selectedRun.updated_at}>{formatDate(selectedRun.updated_at, locale)}</time></dd></div>
                  {selectedRun.started_at && <div><dt>{copy.started}</dt><dd><time dateTime={selectedRun.started_at}>{formatDate(selectedRun.started_at, locale)}</time></dd></div>}
                  {selectedRun.finished_at && <div><dt>{copy.finished}</dt><dd><time dateTime={selectedRun.finished_at}>{formatDate(selectedRun.finished_at, locale)}</time></dd></div>}
                  <div><dt>{copy.stagingProfile}</dt><dd>{selectedRun.staging_profile === "isolated" ? copy.isolated : selectedRun.staging_profile}</dd></div>
                  <div className="pipeline-detail-meta__fingerprint"><dt>{copy.configuration}</dt><dd title={selectedRun.configuration_fingerprint}>{selectedRun.configuration_fingerprint.slice(0, 16)}…</dd></div>
                </dl>

                <div className="pipeline-progress-block">
                  <div className="pipeline-section-heading"><h3>{copy.progress}</h3><span>{selectedRun.progress.current !== null && selectedRun.progress.total !== null ? `${selectedRun.progress.current} / ${selectedRun.progress.total}` : copy.progressUnknown}</span></div>
                  {selectedRun.progress.stage && <p>{(copy.stageNames as Record<string, string>)[selectedRun.progress.stage] ?? selectedRun.progress.stage}</p>}
                  {selectedRun.progress.current !== null && selectedRun.progress.total !== null && (
                    <progress max={selectedRun.progress.total} value={selectedRun.progress.current} aria-label={copy.progress} />
                  )}
                </div>

                <div className="pipeline-steps-block">
                  <div className="pipeline-section-heading"><h3>{copy.steps}</h3><span>{selectedRun.steps.length}</span></div>
                  <ol className="pipeline-step-list">
                    {selectedRun.steps.map((step: PipelineStep, index) => (
                      <li key={step.step_id} className={`pipeline-step-item is-${step.state}`}>
                        <span className="pipeline-step-marker" aria-hidden="true">{step.state === "succeeded" ? <Check /> : step.state === "running" ? <LoaderCircle className="animate-spin" /> : <span>{index + 1}</span>}</span>
                        <div className="pipeline-step-copy">
                          <div className="pipeline-step-name">{(copy.stageNames as Record<string, string>)[step.stage_id] ?? step.stage_id}</div>
                          <div>{stateLabel(step.state)}</div>
                        </div>
                        <span className="pipeline-step-revision">r{step.revision}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                {selectedRun.failure && <div className="pipeline-failure" role="alert"><AlertTriangle aria-hidden="true" /><div><strong>{selectedRun.failure.code}</strong><p>{selectedRun.failure.message}</p></div></div>}
                {selectedRun.artifact_references.length > 0 ? (
                  <div className="pipeline-artifacts"><h3>{copy.artifactReferences}</h3><ul>{selectedRun.artifact_references.map((reference) => <li key={reference}>{reference}</li>)}</ul></div>
                ) : <p className="pipeline-no-artifacts"><Database aria-hidden="true" />{copy.noArtifacts}</p>}

                <div className="pipeline-detail-actions">
                  {showCancel && <button type="button" className="console-btn pipeline-control-button pipeline-cancel-button" onClick={() => void handleCancel()} disabled={cancelPending}><Square aria-hidden="true" />{cancelPending ? copy.cancelling : copy.cancel}</button>}
                  {!session.canExecute && (selectedRun.state === "queued" || selectedRun.state === "running") && <p className="pipeline-action-note"><LockKeyhole aria-hidden="true" />{copy.cancelUnavailable}</p>}
                  {cancelError && <p className="pipeline-action-error" role="alert">{cancelError}</p>}
                  {cancelNotice && <p className="pipeline-action-note" role="status">{cancelNotice}</p>}
                </div>
                <p className="pipeline-stage-safety-note"><ShieldCheck aria-hidden="true" />{copy.stageDoesNotRun}</p>

                <div className="pipeline-event-block">
                  <div className="pipeline-section-heading"><h3>{copy.recentEvents}</h3><span>{streamStatus === "connecting" ? copy.updatesConnecting : streamStatus === "complete" ? copy.updatesComplete : streamStatus === "error" ? copy.updatesUnavailable : interpolate(copy.updatesWaiting, { sequence: eventCursor })}</span></div>
                  {streamError && <p className="pipeline-stream-error" role="status">{streamError}</p>}
                  {events.length === 0 ? <p className="pipeline-no-events">{copy.noEvents}</p> : (
                    <ol className="pipeline-event-list">
                      {events.slice(-5).reverse().map((event) => (
                        <li key={event.event_id}>
                          <span className="pipeline-event-sequence">#{event.sequence}</span>
                          <div><strong>{eventLabel(event)}</strong>{event.reason_code && <span>{copy.reason}: {event.reason_code}</span>}<time dateTime={event.occurred_at}>{formatDate(event.occurred_at, locale)}</time></div>
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              </div>
            )}
          </section>
        </aside>
      </div>

      <ModalDialog
        open={connectDialogOpen}
        onClose={() => { if (session.status !== "connecting") { setConnectDialogOpen(false); setTokenDraft(""); setConnectError(""); } }}
        ariaLabel={copy.connectTitle}
        initialFocusRef={tokenInputRef}
        className="pipeline-dialog"
      >
        <form className="pipeline-dialog-form" onSubmit={(event) => void handleConnect(event)}>
          <div className="pipeline-dialog__header">
            <div><div className="pipeline-dialog__icon"><LockKeyhole aria-hidden="true" /></div><h2>{copy.connectTitle}</h2></div>
            <button type="button" className="pipeline-dialog__close" aria-label={copy.close} onClick={() => { setConnectDialogOpen(false); setTokenDraft(""); setConnectError(""); }} disabled={session.status === "connecting"}><X aria-hidden="true" /></button>
          </div>
          <p className="pipeline-dialog__description">{copy.connectDescription}</p>
          <label className="pipeline-form-label" htmlFor="pipeline-local-token">{copy.tokenLabel}</label>
          <input
            ref={tokenInputRef}
            id="pipeline-local-token"
            type="password"
            autoComplete="off"
            value={tokenDraft}
            onChange={(event) => setTokenDraft(event.target.value)}
            placeholder={copy.tokenPlaceholder}
            className="pipeline-text-input"
            autoCapitalize="off"
            spellCheck={false}
          />
          <p className="pipeline-form-hint"><ShieldCheck aria-hidden="true" />{copy.tokenSafety}</p>
          {connectError && <p className="pipeline-form-error" role="alert">{connectError}</p>}
          <div className="pipeline-dialog__actions">
            <button type="button" className="console-btn pipeline-control-button" onClick={() => { setConnectDialogOpen(false); setTokenDraft(""); setConnectError(""); }} disabled={session.status === "connecting"}>{copy.close}</button>
            <button type="submit" className="console-btn console-btn--primary pipeline-control-button" disabled={!tokenDraft.trim() || session.status === "connecting"}>
              {session.status === "connecting" ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <LockKeyhole aria-hidden="true" />}
              {session.status === "connecting" ? copy.connecting : copy.verifyConnect}
            </button>
          </div>
        </form>
      </ModalDialog>

      <ModalDialog
        open={stageDialogOpen}
        onClose={() => { if (!stagePending) { setStageDialogOpen(false); setStageError(""); } }}
        ariaLabel={copy.stageTitle}
        initialFocusRef={stageInputRef}
        className="pipeline-dialog pipeline-dialog--stage"
      >
        <form className="pipeline-dialog-form" onSubmit={(event) => void handleStage(event)}>
          <div className="pipeline-dialog__header">
            <div><div className="pipeline-dialog__icon"><Play aria-hidden="true" /></div><h2>{copy.stageTitle}</h2></div>
            <button type="button" className="pipeline-dialog__close" aria-label={copy.close} onClick={() => setStageDialogOpen(false)} disabled={stagePending}><X aria-hidden="true" /></button>
          </div>
          <p className="pipeline-dialog__description">{copy.stageDescription}</p>
          <label className="pipeline-form-label" htmlFor="pipeline-ticker-search">{copy.tickerSearch}</label>
          <div className="pipeline-search-field pipeline-ticker-search">
            <Search aria-hidden="true" />
            <input ref={stageInputRef} id="pipeline-ticker-search" type="search" value={tickerSearch} onChange={(event) => setTickerSearch(event.target.value.toLocaleUpperCase())} placeholder={copy.tickerSearch} />
          </div>
          <div className="pipeline-ticker-tools">
            <span>{interpolate(copy.selectedInputs, { count: selectedTickers.length })}</span>
            <button type="button" className="pipeline-text-action" onClick={() => setSelectedTickers((selected) => [...new Set([...selected, ...filteredTickers])])} disabled={filteredTickers.length === 0}>{copy.selectVisible}</button>
            <button type="button" className="pipeline-text-action" onClick={() => setSelectedTickers([])} disabled={selectedTickers.length === 0}>{copy.clearSelection}</button>
          </div>
          <div className="pipeline-ticker-list" role="group" aria-label={copy.tickerSearch}>
            {filteredTickers.map((ticker) => (
              <label className="pipeline-ticker-option" key={ticker}>
                <input
                  type="checkbox"
                  checked={selectedTickers.includes(ticker)}
                  onChange={(event) => setSelectedTickers((selected) => event.target.checked
                    ? [...selected, ticker]
                    : selected.filter((entry) => entry !== ticker))}
                  disabled={stagePending}
                />
                <span>{ticker}</span>
              </label>
            ))}
          </div>
          <div className="pipeline-profile-row"><span>{copy.profile}</span><span className="console-pill console-pill--info">{copy.isolated}</span></div>
          <p className="pipeline-form-hint"><ShieldCheck aria-hidden="true" />{copy.stageSafeNote}</p>
          {stageError && <p className="pipeline-form-error" role="alert">{stageError}</p>}
          {!session.canExecute && <p className="pipeline-form-error" role="alert">{copy.executionDisabled}</p>}
          <div className="pipeline-dialog__actions">
            <button type="button" className="console-btn pipeline-control-button" onClick={() => setStageDialogOpen(false)} disabled={stagePending}>{copy.close}</button>
            <button type="submit" className="console-btn console-btn--primary pipeline-control-button" disabled={stagePending || selectedTickers.length === 0 || !session.canExecute}>
              {stagePending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
              {stagePending ? copy.submittingStage : copy.submitStage}
            </button>
          </div>
          {selectedTickers.length === 0 && <p className="pipeline-input-required" role="status">{copy.inputRequired}</p>}
        </form>
      </ModalDialog>
    </section>
  );
}
