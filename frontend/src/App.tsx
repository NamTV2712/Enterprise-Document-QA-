/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  lazy,
  Suspense,
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
  type CSSProperties,
} from "react";
import { AlertTriangle, BookMarked, ChevronDown, RefreshCw, X } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ChatInput } from "./components/ChatInput";
import { TemplateQuestionDialog } from "./components/TemplateQuestionDialog";
import { SampleQuestion, SampleQuestionChips } from "./components/SampleQuestionChips";
import { OverviewPanel } from "./components/OverviewPanel";
import { WorkspaceHeader } from "./components/WorkspaceHeader";
import { ConversationLibrary } from "./components/ConversationLibrary";
import { HelpDialog } from "./components/HelpDialog";
import { ModalDialog } from "./components/ui/ModalDialog";
import { CommandPalette, PaletteView } from "./components/CommandPalette";
import { EvidenceWorkspaceRail } from "./components/EvidenceWorkspaceRail";
import {
  HealthResponse,
  RequestSnapshot,
  ThemePreference,
  AnswerVariant,
  DisplayedAnswerContext,
  EvidenceSelection,
  Message,
  MessageFeedback,
  Source,
  StageEvent,
} from "./types";
import {
  checkHealth,
  getSupportedTickers,
  queryDecomposed,
  streamQuery,
  streamDecomposedQuery,
} from "./lib/api";
import { formatCompanyLabel, SECTION_METADATA } from "./lib/displayMetadata";
import { ConversationRecord } from "./lib/conversationStore";
import { saveConversationRecord } from "./lib/conversationStore";
import {
  downloadConversationBackup,
  downloadConversationMarkdown,
} from "./lib/conversationExport";
import type { ConversationBackupBundle } from "./lib/conversationExport";
import { useConversationLibrary, SessionContextStatus } from "./hooks/useConversationLibrary";
import { useResearchDraft } from "./hooks/useResearchDraft";
import type { ResearchScope } from "./hooks/useResearchDraft";
import { useNavigationLayout } from "./hooks/useNavigationLayout";
import { useEvidenceSelection } from "./hooks/useEvidenceSelection";
import { useResearchSession } from "./hooks/useResearchSession";
import { useLocale, type Locale } from "./lib/i18n";
import { recordAnalyticsEvent } from "./lib/analyticsStore";
import { getResearchTemplateCopy, isSendableResearchQuestion, RESEARCH_TEMPLATES, type ResearchTemplate, type ResearchTemplateApplyPayload } from "./lib/researchTemplates";
import { mergeEvidenceCollections, saveEvidence } from "./lib/evidenceCollections";
import type { ContextualCommandDefinition } from "./lib/commandRegistry";
import { isWorkspaceView } from "./lib/workspace";
import { getWorkspaceNavItem, type WorkspaceView } from "./lib/workspace";
import { getSemanticIcon } from "./lib/semanticIcons";
import { describeRequestError } from "./lib/requestError";
import { createEvidenceSelection, getSourceKey, sourceMatchesSelection } from "./lib/sourceIdentity";
import { appendStageEvent, isStageEvent } from "./lib/stageEvents";

const STREAM_FLUSH_INTERVAL_MS = 80;
const HEALTH_REFRESH_INTERVAL_MS = 15_000;
const CONTEXT_RAIL_MIN_WIDTH = 360;
const CONTEXT_RAIL_MAX_WIDTH = 560;
const CONTEXT_INLINE_MIN_WORKSPACE_WIDTH = 888;
const CONTEXT_RAIL_STORAGE_KEY = "sec_qa_context_rail_width_v1";
const NAVIGATION_DESKTOP_MIN_WIDTH = 1024;
const COMPARATIVE_KEYWORDS = [
  "compare",
  "vs",
  "versus",
  "both",
  "which company",
  "between",
];

const ChatMessage = lazy(() =>
  import("./components/ChatMessage").then(({ ChatMessage }) => ({
    default: ChatMessage,
  })),
);

// Secondary workspaces are route-level panels. Keep the initial chat shell
// small and load diagnostics only when the user opens that workspace.
const RetrievalLabPanel = lazy(() =>
  import("./components/RetrievalLabPanel").then(({ RetrievalLabPanel }) => ({ default: RetrievalLabPanel })),
);
const DocumentExplorerPanel = lazy(() =>
  import("./components/DocumentExplorerPanel").then(({ DocumentExplorerPanel }) => ({ default: DocumentExplorerPanel })),
);
const SystemInfoPanel = lazy(() =>
  import("./components/SystemInfoPanel").then(({ SystemInfoPanel }) => ({ default: SystemInfoPanel })),
);
const EvaluationPanel = lazy(() =>
  import("./components/EvaluationPanel").then(({ EvaluationPanel }) => ({ default: EvaluationPanel })),
);
const AnalyticsPanel = lazy(() =>
  import("./components/AnalyticsPanel").then(({ AnalyticsPanel }) => ({ default: AnalyticsPanel })),
);
const SearchWorkspace = lazy(() =>
  import("./components/SearchWorkspace").then(({ SearchWorkspace }) => ({ default: SearchWorkspace })),
);
const ArchitecturePanel = lazy(() =>
  import("./components/ArchitecturePanel").then(({ ArchitecturePanel }) => ({ default: ArchitecturePanel })),
);

function WorkspacePanelFallback() {
  return (
    <div className="mx-auto flex w-full max-w-6xl items-center gap-2 px-3 py-8 text-sm text-[var(--text-muted)] md:px-6" role="status">
      <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]" />
      Loading workspace…
    </div>
  );
}

function isComparativeQuery(question: string): boolean {
  const lower = question.toLowerCase();
  return COMPARATIVE_KEYWORDS.some((keyword) => lower.includes(keyword));
}

function getSystemTheme(): "light" | "dark" {
  return typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function readContextRailWidth(): number {
  try {
    const parsed = Number(localStorage.getItem(CONTEXT_RAIL_STORAGE_KEY));
    if (Number.isFinite(parsed)) return Math.min(CONTEXT_RAIL_MAX_WIDTH, Math.max(CONTEXT_RAIL_MIN_WIDTH, Math.round(parsed)));
  } catch {
    // Layout preference is optional and must never block the workspace.
  }
  return 384;
}

function readInitialWorkspaceWidth(isDesktopNavigation: boolean, navigationLayout: string): number {
  if (typeof window === "undefined") return 0;
  const navigationWidth = !isDesktopNavigation ? 0 : navigationLayout === "compact" ? 56 : 216;
  return Math.max(0, window.innerWidth - navigationWidth);
}

function scopeFromRequestSnapshot(snapshot: RequestSnapshot): ResearchScope {
  return {
    ticker: snapshot.ticker,
    section: snapshot.section,
    topK: snapshot.topK,
    enableComparative: snapshot.enableComparative,
  };
}

interface TemplateOpeningSnapshot {
  conversationId: string;
  draft: string;
  locale: Locale;
  scope: ResearchScope;
  templateId: ResearchTemplate["id"];
}

function scopesMatch(left: ResearchScope, right: ResearchScope): boolean {
  return left.ticker === right.ticker &&
    left.section === right.section &&
    left.topK === right.topK &&
    left.enableComparative === right.enableComparative;
}

interface DisplayedAnswerTarget {
  message: Message;
  variant: AnswerVariant | null;
  text: string;
  sources: Source[];
}

export interface CommandEvidenceTarget {
  selection: EvidenceSelection;
  source: Source;
}

function isUsableGroundedAnswer(message: Message): boolean {
  return message.sender === "assistant" &&
    !message.isStreaming &&
    !message.error &&
    message.status !== "error" &&
    Boolean(message.text.trim());
}

/** Resolve an answer by durable IDs, never by position or recency when context is present. */
export function resolveDisplayedAnswerTarget(
  context: DisplayedAnswerContext | null,
  messages: Message[],
  record: ConversationRecord | null,
  conversationId: string,
): DisplayedAnswerTarget | null {
  if (context && context.conversationId !== conversationId) return null;
  const message = context
    ? messages.find((candidate) => candidate.id === context.messageId)
    : [...messages].reverse().find(isUsableGroundedAnswer);
  if (!message || !isUsableGroundedAnswer(message)) return null;

  if (context?.variantId !== null && context?.variantId !== undefined) {
    const variant = record?.variants?.find((candidate) =>
      candidate.id === context.variantId &&
      candidate.originMessageId === message.id &&
      candidate.status !== "error" &&
      Boolean(candidate.text.trim()),
    );
    if (!variant) return null;
    return { message, variant, text: variant.text, sources: variant.sources };
  }

  return { message, variant: null, text: message.text, sources: message.sources ?? [] };
}

/** Resolve the source command target against current records at invocation time. */
export function resolveEvidenceCommandTarget(
  context: DisplayedAnswerContext | null,
  evidenceSelection: EvidenceSelection | null,
  messages: Message[],
  record: ConversationRecord | null,
  conversationId: string,
): CommandEvidenceTarget | null {
  const displayed = resolveDisplayedAnswerTarget(context, messages, record, conversationId);
  const selectionMatchesDisplayed = Boolean(
    context &&
    evidenceSelection &&
    evidenceSelection.conversationId === context.conversationId &&
    evidenceSelection.messageId === context.messageId &&
    (evidenceSelection.variantId ?? null) === context.variantId,
  );

  if (displayed && context && !selectionMatchesDisplayed) {
    const source = displayed.sources[0];
    return source
      ? {
          source,
          selection: createEvidenceSelection(
            conversationId,
            displayed.message.id,
            0,
            source,
            displayed.variant?.id,
          ),
        }
      : null;
  }

  if (evidenceSelection) {
    if (evidenceSelection.conversationId !== conversationId) return null;
    const message = messages.find((candidate) => candidate.id === evidenceSelection.messageId);
    if (!message || message.sender !== "assistant" || message.isStreaming || message.error || message.status === "error") return null;
    const variant = evidenceSelection.variantId
      ? record?.variants?.find((candidate) =>
          candidate.id === evidenceSelection.variantId &&
          candidate.originMessageId === message.id &&
          candidate.status !== "error",
        )
      : null;
    if (evidenceSelection.variantId && !variant) return null;
    const sources = variant?.sources ?? message.sources ?? [];
    const source = sources[evidenceSelection.citationIndex];
    return source && sourceMatchesSelection(source, evidenceSelection, evidenceSelection.citationIndex)
      ? { source, selection: evidenceSelection }
      : null;
  }

  if (!displayed) return null;
  const source = displayed.sources[0];
  return source
    ? {
        source,
        selection: createEvidenceSelection(
          conversationId,
          displayed.message.id,
          0,
          source,
          displayed.variant?.id,
        ),
      }
    : null;
}

function scopeForConversationDraft(record: ConversationRecord | null): Partial<ResearchScope> | null {
  if (!record) return null;

  const draft = record.draft.trim();
  if (draft) {
    const matchingTemplate = RESEARCH_TEMPLATES.find((template) =>
      (["en", "vi"] as const).some(
        (locale) => getResearchTemplateCopy(template, locale).question === draft,
      ),
    );
    if (matchingTemplate) return matchingTemplate.scope;
  }

  const latestSnapshot = [...record.messages]
    .reverse()
    .find((message) => message.sender === "user" && message.requestSnapshot)?.requestSnapshot;
  return latestSnapshot ? scopeFromRequestSnapshot(latestSnapshot) : null;
}

function initialWorkspaceView(): WorkspaceView {
  if (typeof window === "undefined") return "overview";
  if (import.meta.env.MODE === "test") return "overview";
  const value = new URLSearchParams(window.location.search).get("view");
  return isWorkspaceView(value)
    ? value
    : "overview";
}

function evidenceAnchorMessageId(messageId: string): string {
  return messageId.replace(/[^a-zA-Z0-9_-]/g, "-");
}

function writeEvidenceAnchor(messageId: string, citationIndex: number): void {
  window.history.replaceState(
    window.history.state,
    "",
    `${window.location.pathname}${window.location.search}#evidence=${evidenceAnchorMessageId(messageId)}-${citationIndex}`,
  );
}

function clearEvidenceAnchor(): void {
  window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}`);
}

export default function App() {
  const { locale, t } = useLocale();
  const libraryNavItem = getWorkspaceNavItem("library");
  const LibraryIcon = getSemanticIcon(libraryNavItem.icon);
  const [tickers, setTickers] = useState<string[]>([]);
  const [sections, setSections] = useState<string[]>([]);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(
    null,
  );
  const [isPipelineReady, setIsPipelineReady] = useState<boolean | null>(null);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isClearingSession, setIsClearingSession] = useState<boolean>(false);
  const [showResetDialog, setShowResetDialog] = useState<boolean>(false);
  const [isHelpOpen, setIsHelpOpen] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [templateToCustomize, setTemplateToCustomize] = useState<ResearchTemplate | null>(null);
  const templateOpeningSnapshotRef = useRef<TemplateOpeningSnapshot | null>(null);
  const [contextualCommandNotice, setContextualCommandNotice] = useState<string | null>(null);
  const [displayedAnswerContext, setDisplayedAnswerContext] = useState<DisplayedAnswerContext | null>(null);
  const [activeView, setActiveView] = useState<WorkspaceView>(initialWorkspaceView);
  const [pendingFocusMessageId, setPendingFocusMessageId] = useState<string | null>(null);
  const [shouldFocusLibrarySearch, setShouldFocusLibrarySearch] = useState(false);
  const [activeSidebarPanel, setActiveSidebarPanel] = useState<"research" | "library">("research");
  const [stageEventsByMessage, setStageEventsByMessage] = useState<Record<string, StageEvent[]>>({});
  const [contextRailWidth, setContextRailWidth] = useState(readContextRailWidth);
  const [workspaceWidth, setWorkspaceWidth] = useState(0);
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(false);
  const [isScopeEditorOpen, setIsScopeEditorOpen] = useState(false);
  const [isDesktopNavigation, setIsDesktopNavigation] = useState(() =>
    typeof window === "undefined" || typeof window.matchMedia !== "function"
      ? true
      : window.matchMedia(`(min-width: ${NAVIGATION_DESKTOP_MIN_WIDTH}px)`).matches,
  );
  const { layout: navigationLayout, toggleLayout: toggleNavigationLayout } = useNavigationLayout();

  useEffect(() => {
    setWorkspaceWidth(readInitialWorkspaceWidth(isDesktopNavigation, navigationLayout));
  }, [isDesktopNavigation, navigationLayout]);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mediaQuery = window.matchMedia(`(min-width: ${NAVIGATION_DESKTOP_MIN_WIDTH}px)`);
    const syncNavigationMode = () => setIsDesktopNavigation(mediaQuery.matches);
    syncNavigationMode();
    mediaQuery.addEventListener?.("change", syncNavigationMode);
    return () => mediaQuery.removeEventListener?.("change", syncNavigationMode);
  }, []);

  useEffect(() => {
    // A drawer opened below the breakpoint must not remain logically open when
    // the same tab crosses into the inline desktop shell.
    if (isDesktopNavigation && isSidebarOpen) setIsSidebarOpen(false);
  }, [isDesktopNavigation, isSidebarOpen]);

  useEffect(() => {
    try {
      localStorage.setItem(CONTEXT_RAIL_STORAGE_KEY, String(contextRailWidth));
    } catch {
      // A blocked preference store does not affect citation reading.
    }
  }, [contextRailWidth]);

  // Theme state. Keep the preference separate from the resolved color so a
  // system preference can follow OS changes without overwriting user choice.
  const [themePreference, setThemePreference] = useState<ThemePreference>(() => {
    try {
      const saved = localStorage.getItem("theme");
      if (saved === "system" || saved === "light" || saved === "dark") {
        return saved;
      }
    } catch {
      // Storage may be unavailable; fall back to system.
    }
    return "system";
  });
  const [systemTheme, setSystemTheme] = useState<"light" | "dark">(
    getSystemTheme,
  );
  const resolvedTheme = themePreference === "system" ? systemTheme : themePreference;

  useEffect(() => {
    const handlePopState = () => setActiveView(initialWorkspaceView());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (import.meta.env.MODE === "test") return;
    const url = new URL(window.location.href);
    if (activeView === "overview") url.searchParams.delete("view");
    else url.searchParams.set("view", activeView);
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  }, [activeView]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const workspaceMainRef = useRef<HTMLElement>(null);
  const resetCancelRef = useRef<HTMLButtonElement>(null);
  const healthRequestRef = useRef<Promise<HealthResponse> | null>(null);
  const lastHealthRefreshRef = useRef(0);
  const [showScrollButton, setShowScrollButton] = useState<boolean>(false);
  const isNearConversationBottomRef = useRef(true);

  useEffect(() => {
    const element = workspaceMainRef.current;
    if (!element) return;
    const syncWorkspaceWidth = () => setWorkspaceWidth(element.clientWidth);
    syncWorkspaceWidth();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(syncWorkspaceWidth);
      observer.observe(element);
      return () => observer.disconnect();
    }
    window.addEventListener("resize", syncWorkspaceWidth);
    return () => window.removeEventListener("resize", syncWorkspaceWidth);
  }, [isDesktopNavigation, navigationLayout]);

  // Indirection so the library hook can trigger the cancel path (which
  // needs updateMessages) before that function is declared below.
  const cancelActiveRequestRef = useRef<() => void>(() => {});

  const library = useConversationLibrary({
    onCancelActiveRequest: () => cancelActiveRequestRef.current(),
  });
  const {
    conversations,
    activeRecord,
    messages,
    inputText,
    bookmarkedMessageIds,
    storageMode,
    storageWarning,
    isLibraryReady,
    saveIndicator,
    sessionContext,
    isReadOnly,
    isPreflightRunning,
    setInputText,
    updateMessages,
    beginSend,
    ensureSendable,
    finishSend,
    isIdentityActive,
    registerBackendExchange,
    selectConversation,
    startNewConversation,
    renameConversation,
    toggleAnswerBookmark,
    deleteConversation,
    importConversationRecords,
    recheckSessionContext,
    writerStatus,
    requestLibraryWriter,
    updateConversationMetadata,
  } = library;
  const activeConversationId = library.activeConversationId;
  const inputTextRef = useRef(inputText);
  inputTextRef.current = inputText;
  const displayedAnswerContextRef = useRef<DisplayedAnswerContext | null>(null);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const activeRecordRef = useRef(activeRecord);
  activeRecordRef.current = activeRecord;
  const activeConversationIdRef = useRef(activeConversationId);
  activeConversationIdRef.current = activeConversationId;
  const handleDisplayedAnswerContext = useCallback(
    ({ messageId, variantId }: { messageId: string; variantId: string | null }) => {
      const nextContext = { conversationId: activeConversationId, messageId, variantId };
      displayedAnswerContextRef.current = nextContext;
      setDisplayedAnswerContext(nextContext);
    },
    [activeConversationId],
  );
  const previousScopeRef = useRef<ResearchScope | null>(null);
  const draftScopeFallback = useMemo(
    () => scopeForConversationDraft(activeRecord) ?? previousScopeRef.current ?? {},
    [activeRecord],
  );
  const {
    scope: { ticker: selectedTicker, section: selectedSection, topK, enableComparative },
    patchScope,
    setTicker: setSelectedTicker,
    setSection: setSelectedSection,
    setTopK,
    setEnableComparative,
  } = useResearchDraft(activeConversationId, draftScopeFallback, isLibraryReady);
  previousScopeRef.current = { ticker: selectedTicker, section: selectedSection, topK, enableComparative };
  const recentConversations = useMemo(
    () => conversations
      .filter((conversation) => conversation.messages.length > 0)
      .sort((left, right) => right.updatedAt - left.updatedAt)
      .slice(0, 3),
    [conversations],
  );
  const [evidenceSelection, setEvidenceSelection] = useEvidenceSelection(activeConversationId);
  const evidenceSelectionRef = useRef<EvidenceSelection | null>(evidenceSelection);
  evidenceSelectionRef.current = evidenceSelection;
  const evidenceReturnFocusRef = useRef<{ messageId: string; citationIndex: number } | null>(null);
  const evidenceFocusRestorePendingRef = useRef(false);
  const evidenceFocusRestoreTimeoutRef = useRef<number | null>(null);
  const clearEvidenceFocusRestoreTimer = useCallback(() => {
    if (evidenceFocusRestoreTimeoutRef.current !== null) {
      window.clearTimeout(evidenceFocusRestoreTimeoutRef.current);
      evidenceFocusRestoreTimeoutRef.current = null;
    }
  }, []);
  const cancelEvidenceFocusRestore = useCallback(() => {
    clearEvidenceFocusRestoreTimer();
    evidenceFocusRestorePendingRef.current = false;
  }, [clearEvidenceFocusRestoreTimer]);
  useEffect(() => {
    setIsEvidenceOpen(false);
  }, [activeConversationId]);
  useEffect(() => {
    displayedAnswerContextRef.current = null;
    setDisplayedAnswerContext(null);
  }, [activeConversationId]);
  useEffect(() => {
    if (!isLibraryReady || !window.location.hash) return;
    const match = window.location.hash.match(/^#evidence=([a-zA-Z0-9_-]+)-(\d+)$/);
    if (!match) return;
    const message = messages.find(
      (candidate) => evidenceAnchorMessageId(candidate.id) === match[1],
    );
    const citationIndex = Number(match[2]);
    const source = message?.sources?.[citationIndex];
    if (!message || !source || !Number.isInteger(citationIndex)) return;
    if (
      evidenceSelection?.messageId === message.id &&
      evidenceSelection.citationIndex === citationIndex &&
      evidenceSelection.sourceKey === getSourceKey(source)
    ) {
      setIsEvidenceOpen(true);
      return;
    }
    setActiveView("conversation");
    setEvidenceSelection(
      createEvidenceSelection(activeConversationId, message.id, citationIndex, source),
    );
    setIsEvidenceOpen(true);
  }, [activeConversationId, evidenceSelection, isLibraryReady, messages, setEvidenceSelection]);
  const handleInspectSource = useCallback(
    (selection: Omit<EvidenceSelection, "conversationId">) => {
      cancelEvidenceFocusRestore();
      evidenceReturnFocusRef.current = {
        messageId: selection.messageId,
        citationIndex: selection.citationIndex,
      };
      writeEvidenceAnchor(selection.messageId, selection.citationIndex);
      setEvidenceSelection({ conversationId: activeConversationId, ...selection });
      setIsEvidenceOpen(true);
    },
    [activeConversationId, cancelEvidenceFocusRestore, setEvidenceSelection],
  );
  const handleCloseEvidence = useCallback(() => {
    cancelEvidenceFocusRestore();
    evidenceFocusRestorePendingRef.current = true;
    clearEvidenceAnchor();
    setIsEvidenceOpen(false);
  }, [cancelEvidenceFocusRestore]);
  useEffect(() => {
    if (isEvidenceOpen || !evidenceFocusRestorePendingRef.current) return;
    evidenceFocusRestorePendingRef.current = false;
    const target = evidenceReturnFocusRef.current;
    let attempts = 0;
    let timeout: number | null = null;
    const restoreFocus = () => {
      const opener = target
        ? document.getElementById(`message-${target.messageId}`)
          ?.querySelector<HTMLButtonElement>(`button[aria-label="Open source ${target.citationIndex + 1}"]`)
        : null;
      if (opener && !opener.hasAttribute("disabled")) {
        opener.focus({ preventScroll: true });
      }
      if (attempts < 12) {
        attempts += 1;
        timeout = window.setTimeout(() => {
          evidenceFocusRestoreTimeoutRef.current = null;
          restoreFocus();
        }, 16);
        evidenceFocusRestoreTimeoutRef.current = timeout;
      }
    };
    const frame = window.requestAnimationFrame(restoreFocus);
    return () => {
      window.cancelAnimationFrame(frame);
      clearEvidenceFocusRestoreTimer();
    };
  }, [clearEvidenceFocusRestoreTimer, isEvidenceOpen]);
  const researchSession = useResearchSession({ updateMessages });
  const {
    isLoading,
    streamingBufferRef,
    beginRequest,
    isCurrentRequest: isCurrentResearchRequest,
    markRequestIdle,
    finishRequest,
    cancelActiveRequest,
    stopGenerating,
  } = researchSession;
  cancelActiveRequestRef.current = cancelActiveRequest;

  const applyHealth = useCallback((health: HealthResponse) => {
    lastHealthRefreshRef.current = Date.now();
    setHealthData(health);
    setIsBackendConnected(true);
    setIsPipelineReady(health.pipeline_ready);
  }, []);

  const refreshHealth = useCallback(
    async (force = false, signal?: AbortSignal): Promise<HealthResponse | null> => {
      const now = Date.now();
      if (
        !force &&
        lastHealthRefreshRef.current > 0 &&
        now - lastHealthRefreshRef.current < HEALTH_REFRESH_INTERVAL_MS
      ) {
        return null;
      }

      if (healthRequestRef.current) return healthRequestRef.current;

      const request = checkHealth(signal)
        .then((health) => {
          applyHealth(health);
          return health;
        })
        .finally(() => {
          healthRequestRef.current = null;
        });
      healthRequestRef.current = request;
      return request;
    },
    [applyHealth],
  );

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const updateSystemTheme = (event?: MediaQueryListEvent) => {
      setSystemTheme(event ? (event.matches ? "dark" : "light") : getSystemTheme());
    };
    updateSystemTheme();
    media.addEventListener?.("change", updateSystemTheme);
    return () => media.removeEventListener?.("change", updateSystemTheme);
  }, []);

  // Apply the resolved theme class and persist the preference.
  useEffect(() => {
    if (resolvedTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    try {
      localStorage.setItem("theme", themePreference);
    } catch {
      // Storage may be unavailable; theme still applies for this session.
    }
  }, [resolvedTheme, themePreference]);

  // Initialization: health and supported metadata only. Session context is
  // owned by the library hook after local hydration completes.
  useEffect(() => {
    const controller = new AbortController();

    const initData = async () => {
      try {
        const health = await checkHealth(controller.signal);
        applyHealth(health);
        const support = await getSupportedTickers(controller.signal);
        setTickers(support.tickers || []);
        setSections(support.sections || []);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        console.warn("FastAPI initialization check failed:", err);
        setIsBackendConnected(false);
        setIsPipelineReady(false);
      }
    };

    initData();
    return () => controller.abort();
  }, [applyHealth]);

  // Adopted backend history moves the user into the conversation view once.
  const historyAdoptedRef = useRef(false);
  useEffect(() => {
    if (!historyAdoptedRef.current && messages.length > 0 && isLibraryReady) {
      historyAdoptedRef.current = true;
      setActiveView("conversation");
    }
  }, [messages.length, isLibraryReady]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const reduced = prefersReducedMotion();
    messagesEndRef.current?.scrollIntoView({
      behavior: reduced ? "auto" : behavior,
    });
  }, []);

  useEffect(() => {
    if (activeView !== "conversation" || !isNearConversationBottomRef.current) return;

    // Follow a live answer only while the reader is already at the end. A
    // user inspecting an older answer must never be pulled away by stream
    // updates.
    const scroll = () => {
      scrollToBottom(isLoading ? "auto" : "smooth");
    };
    const frame =
      typeof requestAnimationFrame === "function"
        ? requestAnimationFrame(scroll)
        : window.setTimeout(scroll, 0);
    return () => {
      if (typeof cancelAnimationFrame === "function") {
        cancelAnimationFrame(frame);
      } else {
        window.clearTimeout(frame);
      }
    };
  }, [activeView, isLoading, messages, scrollToBottom]);

  useEffect(() => {
    if (activeView === "conversation") return;
    const container = workspaceMainRef.current;
    if (!container) return;
    if (typeof container.scrollTo === "function") {
      container.scrollTo({ top: 0, behavior: "auto" });
    } else {
      container.scrollTop = 0;
    }
  }, [activeView]);

  // Focus a bookmarked message opened from the Library.
  useEffect(() => {
    if (!pendingFocusMessageId) return;
    const frame = window.requestAnimationFrame(() => {
      const target = document.getElementById(`message-${pendingFocusMessageId}`);
      target?.scrollIntoView({
        behavior: prefersReducedMotion() ? "auto" : "smooth",
        block: "start",
      });
      target?.focus({ preventScroll: true });
      setPendingFocusMessageId(null);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [pendingFocusMessageId, activeView, messages.length]);

  // Library is rendered lazily with the workspace view. Wait for the view
  // transition before focusing its search input so Ctrl/Cmd+K is dependable.
  useEffect(() => {
    if (!shouldFocusLibrarySearch || activeView !== "library") return;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById("library-search-input")?.focus();
      setShouldFocusLibrarySearch(false);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [activeView, shouldFocusLibrarySearch]);

  // Detect scroll position to show/hide scroll-to-bottom button
  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (!scrollContainer) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      isNearConversationBottomRef.current = isNearBottom;
      setShowScrollButton(!isNearBottom && messages.length > 0);
    };

    scrollContainer.addEventListener("scroll", handleScroll, { passive: true });
    return () => scrollContainer.removeEventListener("scroll", handleScroll);
  }, [activeView, messages.length]);

  const handleSendMessage = useCallback(async (text: string, snapshot?: RequestSnapshot) => {
    if (!isBackendConnected || !isPipelineReady) return;
    if (isReadOnly) return;
    if (!isSendableResearchQuestion(text)) return;

    const requestSnapshot: RequestSnapshot = snapshot
      ? { ...snapshot, answerLanguage: snapshot.answerLanguage ?? locale }
      : {
          ticker: selectedTicker,
          section: selectedSection,
          topK,
          enableComparative,
          answerLanguage: locale,
        };

    // One identity is captured before the preflight and carried through
    // message creation, the provider request, buffering, completion, and
    // the final save. Duplicate sends are blocked while one is in flight.
    const identity = beginSend(text);
    if (!identity) return;
    const analyticsStartedAt = Date.now();
    recordAnalyticsEvent({
      kind: "query_started",
      ticker: requestSnapshot.ticker,
      language: requestSnapshot.answerLanguage,
    });

    // Re-check a saved conversation's backend session before spending the
    // question; the session can expire while the user is reading. A
    // cancelled preflight (conversation switched meanwhile) never reports a
    // usable context and never touches the newer conversation's state.
    if (sessionContext !== "fresh") {
      const outcome = await ensureSendable(identity);
      if (outcome !== "ok") {
        finishSend(identity);
        return;
      }
    }
    if (!isIdentityActive(identity)) {
      finishSend(identity);
      return;
    }

    // Clear only the draft that was actually accepted. If the user edited a
    // next question while session preflight was pending, leave that newer
    // draft untouched; a failed preflight never erases input.
    if (inputTextRef.current.trim() === text) setInputText("");

    setActiveView("conversation");
    const controller = beginRequest();
    const isCurrentRequest = () => isCurrentResearchRequest(controller);

    const userMessage = {
      id: "user-" + Date.now(),
      sender: "user" as const,
      text: text,
      requestSnapshot,
    };

    updateMessages((prev) => [...prev, userMessage]);
    const isComparative =
      requestSnapshot.enableComparative && isComparativeQuery(text);
    const assistantMsgId = "assistant-" + Date.now();

    // The payload uses the session id captured with the identity, so a
    // session from an older conversation can never be combined with the
    // messages of a newer one.
    const payload = {
      question: text,
      ticker: requestSnapshot.ticker,
      section: requestSnapshot.section,
      top_k: requestSnapshot.topK,
      session_id: identity.sessionId,
      answer_language: requestSnapshot.answerLanguage,
    };

    try {
    if (isComparative) {
      // Create initial loading/placeholder message for Decomposed POST
      const placeholder = {
        id: assistantMsgId,
        sender: "assistant" as const,
        text: "",
        subQueries: [],
        wasDecomposed: true,
        isStreaming: true,
        status: "streaming" as const,
        requestSnapshot,
      };
      updateMessages((prev) => [...prev, placeholder]);

      setStageEventsByMessage((prev) => ({ ...prev, [assistantMsgId]: [] }));
      let comparativeText = "";
      const finishComparativeError = (error: unknown) => {
        if (!isCurrentRequest()) return;
        const requestError = describeRequestError(
          error,
          "We couldn't complete this comparison. Check the connection and try again.",
          locale,
        );
        updateMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  text: comparativeText + (comparativeText ? "\n\n" : "") + requestError.message,
                  error: true,
                  isStreaming: false,
                  status: "error" as const,
                  errorDetail: requestError.detail,
                  retryText: text,
                }
              : m,
          ),
        );
        markRequestIdle();
        recordAnalyticsEvent({
          kind: "query_error",
          ticker: requestSnapshot.ticker,
          language: requestSnapshot.answerLanguage,
          durationMs: Date.now() - analyticsStartedAt,
          status: "error",
        });
      };

      try {
        const useComparativeStream = import.meta.env.MODE !== "test" && typeof streamDecomposedQuery === "function";
        if (!useComparativeStream) {
          // Compatibility for older embedders that only provide the JSON
          // client; the backend JSON route remains supported by contract.
          const response = await queryDecomposed(payload, controller.signal);
          if (!isCurrentRequest()) return;
          comparativeText = response.answer;
          updateMessages((prev) => prev.map((m) => m.id === assistantMsgId ? {
            ...m,
            text: response.answer,
            model_used: response.model_used,
            sources: response.sources,
            subQueries: response.sub_queries,
            wasDecomposed: response.was_decomposed,
            numChunks: response.num_total_chunks,
            queryInterpretation: response.query_interpretation,
            isStreaming: false,
            status: "completed" as const,
          } : m));
          registerBackendExchange();
          markRequestIdle();
          recordAnalyticsEvent({
            kind: "query_completed",
            ticker: requestSnapshot.ticker,
            language: requestSnapshot.answerLanguage,
            durationMs: Date.now() - analyticsStartedAt,
            status: "completed",
          });
        } else {
          await streamDecomposedQuery(
            payload,
            (event) => {
            if (!isCurrentRequest()) return;
            if (event.type === "stage" && isStageEvent(event.data)) {
              setStageEventsByMessage((prev) => ({
                ...prev,
                [assistantMsgId]: appendStageEvent(prev[assistantMsgId] ?? [], event.data),
              }));
            } else if (event.type === "sources") {
              updateMessages((prev) => prev.map((m) => m.id === assistantMsgId ? { ...m, sources: event.data || [] } : m));
            } else if (event.type === "token") {
              comparativeText += typeof event.data === "string" ? event.data : "";
              updateMessages((prev) => prev.map((m) => m.id === assistantMsgId ? { ...m, text: comparativeText } : m));
            } else if (event.type === "done") {
              updateMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        text: comparativeText,
                        model_used: event.data?.model_used,
                        subQueries: event.data?.sub_queries,
                        wasDecomposed: event.data?.was_decomposed,
                        numChunks: event.data?.num_total_chunks,
                        queryInterpretation: event.data?.query_interpretation,
                        isStreaming: false,
                        status: "completed" as const,
                      }
                    : m,
                ),
              );
              registerBackendExchange();
              markRequestIdle();
              recordAnalyticsEvent({
                kind: "query_completed",
                ticker: requestSnapshot.ticker,
                language: requestSnapshot.answerLanguage,
                durationMs: Date.now() - analyticsStartedAt,
                status: "completed",
              });
            } else if (event.type === "error") {
              finishComparativeError(event.data);
            }
            },
            finishComparativeError,
            controller.signal,
          );
        }
      } catch (error) {
        finishComparativeError(error);
      } finally {
        finishRequest(controller);
      }
    } else {
      // Streamed query over POST EventStream
      const placeholder = {
        id: assistantMsgId,
        sender: "assistant" as const,
        text: "",
        isStreaming: true,
        status: "streaming" as const,
        requestSnapshot,
      };
      updateMessages((prev) => [...prev, placeholder]);

      setStageEventsByMessage((prev) => ({ ...prev, [assistantMsgId]: [] }));

      let streamingText = "";
      let pendingFlush: ReturnType<typeof setTimeout> | null = null;
      streamingBufferRef.current = { messageId: assistantMsgId, text: "" };

      const cancelPendingFlush = () => {
        if (pendingFlush !== null) {
          clearTimeout(pendingFlush);
          pendingFlush = null;
        }
      };

      const scheduleStreamingFlush = () => {
        if (pendingFlush === null) {
          pendingFlush = setTimeout(() => {
            pendingFlush = null;
            updateMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, text: streamingText } : m,
              ),
            );
          }, STREAM_FLUSH_INTERVAL_MS);
        }
      };

      try {
        await streamQuery(
          payload,
          (event) => {
            if (!isCurrentRequest()) return;
            if (event.type === "stage" && isStageEvent(event.data)) {
              setStageEventsByMessage((prev) => ({
                ...prev,
                [assistantMsgId]: appendStageEvent(prev[assistantMsgId] ?? [], event.data),
              }));
            } else if (event.type === "sources") {
              const sourcesList = event.data || [];
              updateMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        sources: sourcesList,
                      }
                    : m,
                ),
              );
            } else if (event.type === "token") {
              streamingText += event.data;
              streamingBufferRef.current = { messageId: assistantMsgId, text: streamingText };
              scheduleStreamingFlush();
            } else if (event.type === "done") {
              cancelPendingFlush();
              streamingBufferRef.current = null;
              updateMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        text: streamingText,
                        queryInterpretation: event.data?.query_interpretation,
                        execution: event.data?.execution,
                        visualAnswer: event.data?.visual_answer,
                        isStreaming: false,
                        status: "completed" as const,
                      }
                    : m,
                ),
              );
              registerBackendExchange();
              recordAnalyticsEvent({
                kind: "query_completed",
                ticker: requestSnapshot.ticker,
                language: requestSnapshot.answerLanguage,
                durationMs: Date.now() - analyticsStartedAt,
                status: "completed",
              });
              markRequestIdle();
            } else if (event.type === "error") {
              cancelPendingFlush();
              streamingBufferRef.current = null;
              updateMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        text:
                          streamingText +
                          (streamingText ? "\n\n" : "") +
                          "We couldn't complete this answer. Please try again.",
                        isStreaming: false,
                        error: true,
                        status: "error" as const,
                        errorDetail: event.data,
                        retryText: text,
                      }
                    : m,
                ),
              );
              markRequestIdle();
              recordAnalyticsEvent({
                kind: "query_error",
                ticker: requestSnapshot.ticker,
                language: requestSnapshot.answerLanguage,
                durationMs: Date.now() - analyticsStartedAt,
                status: "error",
              });
            }
          },
          (error) => {
            if (!isCurrentRequest()) return;
            const requestError = describeRequestError(
              error,
              "The connection closed before the answer finished. Please try again.",
              locale,
            );
            cancelPendingFlush();
            streamingBufferRef.current = null;
            updateMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                        text: streamingText + (streamingText ? "\n\n" : "") + requestError.message,
                      isStreaming: false,
                      error: true,
                      status: "error" as const,
                      errorDetail: requestError.detail,
                      retryText: text,
                    }
                  : m,
              ),
            );
            markRequestIdle();
            recordAnalyticsEvent({
              kind: "query_error",
              ticker: requestSnapshot.ticker,
              language: requestSnapshot.answerLanguage,
              durationMs: Date.now() - analyticsStartedAt,
              status: "connection_closed",
            });
          },
          controller.signal,
        );
      } catch (err: any) {
        if (!isCurrentRequest()) return;
          const requestError = describeRequestError(
            err,
            "We couldn't complete this answer. Please try again.",
            locale,
        );
        cancelPendingFlush();
        streamingBufferRef.current = null;
        updateMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                    text: streamingText + (streamingText ? "\n\n" : "") + requestError.message,
                  isStreaming: false,
                  error: true,
                  status: "error" as const,
                  errorDetail: requestError.detail,
                  retryText: text,
                }
              : m,
          ),
        );
        markRequestIdle();
        recordAnalyticsEvent({
          kind: "query_error",
          ticker: requestSnapshot.ticker,
          language: requestSnapshot.answerLanguage,
          durationMs: Date.now() - analyticsStartedAt,
          status: "error",
        });
      } finally {
        cancelPendingFlush();
        finishRequest(controller);
      }

      // The connection closed. If the server never sent a done or error
      // event, flush the buffered partial answer and normalize it to a
      // stopped state; a dropped stream must never remain "streaming".
      if (!isCurrentRequest() && isIdentityActive(identity)) {
        streamingBufferRef.current = null;
        updateMessages((prev) =>
          prev.map((m) => {
            if (m.id !== assistantMsgId || !m.isStreaming) return m;
            if (streamingText) {
              return { ...m, text: streamingText, isStreaming: false, status: "stopped" as const };
            }
            return {
              ...m,
              text: "The connection closed before the answer finished. Please try again.",
              isStreaming: false,
              error: true,
              status: "error" as const,
              retryText: text,
            };
          }),
        );
      }
    }
    } finally {
      streamingBufferRef.current = null;
      finishSend(identity);
    }

    if (controller.signal.aborted) return;

    // Refresh health details to get updated total turn counters, active sessions, etc.
    try {
      await refreshHealth(false, controller.signal);
    } catch (e) {
      if (!controller.signal.aborted) {
        console.warn("Could not refresh health data:", e);
      }
    }
  }, [
    beginRequest,
    beginSend,
    enableComparative,
    ensureSendable,
    finishSend,
    finishRequest,
    isBackendConnected,
    isIdentityActive,
    isCurrentResearchRequest,
    isPipelineReady,
    isReadOnly,
    setInputText,
    locale,
    markRequestIdle,
    registerBackendExchange,
    selectedSection,
    selectedTicker,
    sessionContext,
    topK,
    refreshHealth,
    updateMessages,
  ]);

  // Stable retry callback so memoized ChatMessage items skip re-renders;
  // the ref indirection keeps access to the latest send handler.
  const handleSendMessageRef = useRef(handleSendMessage);
  handleSendMessageRef.current = handleSendMessage;
  const handleRetry = useCallback((text: string, snapshot?: RequestSnapshot) => {
    if (isReadOnly) return;
    setInputText(text);
    handleSendMessageRef.current(text, snapshot);
  }, [isReadOnly, setInputText]);

  const confirmNewConversation = useCallback(async () => {
    setShowResetDialog(false);
    await startNewConversation();
    setActiveView("overview");
    setActiveSidebarPanel("research");
    try {
      await refreshHealth(true);
    } catch (e) {
      setIsBackendConnected(false);
      setIsPipelineReady(false);
    }
  }, [refreshHealth, startNewConversation]);

  const requestNewConversation = useCallback(() => {
    if (messages.length === 0) {
      void confirmNewConversation();
      return;
    }
    setShowResetDialog(true);
  }, [confirmNewConversation, messages.length]);

  const handleSelectConversation = useCallback(
    async (conversation: ConversationRecord) => {
      setActiveView(conversation.messages.length ? "conversation" : "overview");
      if (conversation.id === activeConversationId) return;
      await selectConversation(conversation);
    },
    [activeConversationId, selectConversation],
  );

  // Open the exact bookmarked answer inside its conversation.
  const handleOpenMessage = useCallback(
    async (conversationId: string, messageId: string) => {
      const conversation = conversations.find((item) => item.id === conversationId);
      if (!conversation) return;
      if (conversation.id !== activeConversationId) {
        await selectConversation(conversation);
      }
      setPendingFocusMessageId(messageId);
      setActiveView("conversation");
    },
    [activeConversationId, conversations, selectConversation],
  );

  const handleExportConversation = useCallback((conversation: ConversationRecord) => {
    downloadConversationMarkdown(conversation);
  }, []);

  const handleExportBackup = useCallback(() => {
    downloadConversationBackup(conversations);
  }, [conversations]);

  const handleImportBackup = useCallback(
    async (bundle: ConversationBackupBundle) => {
      const result = await importConversationRecords(bundle.conversations);
      mergeEvidenceCollections(bundle.collections);
      if (result.imported === 0) throw new Error("No conversation could be imported into storage.");
      return result;
    },
    [importConversationRecords],
  );

  // Bookmark toggle that works from Library cards for any conversation,
  // not only the one currently open.
  const handleSidebarToggleBookmark = useCallback(
    (conversationId: string, messageId: string) => {
      const conversation = conversations.find((item) => item.id === conversationId);
      if (!conversation) return;
      if (conversationId === activeConversationId) {
        toggleAnswerBookmark(messageId);
        return;
      }
      const bookmarked = conversation.bookmarkedMessageIds.includes(messageId);
      const next = bookmarked
        ? conversation.bookmarkedMessageIds.filter((id) => id !== messageId)
        : [...conversation.bookmarkedMessageIds, messageId];
      void saveConversationRecord({
        ...conversation,
        bookmarkedMessageIds: next,
        updatedAt: Date.now(),
      });
    },
    [activeConversationId, conversations, toggleAnswerBookmark],
  );

  const handleSaveMessageNote = useCallback((messageId: string, note: string) => {
    updateMessages((prev) => prev.map((message) => message.id === messageId ? { ...message, note: note || undefined } : message));
  }, [updateMessages]);

  const handleMessageFeedback = useCallback((messageId: string, feedback: MessageFeedback | undefined) => {
    updateMessages((prev) => prev.map((message) =>
      message.id === messageId ? { ...message, feedback } : message,
    ));
    recordAnalyticsEvent({
      kind: "feedback",
      status: feedback
        ? `${feedback.rating}${feedback.category ? `:${feedback.category}` : ""}`
        : "cleared",
    });
  }, [updateMessages]);

  const handleSaveAnswerVariant = useCallback((message: Message) => {
    if (!activeRecord || message.sender !== "assistant" || !message.text) return;
    const now = Date.now();
    const variant: AnswerVariant = {
      id: `variant-${now}-${Math.random().toString(36).slice(2, 8)}`,
      originMessageId: message.id,
      text: message.text,
      sources: (message.sources ?? []).map((source) => ({ ...source })),
      requestSnapshot: message.requestSnapshot,
      answerLanguage: message.requestSnapshot?.answerLanguage ?? locale,
      status: message.status === "error" ? "error" : message.status === "stopped" ? "stopped" : "completed",
      execution: message.execution,
      visualAnswer: message.visualAnswer,
      createdAt: now,
      updatedAt: now,
    };
    void updateConversationMetadata(activeRecord.id, {
      variants: [...(activeRecord.variants ?? []), variant],
    });
  }, [activeRecord, locale, updateConversationMetadata]);

  useEffect(() => {
    if (!showResetDialog) return;
    const handleDialogKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowResetDialog(false);
    };
    document.addEventListener("keydown", handleDialogKeyDown);
    resetCancelRef.current?.focus();
    return () => document.removeEventListener("keydown", handleDialogKeyDown);
  }, [showResetDialog]);

  // Global shortcuts: Ctrl/Cmd+K opens the Library with search focused;
  // Escape closes the topmost overlay layer.
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setShouldFocusLibrarySearch(true);
        handleSelectWorkspaceView("library");
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "p") {
        event.preventDefault();
        setIsCommandPaletteOpen(true);
        return;
      }
      if (event.key === "Escape") {
        if (isCommandPaletteOpen) {
          setIsCommandPaletteOpen(false);
          return;
        }
        if (isHelpOpen) {
          setIsHelpOpen(false);
          return;
        }
        if (showResetDialog) {
          setShowResetDialog(false);
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isCommandPaletteOpen, isHelpOpen, showResetDialog]);

  const handleStopGenerating = stopGenerating;

  const closeTemplateQuestion = useCallback(() => {
    templateOpeningSnapshotRef.current = null;
    setTemplateToCustomize(null);
  }, []);

  const openTemplateQuestion = useCallback((template: ResearchTemplate) => {
    templateOpeningSnapshotRef.current = {
      conversationId: activeConversationId,
      draft: inputTextRef.current,
      locale,
      scope: { ticker: selectedTicker, section: selectedSection, topK, enableComparative },
      templateId: template.id,
    };
    setTemplateToCustomize(template);
  }, [activeConversationId, enableComparative, locale, selectedSection, selectedTicker, topK]);

  const handleApplyTemplate = useCallback((payload: ResearchTemplateApplyPayload) => {
    const opening = templateOpeningSnapshotRef.current;
    const currentScope = { ticker: selectedTicker, section: selectedSection, topK, enableComparative };
    const contextChanged = !opening ||
      opening.templateId !== payload.templateId ||
      opening.conversationId !== activeConversationId ||
      opening.draft !== inputTextRef.current ||
      opening.locale !== locale ||
      !scopesMatch(opening.scope, currentScope);

    if (contextChanged) {
      setContextualCommandNotice(locale === "vi"
        ? "Ngữ cảnh nghiên cứu đã thay đổi; hãy mở lại mẫu này."
        : "Research context changed; reopen this template.");
      closeTemplateQuestion();
      return;
    }
    if (!isSendableResearchQuestion(payload.question)) {
      setContextualCommandNotice(locale === "vi"
        ? "Câu hỏi mẫu không hợp lệ; các thay đổi hiện tại vẫn được giữ nguyên."
        : "This template question is invalid; your current draft and scope were preserved.");
      return;
    }

    // The dialog has already validated and normalized the payload. Apply the
    // question and its derived scope in the same event, without sending it.
    setInputText(payload.question);
    patchScope(payload.scope);
    closeTemplateQuestion();
    setActiveView("conversation");
    window.requestAnimationFrame(() => {
      document.getElementById("chat-textarea")?.focus();
    });
  }, [activeConversationId, closeTemplateQuestion, enableComparative, locale, patchScope, selectedSection, selectedTicker, setInputText, topK]);

  const handleSelectSample = useCallback((sample: ResearchTemplate | SampleQuestion) => {
    if ("id" in sample) {
      openTemplateQuestion(sample);
    } else {
      patchScope({
        ...(sample.ticker !== undefined ? { ticker: sample.ticker || null } : {}),
        ...(sample.section !== undefined ? { section: sample.section || null } : {}),
      });
      setInputText(sample.text);
    }
    setIsSidebarOpen(false); // Close sidebar on mobile if clicked
    window.requestAnimationFrame(() => {
      document.getElementById("chat-textarea")?.focus();
    });
  }, [locale, openTemplateQuestion, patchScope, setInputText]);

  const handleCloseSidebar = useCallback(() => {
    cancelEvidenceFocusRestore();
    setIsSidebarOpen(false);
  }, [cancelEvidenceFocusRestore]);

  const handleToggleSidebar = useCallback(() => {
    cancelEvidenceFocusRestore();
    setIsSidebarOpen((open) => !open);
  }, [cancelEvidenceFocusRestore]);

  const handleSelectWorkspaceView = useCallback((view: WorkspaceView) => {
    setActiveView(view);
    setIsSidebarOpen(false);
    if (view !== "conversation") setIsEvidenceOpen(false);
    if (view === "library") setActiveSidebarPanel("library");
    if (view === "overview" || view === "conversation" || view === "search" || view === "documents" || view === "retrieval" || view === "architecture") {
      setActiveSidebarPanel("research");
    }
  }, []);

  const handleSelectTheme = useCallback((nextTheme: ThemePreference) => {
    setThemePreference(nextTheme);
  }, []);

  const handleReturnToConversation = useCallback(() => {
    setActiveView("conversation");
  }, []);

  const handleUseRetrievalQuestion = useCallback((question: string, scope?: { ticker: string | null; section: string | null }) => {
    if (scope) {
      patchScope(scope);
    }
    setInputText(question);
    setActiveView("conversation");
    window.requestAnimationFrame(() => {
      document.getElementById("chat-textarea")?.focus();
    });
  }, [patchScope, setInputText]);

  const handlePaletteNavigate = useCallback((view: PaletteView) => {
    handleSelectWorkspaceView(view);
    if (view === "conversation") {
      window.requestAnimationFrame(() => document.getElementById("chat-textarea")?.focus());
    }
  }, [handleSelectWorkspaceView]);

  const handlePaletteTemplate = openTemplateQuestion;

  const handleRetryConnection = useCallback(async () => {
    try {
      await refreshHealth(true);
      // A recovered backend may also have recovered the session context.
      if (sessionContext === "unknown" || sessionContext === "missing") {
        void recheckSessionContext();
      }
    } catch {
      setIsBackendConnected(false);
      setIsPipelineReady(false);
    }
  }, [refreshHealth, recheckSessionContext, sessionContext]);

  const isStreaming = useMemo(
    () => messages.some((message) => message.isStreaming),
    [messages],
  );
  const scopeLabel = useMemo(() => {
    const labels = [
      selectedTicker ? formatCompanyLabel(selectedTicker) : (locale === "vi" ? "Tất cả công ty" : "All companies"),
      selectedSection ? (SECTION_METADATA[selectedSection]?.shortLabel || selectedSection) : (locale === "vi" ? "Tất cả mục" : "All sections"),
      `Top ${topK}`,
    ];
    if (enableComparative) labels.push(locale === "vi" ? "So sánh" : "Comparison");
    return labels.join(" · ");
  }, [enableComparative, locale, selectedSection, selectedTicker, topK]);

  const hasExchanges = messages.length > 0;
  const evidenceTarget = useMemo(() => {
    if (evidenceSelection) {
      if (evidenceSelection.conversationId !== activeConversationId) return null;
      const message = messages.find((candidate) => candidate.id === evidenceSelection.messageId);
      const variant = evidenceSelection.variantId
        ? activeRecord?.variants?.find((candidate) => candidate.id === evidenceSelection.variantId && candidate.originMessageId === message?.id)
        : null;
      const sources = evidenceSelection.variantId ? variant?.sources : message?.sources;
      const selectedSource = sources?.[evidenceSelection.citationIndex];
      if (sources?.length && sourceMatchesSelection(selectedSource, evidenceSelection, evidenceSelection.citationIndex)) {
        return { sources, selectedIndex: evidenceSelection.citationIndex, selection: evidenceSelection, unavailable: false };
      }
      return { sources: [] as Source[], selectedIndex: -1, selection: evidenceSelection, unavailable: true };
    }
    const latestMessage = [...messages].reverse().find((message) => message.sender === "assistant" && message.sources?.length);
    return latestMessage?.sources?.length && latestMessage.sources[0]
      ? {
          sources: latestMessage.sources,
          selectedIndex: 0,
          selection: createEvidenceSelection(activeConversationId, latestMessage.id, 0, latestMessage.sources[0]),
          unavailable: false,
        }
      : null;
  }, [activeConversationId, activeRecord?.variants, evidenceSelection, messages]);
  const hasGroundedAnswer = useMemo(
    () => Boolean(resolveDisplayedAnswerTarget(null, messages, activeRecord, activeConversationId)),
    [activeConversationId, activeRecord, messages],
  );
  const commandEvidenceTarget = useMemo(
    () => resolveEvidenceCommandTarget(
      displayedAnswerContext,
      evidenceSelection,
      messages,
      activeRecord,
      activeConversationId,
    ),
    [activeConversationId, activeRecord, displayedAnswerContext, evidenceSelection, messages],
  );
  const contextualCommands = useMemo<ContextualCommandDefinition[]>(() => {
    const commands: ContextualCommandDefinition[] = [];
    const unavailableAnswerNotice = locale === "vi"
      ? "Câu trả lời đang chọn không còn khả dụng."
      : "The selected answer is no longer available.";
    const unavailableSourceNotice = locale === "vi"
      ? "Source đang chọn không còn khả dụng."
      : "The selected source is no longer available.";
    if (hasGroundedAnswer) {
      commands.push({
        id: "copy-current-answer",
        labelKey: "palette.copyAnswer",
        descriptionKey: "palette.copyAnswerDescription",
        icon: "copy",
        accentFamily: "evidence",
        run: () => {
          const target = resolveDisplayedAnswerTarget(
            displayedAnswerContextRef.current,
            messagesRef.current,
            activeRecordRef.current,
            activeConversationIdRef.current,
          );
          if (!target) {
            setContextualCommandNotice(unavailableAnswerNotice);
            return;
          }
          if (!navigator.clipboard) {
            setContextualCommandNotice(locale === "vi" ? "Không thể sao chép câu trả lời." : "Could not copy the current answer.");
            return;
          }
          void navigator.clipboard.writeText(target.text).then(
            () => setContextualCommandNotice(locale === "vi" ? "Đã sao chép câu trả lời hiện tại." : "Current answer copied."),
            () => setContextualCommandNotice(locale === "vi" ? "Không thể sao chép câu trả lời." : "Could not copy the current answer."),
          );
        },
      });
    }
    if (commandEvidenceTarget) {
      commands.push({
        id: "inspect-current-sources",
        labelKey: "palette.inspectSources",
        descriptionKey: "palette.inspectSourcesDescription",
        icon: "sources",
        accentFamily: "evidence",
        run: () => {
          const target = resolveEvidenceCommandTarget(
            displayedAnswerContextRef.current,
            evidenceSelectionRef.current,
            messagesRef.current,
            activeRecordRef.current,
            activeConversationIdRef.current,
          );
          if (!target) {
            setContextualCommandNotice(unavailableSourceNotice);
            return;
          }
          setActiveView("conversation");
          setEvidenceSelection(target.selection);
          setIsEvidenceOpen(true);
        },
      });
      commands.push({
        id: "save-selected-source",
        labelKey: "palette.saveSource",
        descriptionKey: "palette.saveSourceDescription",
        icon: "saveSource",
        accentFamily: "evidence",
        run: () => {
          const target = resolveEvidenceCommandTarget(
            displayedAnswerContextRef.current,
            evidenceSelectionRef.current,
            messagesRef.current,
            activeRecordRef.current,
            activeConversationIdRef.current,
          );
          if (!target) {
            setContextualCommandNotice(unavailableSourceNotice);
            return;
          }
          try {
            saveEvidence(target.source, {
              conversationId: target.selection.conversationId,
              messageId: target.selection.messageId,
            });
            setContextualCommandNotice(locale === "vi" ? "Đã lưu source đang chọn." : "Selected source saved.");
          } catch (error) {
            setContextualCommandNotice(error instanceof Error ? error.message : (locale === "vi" ? "Không thể lưu source." : "Could not save the selected source."));
          }
        },
      });
    }
    commands.push({
      id: "open-scope-editor",
      labelKey: "palette.openScope",
      descriptionKey: "palette.openScopeDescription",
      icon: "metadata",
      accentFamily: "research",
      run: () => {
        setActiveView("conversation");
        setIsScopeEditorOpen(true);
      },
    });
    return commands;
  }, [commandEvidenceTarget, hasGroundedAnswer, locale, setEvidenceSelection]);
  const showContextBanner =
    activeView === "conversation" && hasExchanges &&
    (sessionContext === "checking" || isReadOnly);
  const evidenceInline = workspaceWidth >= CONTEXT_INLINE_MIN_WORKSPACE_WIDTH;
  const effectiveContextRailWidth = Math.min(
    CONTEXT_RAIL_MAX_WIDTH,
    Math.max(CONTEXT_RAIL_MIN_WIDTH, workspaceWidth > 0 ? workspaceWidth - 496 : contextRailWidth),
    contextRailWidth,
  );
  const showComposer = !["retrieval", "documents", "library", "search", "architecture", "evaluation", "analytics", "system"].includes(activeView);
  const composer = showComposer ? (
    <div className="composer-shell flex-shrink-0 z-10">
      <ChatInput
        inputText={inputText}
        setInputText={setInputText}
        onSendMessage={handleSendMessage}
        onStopGenerating={handleStopGenerating}
        isLoading={isLoading}
        isStreaming={isStreaming}
        isPreflightRunning={isPreflightRunning}
        isBackendConnected={isBackendConnected}
        isPipelineReady={isPipelineReady}
        isReadOnly={isReadOnly && hasExchanges}
        readOnlyMessage={
          sessionContext === "missing"
            ? "The backend session for this saved conversation has expired. Start a new conversation to ask follow-up questions."
            : "The backend could not be reached. Check the connection again before asking follow-up questions."
        }
        showBanner={activeView === "conversation" && hasExchanges}
        scopeLabel={scopeLabel || undefined}
        tickers={tickers}
        sections={sections}
        selectedTicker={selectedTicker}
        onSelectTicker={setSelectedTicker}
        selectedSection={selectedSection}
        onSelectSection={setSelectedSection}
        topK={topK}
        onChangeTopK={setTopK}
        enableComparative={enableComparative}
        onToggleComparative={setEnableComparative}
        scopeOpen={isScopeEditorOpen}
        onScopeOpenChange={setIsScopeEditorOpen}
      />
    </div>
  ) : null;

  return (
    <div className="app-shell flex w-screen max-w-full h-dvh font-sans text-[var(--text-primary)] overflow-hidden bg-grid-pattern">
      {/* Collapsible Sidebar */}
      <Sidebar
        tickers={tickers}
        sections={sections}
        selectedTicker={selectedTicker}
        onSelectTicker={setSelectedTicker}
        selectedSection={selectedSection}
        onSelectSection={setSelectedSection}
        topK={topK}
        onChangeTopK={setTopK}
        enableComparative={enableComparative}
        onToggleComparative={setEnableComparative}
        onNewConversation={requestNewConversation}
        onSelectSample={handleSelectSample}
        healthData={healthData}
        isOpen={isSidebarOpen}
        onClose={handleCloseSidebar}
        isDesktopNavigation={isDesktopNavigation}
        navigationLayout={navigationLayout}
        isClearingSession={isClearingSession}
        activePanel={activeSidebarPanel}
        onChangePanel={setActiveSidebarPanel}
        activeView={activeView}
        onSelectView={handleSelectWorkspaceView}
        hasMessages={hasExchanges}
        conversations={conversations}
        activeConversationId={activeConversationId}
        storageMode={storageMode}
        storageWarning={storageWarning}
        saveIndicator={saveIndicator}
        onSelectConversation={handleSelectConversation}
        onOpenMessage={handleOpenMessage}
        onRenameConversation={renameConversation}
        onToggleBookmark={handleSidebarToggleBookmark}
        onDeleteConversation={(conversationId) => {
          void deleteConversation(conversationId);
        }}
        onExportConversation={handleExportConversation}
        onExportBackup={handleExportBackup}
        onImportBackup={handleImportBackup}
        onUpdateMetadata={updateConversationMetadata}
        writerStatus={writerStatus}
        onRequestWriter={requestLibraryWriter}
      />

      {/* Main chat window area */}
      <div className="w-0 flex-1 min-w-0 max-w-full flex flex-col h-full overflow-hidden">
        {/* Header toolbar */}
        <WorkspaceHeader
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={handleToggleSidebar}
          navigationLayout={navigationLayout}
          onToggleNavigationLayout={toggleNavigationLayout}
          activeView={activeView}
          onSelectView={handleSelectWorkspaceView}
          hasMessages={hasExchanges}
          isBackendConnected={isBackendConnected}
          isPipelineReady={isPipelineReady}
          companyCount={healthData?.corpus?.searchable_company_count}
          theme={themePreference}
          resolvedTheme={resolvedTheme}
          onSelectTheme={handleSelectTheme}
          isClearingSession={isClearingSession}
          onReset={requestNewConversation}
          onOpenHelp={() => setIsHelpOpen(true)}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        />
        {/* Content stream area */}
        <main
          aria-label="Research workspace"
          ref={workspaceMainRef}
          className={`workspace-scroll flex-1 overflow-y-auto overflow-x-hidden min-h-0 relative z-10 ${activeView === "conversation" ? "workspace-scroll--conversation" : ""}`}
        >
          {showContextBanner && (
            <SessionContextBanner
              status={sessionContext}
              onRecheck={() => void recheckSessionContext()}
              onNewConversation={requestNewConversation}
            />
          )}
          {contextualCommandNotice && (
            <div className="mx-auto mt-3 flex max-w-6xl items-center justify-between gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-3 py-2 text-sm text-[var(--text-muted)]" role="status">
              <span>{contextualCommandNotice}</span>
              <button type="button" className="text-xs font-semibold text-[var(--accent-text)]" onClick={() => setContextualCommandNotice(null)}>
                {locale === "vi" ? "Đóng" : "Dismiss"}
              </button>
            </div>
          )}
          <div
            className={`workspace-main-grid ${activeView === "conversation" ? "workspace-main-grid--conversation" : ""} ${activeView === "conversation" && evidenceTarget && isEvidenceOpen && evidenceInline ? "workspace-main-grid--with-evidence" : ""}`}
            style={{ "--context-rail-width": `${effectiveContextRailWidth}px` } as CSSProperties}
          >
            <div className="workspace-primary-column">
              <Suspense fallback={<WorkspacePanelFallback />}>
                {activeView === "search" ? (
              <SearchWorkspace
                selectedTicker={selectedTicker}
                selectedSection={selectedSection}
                isBackendConnected={isBackendConnected}
                onUseQuestion={handleUseRetrievalQuestion}
              />
                ) : activeView === "architecture" ? (
              <ArchitecturePanel />
                ) : activeView === "retrieval" ? (
              <RetrievalLabPanel
                tickers={tickers}
                sections={sections}
                selectedTicker={selectedTicker}
                selectedSection={selectedSection}
                isBackendConnected={isBackendConnected}
                onUseQuestion={handleUseRetrievalQuestion}
              />
                ) : activeView === "documents" ? (
              <DocumentExplorerPanel tickers={tickers} sections={sections} />
                ) : activeView === "library" ? (
              <section className="workspace-page" aria-labelledby="library-workspace-title">
                <div className="workspace-page__intro">
                  <div>
                    <div className="workspace-eyebrow"><LibraryIcon className="h-3.5 w-3.5" />{locale === "vi" ? "Kho nghiên cứu" : "Research library"}</div>
                    <h1 id="library-workspace-title">{locale === "vi" ? "Thư viện cuộc trò chuyện" : "Conversation library"}</h1>
                    <p>{t(libraryNavItem.descriptionKey)}</p>
                  </div>
                </div>
                <div className="library-workspace-surface">
                  <ConversationLibrary
                    conversations={conversations}
                    activeConversationId={activeConversationId}
                    storageMode={storageMode}
                    storageWarning={storageWarning}
                    saveIndicator={saveIndicator}
                    onSelect={handleSelectConversation}
                    onRename={renameConversation}
                    onToggleBookmark={handleSidebarToggleBookmark}
                    onDelete={(conversationId) => void deleteConversation(conversationId)}
                    onExport={handleExportConversation}
                    onExportBackup={handleExportBackup}
                    onImportBackup={handleImportBackup}
                    onUpdateMetadata={updateConversationMetadata}
                    writerStatus={writerStatus}
                    onRequestWriter={requestLibraryWriter}
                    onOpenMessage={handleOpenMessage}
                    onClose={() => setActiveView("overview")}
                  />
                </div>
              </section>
                ) : activeView === "system" ? (
              <SystemInfoPanel />
                ) : activeView === "evaluation" ? (
              <EvaluationPanel />
                ) : activeView === "analytics" ? (
              <AnalyticsPanel />
                ) : activeView === "overview" ? (
              <OverviewPanel
                hasMessages={hasExchanges}
                companyCount={healthData?.corpus?.searchable_company_count ?? null}
                indexedChunkCount={healthData?.corpus?.indexed_chunk_count ?? null}
                onReturnToConversation={handleReturnToConversation}
                isBackendConnected={isBackendConnected}
                isPipelineReady={isPipelineReady}
                onRetryConnection={handleRetryConnection}
                scopeLabel={scopeLabel}
                recentConversations={recentConversations}
                onSelectTemplate={handlePaletteTemplate}
                onSelectConversation={handleSelectConversation}
              />
                ) : (
            /* Active Chat Stream */
            <div className="conversation-primary-shell">
              <div ref={scrollContainerRef} className="conversation-message-scroll">
                <div className="flex flex-col w-full min-h-full py-4 md:py-5 pb-6 relative">
              <Suspense
                fallback={
                  <div className="flex items-center gap-2 max-w-4xl mx-auto w-full px-3 py-4 text-sm text-slate-500 dark:text-slate-400" role="status">
                    <span className="w-2 h-2 rounded-full bg-brand-indigo animate-pulse" />
                    Loading response renderer…
                  </div>
                }
              >
                {messages.length === 0 ? (
                  <section className="research-empty-state max-w-2xl mx-auto w-full px-4 py-10 md:py-16" aria-labelledby="research-empty-title">
                    <p className="research-empty-state__eyebrow">New research</p>
                    <h1 id="research-empty-title">Start with a filing question</h1>
                    <p>
                      Choose a focused example or write your own question below. The answer will stay grounded in retrieved 10-K evidence.
                    </p>
                    <SampleQuestionChips onSelect={handleSelectSample} />
                  </section>
                ) : messages.map((msg, index) => (
                  <ChatMessage
                    key={msg.id}
                    message={msg}
                    messageId={msg.id}
                    isLatest={index === messages.length - 1}
                    onRetry={isReadOnly ? undefined : handleRetry}
                    bookmarked={bookmarkedMessageIds.includes(msg.id)}
                    onToggleBookmark={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? () => toggleAnswerBookmark(msg.id)
                        : undefined
                    }
                    onSaveNote={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? (note) => handleSaveMessageNote(msg.id, note)
                        : undefined
                    }
                    onFeedback={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? (feedback) => handleMessageFeedback(msg.id, feedback)
                        : undefined
                    }
                    variants={activeRecord?.variants?.filter((variant) => variant.originMessageId === msg.id)}
                    onSaveVariant={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? () => handleSaveAnswerVariant(msg)
                        : undefined
                    }
                    onInspectSource={handleInspectSource}
                    onDisplayedAnswerContext={handleDisplayedAnswerContext}
                    pipelineStages={stageEventsByMessage[msg.id]}
                    tabIndex={0}
                  />
                ))}
              </Suspense>
              <div ref={messagesEndRef} />

              {/* Scroll to bottom button */}
              {showScrollButton && (
                <button
                  type="button"
                  onClick={() => scrollToBottom()}
                  className="ui-message-enter fixed bottom-32 right-6 md:right-8 min-h-10 min-w-10 p-2.5 rounded-full surface-raised border-[var(--border-subtle)] shadow-lg text-[var(--text-muted)] transition-colors cursor-pointer z-30"
                  aria-label="Scroll to bottom"
                >
                  <ChevronDown className="w-5 h-5" />
                </button>
              )}
                </div>
              </div>
              {composer}
            </div>
                )}
              </Suspense>
            </div>
            {activeView === "conversation" && evidenceTarget && (
              <EvidenceWorkspaceRail
                sources={evidenceTarget.sources}
                selectedIndex={evidenceTarget.selectedIndex}
                unavailable={evidenceTarget.unavailable}
                messageId={evidenceTarget.selection.messageId}
                conversationId={evidenceTarget.selection.conversationId}
                railWidth={effectiveContextRailWidth}
                onRailWidthChange={setContextRailWidth}
                isOpen={isEvidenceOpen}
                presentation={evidenceInline ? "inline" : "drawer"}
                onClose={handleCloseEvidence}
                onSelectIndex={(citationIndex) => {
                  const source = evidenceTarget.sources[citationIndex];
                  if (!source) return;
                  handleInspectSource(
                    (() => {
                      const { conversationId: _conversationId, ...selection } = createEvidenceSelection(
                        activeConversationId,
                        evidenceTarget.selection.messageId,
                        citationIndex,
                        source,
                        evidenceTarget.selection.variantId,
                      );
                      return selection;
                    })(),
                  );
                }}
              />
            )}
          </div>
        </main>

        {activeView !== "conversation" && composer}
      </div>

      <HelpDialog open={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
      <TemplateQuestionDialog
        open={templateToCustomize !== null}
        template={templateToCustomize}
        tickers={tickers}
        onClose={closeTemplateQuestion}
        onApply={handleApplyTemplate}
      />
      <CommandPalette
        open={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onNavigate={handlePaletteNavigate}
        onTemplate={handlePaletteTemplate}
        onHelp={() => setIsHelpOpen(true)}
        onNewConversation={requestNewConversation}
        contextualCommands={contextualCommands}
      />

      <ModalDialog
        open={showResetDialog}
        onClose={() => setShowResetDialog(false)}
        labelledBy="reset-dialog-title"
        initialFocusRef={resetCancelRef}
        className="w-full max-w-md rounded-2xl surface-raised border-[var(--border-subtle)] p-5 shadow-2xl"
      >
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full state-warning-surface">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <h2 id="reset-dialog-title" className="text-base font-semibold text-[var(--text-primary)]">
                    Start a new conversation?
                  </h2>
                  <button
                    type="button"
                    aria-label="Close confirmation dialog"
                    onClick={() => setShowResetDialog(false)}
                    className="min-h-9 min-w-9 rounded-lg p-2 text-[var(--text-subtle)] hover:surface-muted-hover"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
                  This saves the current conversation to your local Library and
                  starts a fresh session. The new conversation does not carry
                  over the previous backend context. Your draft text and
                  filters are kept so you can edit and resend them.
                </p>
                <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <button
                    type="button"
                    ref={resetCancelRef}
                    onClick={() => setShowResetDialog(false)}
                    className="min-h-10 rounded-lg border-[var(--border-strong)] px-4 py-2 text-sm font-semibold text-[var(--text-primary)] hover:surface-muted-hover"
                  >
                    Keep conversation
                  </button>
                  <button
                    type="button"
                    onClick={() => void confirmNewConversation()}
                    className="min-h-10 rounded-lg primary-action-button px-4 py-2 text-sm font-semibold"
                  >
                    Start new conversation
                  </button>
                </div>
              </div>
            </div>
      </ModalDialog>
    </div>
  );
}

/**
 * Backend session context banner. It explains that the local copy is
 * authoritative for reading while the backend memory is unavailable — it
 * never implies that local history was restored on the server.
 */
function SessionContextBanner({
  status,
  onRecheck,
  onNewConversation,
}: {
  status: SessionContextStatus;
  onRecheck: () => void;
  onNewConversation: () => void;
}) {
  if (status === "fresh" || status === "available") return null;
  if (status === "checking") {
    return (
      <div className="session-notice session-notice--checking" role="status" aria-live="polite">
        <RefreshCw className="h-4 w-4 animate-spin flex-shrink-0" aria-hidden="true" />
        <span className="min-w-0 flex-1">Checking whether the backend still holds this conversation's context…</span>
      </div>
    );
  }
  if (status === "missing") {
    return (
      <div className="session-notice session-notice--missing" role="status" aria-live="polite">
        <BookMarked className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
        <span className="min-w-0 flex-1">
          The backend session for this saved conversation has expired. You can
          still read, search, bookmark, and export the local copy below.
        </span>
        <button type="button" onClick={onNewConversation}>
          Start new conversation
        </button>
      </div>
    );
  }
  return (
    <div className="session-notice session-notice--unknown" role="status" aria-live="polite">
      <AlertTriangle className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
      <span className="min-w-0 flex-1">
        The backend could not be reached, so this conversation's context is
        unknown. Follow-up questions are paused until the connection is
        checked.
      </span>
      <button type="button" onClick={onRecheck}>
        Check connection again
      </button>
    </div>
  );
}
