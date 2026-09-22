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
} from "react";
import { BrowserRouter, useLocation, useNavigate } from "react-router-dom";
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
import { CommandPalette } from "./components/CommandPalette";
import { EvidenceWorkspaceRail } from "./components/EvidenceWorkspaceRail";
import { RouteDocumentContext } from "./components/workbench/RouteDocumentContext";
import {
  DocumentWorkspaceTarget,
  HealthResponse,
  RequestSnapshot,
  ThemePreference,
  AnswerVariant,
  ConversationMode,
  DisplayedAnswerContext,
  EvidenceSelection,
  Message,
  MessageFeedback,
  AnswerTarget,
  Source,
  StageEvent,
} from "./types";
import {
  checkHealth,
  getSupportedTickers,
  getChunkDetail,
  queryDecomposed,
  streamQuery,
  streamDecomposedQuery,
  ApiError,
} from "./lib/api";
import { formatCompanyLabel, SECTION_METADATA } from "./lib/displayMetadata";
import { ConversationRecord } from "./lib/conversationStore";
import {
  downloadConversationBackup,
  downloadConversationMarkdown,
} from "./lib/conversationExport";
import type { ConversationBackupBundle } from "./lib/conversationExport";
import { useConversationLibrary, SessionContextStatus } from "./hooks/useConversationLibrary";
import { buildRelatedResearchSuggestions } from "./lib/relatedResearch";
import { useAnswerActions, toLegacySaveStatus } from "./hooks/useAnswerActions";
import { useResearchDraft } from "./hooks/useResearchDraft";
import type { ResearchScope } from "./hooks/useResearchDraft";
import { useNavigationLayout } from "./hooks/useNavigationLayout";
import { useEvidenceSelection } from "./hooks/useEvidenceSelection";
import { useReaderSession } from "./hooks/useReaderSession";
import { useResearchSession } from "./hooks/useResearchSession";
import { useLocale, type Locale } from "./lib/i18n";
import { recordAnalyticsEvent } from "./lib/analyticsStore";
import { getResearchTemplateCopy, isSendableResearchQuestion, RESEARCH_TEMPLATES, type ResearchTemplate, type ResearchTemplateApplyPayload } from "./lib/researchTemplates";
import { importEvidenceCollections, mergeEvidenceCollections, preflightEvidenceCollectionsImport, saveEvidence, snapshotProvenanceFromSource } from "./lib/evidenceCollections";
import type { EvidenceItem } from "./lib/evidenceCollections";
import { evidenceCurrentSourceFocusId, evidenceItemFocusId } from "./components/EvidenceCollectionsPanel";
import type { CurrentSourceCheckResult } from "./components/EvidenceCollectionsPanel";
import type { ContextualCommandDefinition } from "./lib/commandRegistry";
import { getWorkspaceNavItem, type WorkspaceView } from "./lib/workspace";
import { getSemanticIcon } from "./lib/semanticIcons";
import { describeRequestError } from "./lib/requestError";
import { createEvidenceSelection, sourceMatchesSelection } from "./lib/sourceIdentity";
import { buildEvidenceDeepLinkForSelection, parseEvidenceDeepLink } from "./lib/evidenceDeepLink";
import { appendStageEvent, isStageEvent } from "./lib/stageEvents";
import { ApplicationWorkspace } from "./components/workbench/ApplicationWorkspace";
import { ConversationPageShell } from "./components/conversation/ConversationPageShell";
import {
  primaryRouteId,
  resolveAppRoute,
  routeForWorkspaceView,
  routePath,
  translateLegacyLocation,
  type ShellRouteId,
} from "./app/routes";

const STREAM_FLUSH_INTERVAL_MS = 80;
const HEALTH_REFRESH_INTERVAL_MS = 15_000;
const NAVIGATION_DESKTOP_MIN_WIDTH = 1025;
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
const RetrievalPanel = lazy(() =>
  import("./components/retrieval/RetrievalPanel").then(({ RetrievalPanel }) => ({ default: RetrievalPanel })),
);
const RerankerPanel = lazy(() =>
  import("./components/reranker/RerankerPanel").then(({ RerankerPanel }) => ({ default: RerankerPanel })),
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
const DiscoverySearchPage = lazy(() =>
  import("./components/search/DiscoverySearchPage").then(({ DiscoverySearchPage }) => ({ default: DiscoverySearchPage })),
);
const ArchitecturePanel = lazy(() =>
  import("./components/ArchitecturePanel").then(({ ArchitecturePanel }) => ({ default: ArchitecturePanel })),
);
const CollectionsConsole = lazy(() =>
  import("./components/CollectionsConsole").then(({ CollectionsConsole }) => ({ default: CollectionsConsole })),
);
const ModelsConsole = lazy(() =>
  import("./components/ModelsConsole").then(({ ModelsConsole }) => ({ default: ModelsConsole })),
);
const PipelineConsole = lazy(() =>
  import("./components/PipelineConsole").then(({ PipelineConsole }) => ({ default: PipelineConsole })),
);

function WorkspacePanelFallback() {
  return (
    <div className="mx-auto flex w-full max-w-6xl items-center gap-2 px-3 py-8 text-sm text-[var(--text-muted)] md:px-6" role="status">
      <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]" />
      Loading workspace…
    </div>
  );
}

function DeferredRoutePanel({ routeId, pathname, locale }: { routeId: string; pathname: string; locale: Locale }) {
  const isUnknown = routeId === "not-found" || routeId === "legacy-root";
  return (
    <section className="ui-empty-state mx-auto my-8 w-[min(100%-2rem,48rem)]" aria-labelledby="deferred-route-title" data-route-state="unavailable">
      <div className="ui-empty-state__icon" aria-hidden="true"><AlertTriangle className="h-5 w-5" /></div>
      <h1 id="deferred-route-title">
        {isUnknown
          ? (locale === "vi" ? "Đường dẫn chưa được hỗ trợ" : "Route not supported")
          : (locale === "vi" ? "Khu vực này chưa khả dụng" : "This workspace is not available yet")}
      </h1>
      <p>
        {isUnknown
          ? (locale === "vi" ? `Không có nội dung nào được tạo cho ${pathname}.` : `No workspace content was invented for ${pathname}.`)
          : (locale === "vi" ? "Khả năng này chưa được kết nối với dữ liệu thật." : "This capability is not connected to real data yet.")}
      </p>
    </section>
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

function evidenceAnchorMessageId(messageId: string): string {
  return messageId.replace(/[^a-zA-Z0-9_-]/g, "-");
}

function AppWorkspace() {
  const { locale, t } = useLocale();
  const location = useLocation();
  const navigate = useNavigate();
  const resolvedRoute = useMemo(
    () => resolveAppRoute(location.pathname, location.search, location.hash),
    [location.hash, location.pathname, location.search],
  );
  const activeView = resolvedRoute.workspaceView;
  const activeRouteId = primaryRouteId(resolvedRoute);
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
  const [shouldFocusComposer, setShouldFocusComposer] = useState(false);
  const templateOpeningSnapshotRef = useRef<TemplateOpeningSnapshot | null>(null);
  const [contextualCommandNotice, setContextualCommandNotice] = useState<string | null>(null);
  const [displayedAnswerContext, setDisplayedAnswerContext] = useState<DisplayedAnswerContext | null>(null);
  const [documentsViewMounted, setDocumentsViewMounted] = useState(activeView === "documents");
  const [pendingFocusMessageId, setPendingFocusMessageId] = useState<string | null>(null);
  const [pendingOpenVariant, setPendingOpenVariant] = useState<{ conversationId: string; messageId: string; variantId: string } | null>(null);
  const [shouldFocusLibrarySearch, setShouldFocusLibrarySearch] = useState(false);
  const [activeSidebarPanel, setActiveSidebarPanel] = useState<"research" | "library">("research");
  const [stageEventsByMessage, setStageEventsByMessage] = useState<Record<string, StageEvent[]>>({});
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(false);
  const [standaloneReaderSource, setStandaloneReaderSource] = useState<Source | null>(null);
  const [documentWorkspaceTarget, setDocumentWorkspaceTarget] = useState<DocumentWorkspaceTarget | null>(null);
  const [isScopeEditorOpen, setIsScopeEditorOpen] = useState(false);
  const [isDesktopNavigation, setIsDesktopNavigation] = useState(() =>
    typeof window === "undefined" || typeof window.matchMedia !== "function"
      ? true
      : window.matchMedia(`(min-width: ${NAVIGATION_DESKTOP_MIN_WIDTH}px)`).matches,
  );
  const { layout: navigationLayout, toggleLayout: toggleNavigationLayout } = useNavigationLayout();

  useEffect(() => {
    if (activeView === "documents") setDocumentsViewMounted(true);
  }, [activeView]);

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
    const target = translateLegacyLocation(location.pathname, location.search, location.hash);
    if (target) navigate(target, { replace: true });
  }, [location.hash, location.pathname, location.search, navigate]);

  useEffect(() => {
    if (documentWorkspaceTarget && documentWorkspaceTarget.returnView !== activeView) {
      setDocumentWorkspaceTarget(null);
    }
  }, [activeView, documentWorkspaceTarget]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const workspaceMainRef = useRef<HTMLElement>(null);
  const resetCancelRef = useRef<HTMLButtonElement>(null);
  const healthRequestRef = useRef<Promise<HealthResponse> | null>(null);
  const healthRequestSequenceRef = useRef(0);
  const lastHealthRefreshRef = useRef(0);
  const [showScrollButton, setShowScrollButton] = useState<boolean>(false);
  const isNearConversationBottomRef = useRef(true);

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
    isLegacyExample,
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
    toggleConversationBookmark,
    deleteConversation,
    importConversationRecords,
    recheckSessionContext,
    writerStatus,
    requestLibraryWriter,
    updateConversationMetadata,
    saveMessageNote,
    saveMessageFeedback,
    saveAnswerVersion,
  } = library;
  const activeConversationId = library.activeConversationId;
  // The route family carries presentation mode for a new conversation; a saved
  // conversation keeps the mode it was started in regardless of the URL.
  const routeConversationMode: ConversationMode = activeRouteId === "chat" ? "chat" : "research";
  const activeConversationMode: ConversationMode = activeRecord?.mode ?? routeConversationMode;
  const navigateWorkspaceRoute = useCallback((view: WorkspaceView, conversationId?: string | null, preserveHash = false, family?: ConversationMode) => {
    const target = routeForWorkspaceView(view, {
      conversationId: conversationId ?? (view === "conversation" ? activeConversationId : null),
      currentRouteId: resolvedRoute.id,
      family,
    });
    navigate(`${target}${preserveHash ? location.hash : ""}`);
  }, [activeConversationId, location.hash, navigate, resolvedRoute.id]);
  const answerActions = useAnswerActions({
    activeConversationId,
    toggleBookmark: toggleAnswerBookmark,
    saveNote: saveMessageNote,
    saveFeedback: saveMessageFeedback,
    saveVersion: async (target: AnswerTarget) => saveAnswerVersion(target),
  });
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
  const readerSession = useReaderSession();
  const evidenceSelectionRef = useRef<EvidenceSelection | null>(evidenceSelection);
  evidenceSelectionRef.current = evidenceSelection;
  const appliedEvidenceDeepLinkRef = useRef<string | null>(null);
  const suppressedEvidenceDeepLinkRef = useRef<string | null>(null);
  const evidenceReturnFocusRef = useRef<{ messageId: string; citationIndex: number } | null>(null);
  const evidenceReturnElementRef = useRef<HTMLElement | null>(null);
  const evidenceFocusRestorePendingRef = useRef(false);
  const standaloneReaderReturnFocusRef = useRef<string | null>(null);
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
    if (!isLibraryReady) return;
    const routeConversationId = resolvedRoute.params.conversationId;
    if (!routeConversationId || routeConversationId === activeConversationId) return;
    const conversation = conversations.find((candidate) => candidate.id === routeConversationId);
    if (!conversation) {
      setContextualCommandNotice(locale === "vi"
        ? "Cuộc trò chuyện trong đường dẫn không khả dụng; không chọn cuộc trò chuyện khác."
        : "The conversation in this route is unavailable; no other conversation was selected.");
      return;
    }
    void selectConversation(conversation);
  }, [activeConversationId, conversations, isLibraryReady, locale, resolvedRoute.params.conversationId, selectConversation]);
  useEffect(() => {
    if (!isLibraryReady) return;
    const hash = location.hash;
    if (!hash) {
      suppressedEvidenceDeepLinkRef.current = null;
      return;
    }
    if (suppressedEvidenceDeepLinkRef.current === hash) return;
    const link = parseEvidenceDeepLink(hash);
    if (!link) return;
    const conversationId = link.conversationId ?? activeConversationId;
    const conversation = conversations.find((candidate) => candidate.id === conversationId);
    const pendingKey = hash + "|pending-conversation";
    if (!conversation) {
      if (appliedEvidenceDeepLinkRef.current === hash) return;
      appliedEvidenceDeepLinkRef.current = hash;
      setEvidenceSelection(null);
      setIsEvidenceOpen(false);
      setContextualCommandNotice(locale === "vi" ? "Cuộc trò chuyện trong liên kết không còn khả dụng; không chọn câu trả lời khác." : "The conversation in this link is unavailable; no other answer was selected.");
      return;
    }
    if (conversation.id !== activeConversationId) {
      if (appliedEvidenceDeepLinkRef.current === pendingKey) return;
      appliedEvidenceDeepLinkRef.current = pendingKey;
      navigateWorkspaceRoute("conversation", conversation.id, true, conversation.mode);
      void selectConversation(conversation);
      return;
    }
    if (appliedEvidenceDeepLinkRef.current === hash) {
      setIsEvidenceOpen(true);
      return;
    }

    const message = messages.find(
      (candidate) => candidate.id === link.messageId || evidenceAnchorMessageId(candidate.id) === link.messageId,
    );
    navigateWorkspaceRoute("conversation", conversation.id, true, conversation.mode);
    setContextualCommandNotice(null);
    if (!message) {
      appliedEvidenceDeepLinkRef.current = hash;
      setEvidenceSelection(null);
      setIsEvidenceOpen(false);
      setContextualCommandNotice(locale === "vi" ? "Tin nhắn trong liên kết không còn khả dụng; không chọn câu trả lời khác." : "The message in this link is unavailable; no other answer was selected.");
      return;
    }

    const variant = link.variantId
      ? activeRecord?.variants?.find((candidate) => candidate.id === link.variantId && candidate.originMessageId === message.id && candidate.status !== "error")
      : undefined;
    const sources = link.variantId ? variant?.sources : message.sources;
    const source = sources?.[link.citationIndex];
    const sourceIdentityMatches = source && (!link.sourceKey || sourceMatchesSelection(source, {
      conversationId,
      messageId: message.id,
      ...(link.variantId ? { variantId: link.variantId } : {}),
      citationIndex: link.citationIndex,
      sourceKey: link.sourceKey ?? "",
    }, link.citationIndex));
    const exactVariant = Boolean(!link.variantId || variant);
    const exactSource = Boolean(exactVariant && source && sourceIdentityMatches);
    const selection: EvidenceSelection = exactSource
      ? createEvidenceSelection(conversationId, message.id, link.citationIndex, source!, variant?.id)
      : {
          conversationId,
          messageId: message.id,
          ...(link.variantId ? { variantId: link.variantId } : {}),
          citationIndex: link.citationIndex,
          sourceKey: link.sourceKey ?? "linked-source-unavailable",
        };
    appliedEvidenceDeepLinkRef.current = hash;
    setEvidenceSelection(selection);
    setIsEvidenceOpen(true);
    if (variant) setPendingOpenVariant({ conversationId, messageId: message.id, variantId: variant.id });
    else setPendingOpenVariant(null);
    if (!exactVariant) {
      setContextualCommandNotice(locale === "vi" ? "Phiên bản trong liên kết không còn khả dụng; không chọn phiên bản khác." : "The answer variant in this link is unavailable; no other variant was selected.");
    } else if (!source || !sourceIdentityMatches) {
      setContextualCommandNotice(locale === "vi" ? "Nguồn trong liên kết không còn khớp với citation đã chọn; hãy chọn lại đúng nguồn." : "The source in this link no longer matches the selected citation; choose the exact source again.");
    }
  }, [activeConversationId, activeRecord?.variants, conversations, isLibraryReady, locale, location.hash, messages, navigateWorkspaceRoute, selectConversation, setEvidenceSelection]);
  const handleInspectSource = useCallback(
    (selection: Omit<EvidenceSelection, "conversationId">) => {
      cancelEvidenceFocusRestore();
      evidenceReturnFocusRef.current = {
        messageId: selection.messageId,
        citationIndex: selection.citationIndex,
      };
      evidenceReturnElementRef.current = document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
      const fullSelection = { conversationId: activeConversationId, ...selection };
      const anchor = buildEvidenceDeepLinkForSelection(fullSelection);
      if (anchor) {
        suppressedEvidenceDeepLinkRef.current = window.location.hash || null;
        appliedEvidenceDeepLinkRef.current = anchor;
        navigate(`${location.pathname}${location.search}${anchor}`, { replace: true });
      }
      setEvidenceSelection(fullSelection);
      if (!selection.variantId) setPendingOpenVariant(null);
      setIsEvidenceOpen(true);
    },
    [activeConversationId, cancelEvidenceFocusRestore, location.pathname, location.search, navigate, setEvidenceSelection],
  );
  const handleCloseEvidence = useCallback(() => {
    cancelEvidenceFocusRestore();
    const standaloneReturnFocusId = standaloneReaderReturnFocusRef.current;
    standaloneReaderReturnFocusRef.current = null;
    evidenceFocusRestorePendingRef.current = !standaloneReturnFocusId;
    suppressedEvidenceDeepLinkRef.current = window.location.hash || null;
    setIsEvidenceOpen(false);
    setStandaloneReaderSource(null);
    setDocumentWorkspaceTarget(null);
    readerSession.clear();
    navigate(`${window.location.pathname}${window.location.search}`, { replace: true });
    if (standaloneReturnFocusId) {
      window.requestAnimationFrame(() => document.getElementById(standaloneReturnFocusId)?.focus({ preventScroll: true }));
    }
  }, [cancelEvidenceFocusRestore, location.pathname, location.search, navigate, readerSession]);

  const handleOpenStandaloneSource = useCallback((source: Source, returnFocusId?: string) => {
    cancelEvidenceFocusRestore();
    navigate(`${location.pathname}${location.search}`, { replace: true });
    setDocumentWorkspaceTarget(null);
    standaloneReaderReturnFocusRef.current = returnFocusId ?? null;
    setStandaloneReaderSource(source);
    setIsEvidenceOpen(true);
  }, [cancelEvidenceFocusRestore, location.pathname, location.search, navigate]);

  const handleOpenDocumentWorkspace = useCallback((target: DocumentWorkspaceTarget) => {
    cancelEvidenceFocusRestore();
    standaloneReaderReturnFocusRef.current = null;
    navigate(`${location.pathname}${location.search}`, { replace: true });
    setIsEvidenceOpen(false);
    setStandaloneReaderSource(null);
    setDocumentWorkspaceTarget(target);
    readerSession.clear();
  }, [cancelEvidenceFocusRestore, location.pathname, location.search, navigate, readerSession]);

  const handleCloseDocumentWorkspace = useCallback(() => {
    const target = documentWorkspaceTarget;
    standaloneReaderReturnFocusRef.current = null;
    setDocumentWorkspaceTarget(null);
    readerSession.clear();
    window.requestAnimationFrame(() => {
      if (target?.returnFocusId) document.getElementById(target.returnFocusId)?.focus();
    });
  }, [documentWorkspaceTarget, readerSession]);
  const handleOpenCurrentSource = useCallback((source: Source) => {
    const chunkId = source.stored_snapshot?.chunk_id ?? source.chunk_id;
    const { stored_snapshot: _storedSnapshot, ...currentSource } = source;
    handleOpenStandaloneSource({ ...currentSource, chunk_id: chunkId });
  }, [handleOpenStandaloneSource]);
  const handleOpenSavedEvidence = useCallback((item: EvidenceItem) => {
    handleOpenStandaloneSource({
      citation: item.citation,
      text_preview: item.excerpt,
      text: item.excerpt,
      chunk_id: item.chunkId ?? null,
      document_id: item.documentId ?? null,
      ticker: item.ticker ?? null,
      section: item.section ?? null,
      filing_date: item.filingDate ?? null,
      report_date: item.reportDate ?? null,
      source_url: item.sourceUrl ?? null,
      sec_index_url: item.secIndexUrl ?? null,
      ...(item.chunkTextHash ? { chunk_text_hash: item.chunkTextHash } : {}),
      stored_snapshot: {
        chunk_id: item.chunkId ?? null,
        ...(item.documentRevision ? { document_revision: item.documentRevision } : {}),
        ...(item.sourceSetRevision ? { source_set_revision: item.sourceSetRevision } : {}),
        ...(item.representation ? { representation: item.representation } : {}),
        ...(item.coverageStatus ? { coverage_status: item.coverageStatus } : {}),
        ...(item.locationStatus ? { location_status: item.locationStatus } : {}),
        ...(item.snapshotState ? { snapshot_state: item.snapshotState } : {}),
      },
    }, evidenceItemFocusId(item.id));
  }, [handleOpenStandaloneSource]);

  const handleOpenCurrentEvidence = useCallback(async (item: EvidenceItem): Promise<CurrentSourceCheckResult> => {
    if (!item.chunkId) {
      return { status: "unknown", message: locale === "vi" ? "Snapshot này không có chunk ID exact nên không thể mở corpus hiện tại." : "This snapshot has no exact chunk ID, so the current corpus cannot be opened." };
    }
    try {
      const detail = await getChunkDetail(item.chunkId);
      if (detail.chunk_id !== item.chunkId || (item.documentId && detail.document_id !== item.documentId)) {
        return { status: "stale", message: locale === "vi" ? "Định danh nguồn hiện tại không khớp; chỉ giữ bản chụp lịch sử." : "The current source identity did not match; only the historical snapshot remains available." };
      }
      if (item.chunkTextHash && item.chunkTextHash !== detail.chunk_text_hash) {
        return { status: "stale", message: locale === "vi" ? "Hash văn bản đã thay đổi; chỉ giữ bản chụp lịch sử." : "The text hash changed; only the historical snapshot remains available." };
      }
      handleOpenStandaloneSource({
        citation: item.citation,
        text_preview: detail.text_preview,
        text: detail.text,
        chunk_id: detail.chunk_id,
        document_id: detail.document_id,
        ticker: detail.ticker,
        section: detail.section,
        filing_date: detail.filing_date,
        report_date: detail.report_date,
        source_url: detail.source_url,
        sec_index_url: detail.sec_index_url,
        chunk_text_hash: detail.chunk_text_hash,
      }, evidenceCurrentSourceFocusId(item.id));
      return { status: "current" };
    } catch (error) {
      const status = error instanceof ApiError ? error.status : null;
      if (status === 404) return { status: "missing", message: locale === "vi" ? "Chunk exact không còn trong corpus; bản chụp lịch sử vẫn đọc được." : "The exact chunk is missing from the corpus; the historical snapshot remains readable." };
      if (status === 409) return { status: "unavailable", message: locale === "vi" ? "Chunk ID không xác định duy nhất; không mở nguồn gần kề." : "The chunk ID is not uniquely resolvable; no nearby source was substituted." };
      return { status: "unavailable", message: locale === "vi" ? "Không thể kiểm tra corpus hiện tại; bản chụp lịch sử vẫn được giữ." : "The current corpus could not be checked; the historical snapshot is preserved." };
    }
  }, [handleOpenStandaloneSource, locale]);
  useEffect(() => {
    if (isEvidenceOpen || !evidenceFocusRestorePendingRef.current) return;
    evidenceFocusRestorePendingRef.current = false;
    const target = evidenceReturnFocusRef.current;
    let attempts = 0;
    let timeout: number | null = null;
    const restoreFocus = () => {
      const retainedOpener = evidenceReturnElementRef.current;
      const opener = retainedOpener?.isConnected
        ? retainedOpener
        : target
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

      const requestId = ++healthRequestSequenceRef.current;
      const request = checkHealth(signal)
        .then((health) => {
          if (requestId === healthRequestSequenceRef.current) applyHealth(health);
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
    const requestId = ++healthRequestSequenceRef.current;

    const initData = async () => {
      try {
        const health = await checkHealth(controller.signal);
        if (requestId !== healthRequestSequenceRef.current || controller.signal.aborted) return;
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

  // Adopted backend history moves the user into the conversation view once,
  // but never away from a view explicitly requested through the URL.
  const historyAdoptedRef = useRef(false);
  useEffect(() => {
    if (!historyAdoptedRef.current && messages.length > 0 && isLibraryReady) {
      historyAdoptedRef.current = true;
      if (activeView === "overview") navigateWorkspaceRoute("conversation");
    }
  }, [activeView, isLibraryReady, messages.length, navigateWorkspaceRoute]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const reduced = prefersReducedMotion();
    messagesEndRef.current?.scrollIntoView({
      behavior: reduced ? "auto" : behavior,
    });
  }, []);

  useEffect(() => {
    if (activeView !== "conversation" || !isNearConversationBottomRef.current) return;
    if (!isLoading) return;

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
    if (!pendingFocusMessageId || activeView !== "conversation") return;
    let frame = 0;
    let attempts = 0;
    const focusMessage = () => {
      const target = document.getElementById(`message-${pendingFocusMessageId}`);
      if (!target && attempts < 12) {
        attempts += 1;
        frame = window.requestAnimationFrame(focusMessage);
        return;
      }
      target?.scrollIntoView({
        behavior: prefersReducedMotion() ? "auto" : "smooth",
        block: "start",
      });
      target?.focus({ preventScroll: true });
      if (target) setPendingFocusMessageId(null);
    };
    frame = window.requestAnimationFrame(focusMessage);
    return () => window.cancelAnimationFrame(frame);
  }, [pendingFocusMessageId, activeView, messages.length]);

  useEffect(() => {
    if (!shouldFocusComposer || templateToCustomize !== null || activeView !== "conversation") return;
    const timeout = window.setTimeout(() => {
      const composer = document.getElementById("chat-textarea");
      if (!composer) return;
      composer.focus();
      setShouldFocusComposer(false);
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [activeView, shouldFocusComposer, templateToCustomize]);

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

    const requestSnapshot: RequestSnapshot = {
      ...(snapshot ?? {
        ticker: selectedTicker,
        section: selectedSection,
        topK,
        enableComparative,
        answerLanguage: locale,
      }),
      answerLanguage: snapshot?.answerLanguage ?? locale,
      // The submitted mode is captured from the page the question was asked
      // on; it is presentation provenance only and never changes retrieval.
      mode: activeConversationMode,
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

    navigateWorkspaceRoute("conversation");
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
    activeConversationMode,
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

  // The mode the user asked to start in; a chat start lands on the direct
  // /chat page, a research start keeps the existing /research overview.
  const pendingNewConversationModeRef = useRef<ConversationMode>(activeConversationMode);
  const confirmNewConversation = useCallback(async (startMode?: ConversationMode) => {
    const mode = startMode ?? pendingNewConversationModeRef.current;
    setShowResetDialog(false);
    await startNewConversation();
    if (mode === "chat") {
      navigate(routePath("chat"));
    } else {
      navigateWorkspaceRoute("overview");
    }
    setActiveSidebarPanel("research");
    try {
      await refreshHealth(true);
    } catch (e) {
      setIsBackendConnected(false);
      setIsPipelineReady(false);
    }
  }, [navigate, navigateWorkspaceRoute, refreshHealth, startNewConversation]);

  const requestNewConversation = useCallback((mode: ConversationMode = activeConversationMode) => {
    pendingNewConversationModeRef.current = mode;
    if (messages.length === 0) {
      void confirmNewConversation(mode);
      return;
    }
    setShowResetDialog(true);
  }, [activeConversationMode, confirmNewConversation, messages.length]);

  const handleSelectConversation = useCallback(
    async (conversation: ConversationRecord) => {
      if (conversation.messages.length) {
        // Reopen in the family the conversation was started in; its mode is
        // presentation provenance and never regenerates the stored answer.
        navigateWorkspaceRoute("conversation", conversation.id, false, conversation.mode);
      } else if (conversation.mode === "chat") {
        navigate(routePath("chat"));
      } else {
        navigateWorkspaceRoute("overview", conversation.id);
      }
      if (conversation.id === activeConversationId) return;
      await selectConversation(conversation);
    },
    [activeConversationId, navigate, navigateWorkspaceRoute, selectConversation],
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
      navigateWorkspaceRoute("conversation", conversation.id, false, conversation.mode);
    },
    [activeConversationId, conversations, navigateWorkspaceRoute, selectConversation],
  );

  // Reopen an immutable answer variant by durable conversation/message/variant
  // IDs. The renderer receives the pending ID for one render and never falls
  // back to the latest answer by position.
  const handleOpenVariant = useCallback(
    async (conversationId: string, messageId: string, variantId: string) => {
      const conversation = conversations.find((item) => item.id === conversationId);
      const message = conversation?.messages.find((item) => item.id === messageId && item.sender === "assistant");
      const variant = conversation?.variants?.find((item) => item.id === variantId && item.originMessageId === messageId);
      if (!conversation || !message || !variant || variant.status === "error") {
        setContextualCommandNotice(locale === "vi" ? "Phiên bản đã lưu không còn khả dụng; bản lưu không bị thay thế." : "That saved version is unavailable; the stored snapshot was not replaced.");
        return;
      }
      setPendingOpenVariant({ conversationId, messageId, variantId });
      if (conversation.id !== activeConversationId) await selectConversation(conversation);
      setPendingFocusMessageId(messageId);
      navigateWorkspaceRoute("conversation", conversation.id, false, conversation.mode);
    },
    [activeConversationId, conversations, locale, navigateWorkspaceRoute, selectConversation],
  );

  useEffect(() => {
    if (!pendingOpenVariant || activeView !== "conversation" || activeConversationId !== pendingOpenVariant.conversationId) return;
    const message = messages.find((item) => item.id === pendingOpenVariant.messageId && item.sender === "assistant");
    const variant = activeRecord?.variants?.find((item) => item.id === pendingOpenVariant.variantId && item.originMessageId === pendingOpenVariant.messageId);
    if (!message || !variant || variant.status === "error") {
      setContextualCommandNotice(locale === "vi" ? "Không thể mở phiên bản exact; bản lưu lịch sử vẫn được giữ nguyên." : "The exact saved version could not be opened; its historical snapshot remains preserved.");
      setPendingOpenVariant(null);
      return;
    }
    setDisplayedAnswerContext({ conversationId: activeConversationId, messageId: message.id, variantId: variant.id });
    const frame = window.requestAnimationFrame(() => setPendingOpenVariant(null));
    return () => window.cancelAnimationFrame(frame);
  }, [activeConversationId, activeRecord?.variants, activeView, locale, messages, pendingOpenVariant]);

  const handleContinueResearch = useCallback(
    async (conversation: ConversationRecord) => {
      if (conversation.id !== activeConversationId) await selectConversation(conversation);
      const latestUser = [...conversation.messages].reverse().find((message) => message.sender === "user");
      const latestContext = [...conversation.messages].reverse().find((message) => message.requestSnapshot)?.requestSnapshot;
      if (latestContext) {
        patchScope({
          ticker: latestContext.ticker,
          section: latestContext.section,
          topK: latestContext.topK,
          enableComparative: latestContext.enableComparative,
        });
      }
      setInputText(conversation.draft.trim() || latestUser?.text || "");
      navigateWorkspaceRoute("conversation", conversation.id, false, conversation.mode);
      window.requestAnimationFrame(() => document.getElementById("chat-textarea")?.focus());
    },
    [activeConversationId, navigateWorkspaceRoute, patchScope, selectConversation, setInputText],
  );

  const handleExportConversation = useCallback((conversation: ConversationRecord) => {
    downloadConversationMarkdown(conversation);
  }, []);

  const handleExportBackup = useCallback(() => {
    downloadConversationBackup(conversations);
  }, [conversations]);

  const handleImportBackup = useCallback(
    async (bundle: ConversationBackupBundle) => {
      const importedCollections = importEvidenceCollections(bundle.collections);
      preflightEvidenceCollectionsImport(importedCollections);
      const result = await importConversationRecords(bundle.conversations);
      if (result.imported === 0) throw new Error("No conversation could be imported into storage.");
      if (importedCollections.length === 0) return { ...result, evidencePersisted: 0, evidenceFailed: 0, evidenceWarning: null };
      try {
        mergeEvidenceCollections(importedCollections);
        return { ...result, evidencePersisted: importedCollections.length, evidenceFailed: 0, evidenceWarning: null };
      } catch (error) {
        return {
          ...result,
          evidencePersisted: 0,
          evidenceFailed: importedCollections.length,
          evidenceWarning: error instanceof Error ? error.message : "Evidence collections were not imported.",
        };
      }
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
      toggleConversationBookmark(conversationId, messageId);
    },
    [activeConversationId, conversations, toggleAnswerBookmark, toggleConversationBookmark],
  );

  const handleSaveMessageNote = useCallback((messageId: string, note: string) => {
    const target: AnswerTarget = { conversationId: activeConversationId, messageId, variantId: null };
    void answerActions.note(target, note);
  }, [activeConversationId, answerActions]);

  const handleMessageFeedback = useCallback((messageId: string, feedback: MessageFeedback | undefined) => {
    const target: AnswerTarget = {
      conversationId: activeConversationId,
      messageId,
      variantId: feedback?.variantId ?? null,
    };
    void answerActions.feedback(target, feedback);
    recordAnalyticsEvent({
      kind: "feedback",
      status: feedback
        ? `${feedback.rating}${feedback.category ? `:${feedback.category}` : ""}`
        : "cleared",
    });
  }, [activeConversationId, answerActions]);

  const handleSaveAnswerVersion = useCallback(async (target: { messageId: string; variantId: string | null }) => {
    const identity: AnswerTarget = {
      conversationId: activeConversationId,
      messageId: target.messageId,
      variantId: target.variantId,
    };
    await answerActions.saveVersion(identity);
  }, [activeConversationId, answerActions]);

  const handleViewSavedVersion = useCallback(() => {
    navigateWorkspaceRoute("library");
    setActiveSidebarPanel("library");
    setIsEvidenceOpen(false);
    setStandaloneReaderSource(null);
  }, [navigateWorkspaceRoute]);

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

  const handleConversationSearchFocused = useCallback(() => {
    setShouldFocusLibrarySearch(false);
  }, []);

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
    setShouldFocusComposer(true);
    navigateWorkspaceRoute("conversation");
  }, [activeConversationId, closeTemplateQuestion, enableComparative, locale, navigateWorkspaceRoute, patchScope, selectedSection, selectedTicker, setInputText, topK]);

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
    if (view !== "conversation" && isLoading) {
      // A route change is a request boundary. Stop the active stream before
      // unmounting its conversation surface so late SSE events cannot paint
      // into a different workspace route.
      cancelActiveRequest();
    }
    navigateWorkspaceRoute(view);
    setIsSidebarOpen(false);
    if (view !== "conversation") setIsEvidenceOpen(false);
    standaloneReaderReturnFocusRef.current = null;
    setStandaloneReaderSource(null);
    setDocumentWorkspaceTarget(null);
    if (view === "library") setActiveSidebarPanel("library");
    if (view === "overview" || view === "conversation" || view === "search" || view === "documents" || view === "retrieval" || view === "architecture" || view === "models" || view === "pipeline") {
      setActiveSidebarPanel("research");
    }
  }, [cancelActiveRequest, isLoading, navigateWorkspaceRoute]);

  const handleSelectShellRoute = useCallback((routeId: ShellRouteId) => {
    const nextView = resolveAppRoute(routePath(routeId)).workspaceView;
    if (nextView !== "conversation" && isLoading) cancelActiveRequest();
    navigate(routePath(routeId));
    setIsSidebarOpen(false);
    if (nextView !== "conversation") setIsEvidenceOpen(false);
    standaloneReaderReturnFocusRef.current = null;
    setStandaloneReaderSource(null);
    setDocumentWorkspaceTarget(null);
    setActiveSidebarPanel(routeId === "collections" ? "library" : "research");
  }, [cancelActiveRequest, isLoading, navigate]);

  const handleSelectTheme = useCallback((nextTheme: ThemePreference) => {
    setThemePreference(nextTheme);
  }, []);

  const handleReturnToConversation = useCallback(() => {
    navigateWorkspaceRoute("conversation");
  }, [navigateWorkspaceRoute]);

  const handleSearchScopeChange = useCallback((ticker: string | null, section: string | null) => {
    setSelectedTicker(ticker);
    setSelectedSection(section);
  }, []);


  const handleUseRetrievalQuestion = useCallback((question: string, scope?: { ticker: string | null; section: string | null }) => {
    if (scope) {
      patchScope(scope);
    }
    setInputText(question);
    navigateWorkspaceRoute("conversation");
    window.requestAnimationFrame(() => {
      document.getElementById("chat-textarea")?.focus();
    });
  }, [navigateWorkspaceRoute, patchScope, setInputText]);

  const handleUseRelatedResearch = useCallback((question: string, scope: { ticker: string | null; section: string | null }) => {
    if (inputTextRef.current.trim()) {
      setContextualCommandNotice(locale === "vi"
        ? "Bản nháp hiện tại được giữ nguyên; hãy gửi hoặc xóa bản nháp trước khi chọn nghiên cứu tiếp theo."
        : "Your current draft was preserved; send or clear it before choosing related research.");
      return;
    }
    handleUseRetrievalQuestion(question, scope);
  }, [handleUseRetrievalQuestion, locale]);

  const handleSaveRetrievedEvidence = useCallback((source: Source) => {
    try {
      saveEvidence(source, { provenance: snapshotProvenanceFromSource(source) });
      setContextualCommandNotice(locale === "vi" ? "Đã lưu evidence vào Thư viện." : "Evidence saved to Library.");
    } catch (error) {
      setContextualCommandNotice(error instanceof Error ? error.message : (locale === "vi" ? "Không thể lưu evidence." : "Could not save evidence."));
    }
  }, [locale]);

  const handlePaletteNavigate = useCallback((routeId: ShellRouteId) => {
    navigate(routePath(routeId));
    if (routeId === "chat" || routeId === "research") {
      window.requestAnimationFrame(() => document.getElementById("chat-textarea")?.focus());
    }
  }, [navigate]);

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
        return { sources, selectedIndex: evidenceSelection.citationIndex, selection: evidenceSelection, unavailable: false, unavailableReason: undefined };
      }
      const unavailableReason = !message
        ? (locale === "vi" ? "Tin nhắn trong liên kết không còn khả dụng." : "The linked message is unavailable.")
        : evidenceSelection.variantId && !variant
          ? (locale === "vi" ? "Phiên bản trong liên kết không còn khả dụng; không chọn phiên bản khác." : "The linked answer variant is unavailable; no other variant was selected.")
          : (!sources?.[evidenceSelection.citationIndex]
            ? (locale === "vi" ? "Citation trong liên kết không còn tồn tại ở vị trí exact." : "The linked citation is no longer available at that exact position.")
            : (locale === "vi" ? "Nguồn trong liên kết không khớp với identity hiện tại." : "The linked source does not match the current source identity."));
      return { sources: sources ?? [] as Source[], selectedIndex: -1, selection: evidenceSelection, unavailable: true, unavailableReason };
    }
    const latestMessage = [...messages].reverse().find((message) => message.sender === "assistant" && message.sources?.length);
    return latestMessage?.sources?.length && latestMessage.sources[0]
      ? {
          sources: latestMessage.sources,
          selectedIndex: 0,
          selection: createEvidenceSelection(activeConversationId, latestMessage.id, 0, latestMessage.sources[0]),
          unavailable: false,
          unavailableReason: undefined,
        }
      : null;
  }, [activeConversationId, activeRecord?.variants, evidenceSelection, locale, messages]);
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
          navigateWorkspaceRoute("conversation");
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
              provenance: snapshotProvenanceFromSource(target.source),
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
        navigateWorkspaceRoute("conversation");
        setIsScopeEditorOpen(true);
      },
    });
    return commands;
  }, [commandEvidenceTarget, hasGroundedAnswer, locale, navigateWorkspaceRoute, setEvidenceSelection]);
  // The latest answer the workspace can truthfully summarize: completed,
  // non-error, with text. Insight tiles and follow-ups both read from it.
  const latestCompletedAnswer = useMemo(
    () =>
      [...messages].reverse().find((message) =>
        message.sender === "assistant" && !message.isStreaming && !message.error && message.text.trim(),
      ) ?? null,
    [messages],
  );
  const followUpQuestions = useMemo(() => {
    if (!latestCompletedAnswer) return [];
    return buildRelatedResearchSuggestions(latestCompletedAnswer, sections).slice(0, 4);
  }, [latestCompletedAnswer, sections]);
  const showContextBanner =
    activeView === "conversation" && hasExchanges &&
    (sessionContext === "checking" || isReadOnly);
  const showComposer = !["retrieval", "documents", "library", "search", "architecture", "evaluation", "analytics", "system", "models", "pipeline"].includes(activeView);
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
          isLegacyExample
            ? (locale === "vi" ? "Mẫu cũ — không phải bằng chứng trực tiếp. Bản ghi được giữ ở chế độ chỉ đọc vì không thể xác minh nguồn sống." : "Legacy example — not live evidence. This record is preserved read-only because its live source could not be verified.")
            : sessionContext === "missing"
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

  const hasEvidenceContext = isEvidenceOpen && (
    (activeView === "conversation" && evidenceTarget) ||
    (activeView !== "conversation" && standaloneReaderSource)
  );
  const evidenceInline = isDesktopNavigation && (typeof window === "undefined" || window.innerWidth > 1024);
  const workbenchContext = documentWorkspaceTarget ? (
    <RouteDocumentContext
      target={documentWorkspaceTarget}
      onBack={handleCloseDocumentWorkspace}
      readerSession={readerSession}
    />
  ) : hasEvidenceContext ? (
    activeView === "conversation" && evidenceTarget ? (
      <EvidenceWorkspaceRail
        sources={evidenceTarget.sources}
        selectedIndex={evidenceTarget.selectedIndex}
        unavailable={evidenceTarget.unavailable}
        unavailableReason={evidenceTarget.unavailableReason}
        messageId={evidenceTarget.selection.messageId}
        conversationId={evidenceTarget.selection.conversationId}
        isOpen={isEvidenceOpen}
        presentation="workbench"
        onClose={handleCloseEvidence}
        readerSession={readerSession}
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
    ) : standaloneReaderSource ? (
      <EvidenceWorkspaceRail
        sources={[standaloneReaderSource]}
        selectedIndex={0}
        messageId={undefined}
        conversationId={undefined}
        isOpen={isEvidenceOpen}
        presentation="workbench"
        onClose={handleCloseEvidence}
        readerSession={readerSession}
        onOpenCurrentSource={handleOpenCurrentSource}
        onSelectIndex={() => undefined}
      />
    ) : null
  ) : null;
  const workbenchContextKind = documentWorkspaceTarget
    ? "document"
    : hasEvidenceContext
      ? "evidence"
      : undefined;

  const overlays = (
    <>
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
                onClick={() => void confirmNewConversation(pendingNewConversationModeRef.current)}
                className="min-h-10 rounded-lg primary-action-button px-4 py-2 text-sm font-semibold"
              >
                Start new conversation
              </button>
            </div>
          </div>
        </div>
      </ModalDialog>
    </>
  );

  return (
    <ApplicationWorkspace
      navigation={
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
        onToggleNavigationLayout={toggleNavigationLayout}
        isClearingSession={isClearingSession}
        activePanel={activeSidebarPanel}
        onChangePanel={setActiveSidebarPanel}
        activeRouteId={activeRouteId}
        onSelectRoute={handleSelectShellRoute}
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
      }
      header={
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
          selectedTicker={selectedTicker}
          modelLabel={[...messages].reverse().find((message) => message.sender === "assistant" && message.model_used)?.model_used ?? null}
        />
      }
      context={workbenchContext}
      contextKind={workbenchContextKind}
      target={documentWorkspaceTarget}
      footer={activeView !== "conversation" ? composer : null}
      overlays={overlays}
    >
      {/* Content stream area */}
      <main
          aria-label="Research workspace"
          data-route-id={resolvedRoute.id}
          data-route-path={location.pathname}
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
          {isLegacyExample && (
            <div className="mx-auto mt-3 max-w-6xl rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-[var(--text-primary)]" role="alert">
              {locale === "vi"
                ? "Mẫu cũ — không phải bằng chứng trực tiếp. Bản ghi được giữ ở chế độ chỉ đọc; hãy bắt đầu phiên mới để dùng dữ liệu live."
                : "Legacy example — not live evidence. This record is preserved read-only; start a new conversation to use live data."}
            </div>
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
            className={`workspace-main-grid ${activeView === "conversation" ? "workspace-main-grid--conversation" : ""} ${evidenceInline && ((activeView === "conversation" && evidenceTarget) || (activeView !== "conversation" && standaloneReaderSource)) && isEvidenceOpen ? "workspace-main-grid--with-evidence" : ""}`}
          >
            <div className="workspace-primary-column">
              <Suspense fallback={<WorkspacePanelFallback />}>
                {resolvedRoute.isDeferred || !resolvedRoute.isKnown ? (
                  <DeferredRoutePanel routeId={resolvedRoute.id} pathname={location.pathname} locale={locale} />
                ) : documentsViewMounted || activeView === "documents" ? (
                  <div hidden={activeView !== "documents"} aria-hidden={activeView !== "documents"}>
                    <DocumentExplorerPanel
                      tickers={tickers}
                      sections={sections}
                      companyCount={healthData?.corpus?.searchable_company_count ?? null}
                      chunkCount={healthData?.corpus?.indexed_chunk_count ?? null}
                      onOpenDocument={handleOpenDocumentWorkspace}
                      onOpenSource={handleOpenStandaloneSource}
                      onSaveEvidence={handleSaveRetrievedEvidence}
                    />
                  </div>
                ) : null}
                {activeView === "search" ? (
              <>
                <div>
                  <DiscoverySearchPage
                    tickers={tickers}
                    sections={sections}
                    isBackendConnected={isBackendConnected}
                    onUseQuestion={handleUseRetrievalQuestion}
                    onOpenDocument={handleOpenDocumentWorkspace}
                    onOpenSource={handleOpenStandaloneSource}
                    onSaveEvidence={handleSaveRetrievedEvidence}
                  />
                </div>
              </>
                ) : activeView === "architecture" ? (
              <ArchitecturePanel />
                ) : activeView === "retrieval" ? (
              resolvedRoute.id === "reranker" ? (
                <RerankerPanel
                  tickers={tickers}
                  sections={sections}
                  isBackendConnected={isBackendConnected}
                  onUseQuestion={handleUseRetrievalQuestion}
                  onOpenDocument={handleOpenDocumentWorkspace}
                  onOpenSource={handleOpenStandaloneSource}
                  onSaveEvidence={handleSaveRetrievedEvidence}
                />
              ) : (
                <RetrievalPanel
                  tickers={tickers}
                  sections={sections}
                  isBackendConnected={isBackendConnected}
                  onUseQuestion={handleUseRetrievalQuestion}
                  onOpenDocument={handleOpenDocumentWorkspace}
                  onOpenSource={handleOpenStandaloneSource}
                  onSaveEvidence={handleSaveRetrievedEvidence}
                />
              )
                ) : activeView === "documents" ? (
              null
                ) : activeView === "library" ? (
              <CollectionsConsole
                librarySlot={
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
                    onOpenVariant={handleOpenVariant}
                    onContinueResearch={handleContinueResearch}
                    onOpenEvidence={handleOpenSavedEvidence}
                    onOpenCurrentSource={handleOpenCurrentEvidence}
                    onClose={() => navigateWorkspaceRoute("overview")}
                  />
                }
                onDownloadBackup={handleExportBackup}
                focusConversationSearch={shouldFocusLibrarySearch}
                onConversationSearchFocused={handleConversationSearchFocused}
              />
                ) : activeView === "models" ? (
              <ModelsConsole />
                ) : activeView === "pipeline" ? (
              <PipelineConsole healthData={healthData} />
                ) : activeView === "system" ? (
              <SystemInfoPanel
                onOpenDocuments={() => handleSelectWorkspaceView("documents")}
                onOpenRetrieval={() => handleSelectWorkspaceView("retrieval")}
                onOpenEvaluation={() => handleSelectWorkspaceView("evaluation")}
              />
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
            /* Active conversation (Chat or Research family) */
            <ConversationPageShell
              mode={activeConversationMode}
              insightMessage={latestCompletedAnswer}
              followUps={followUpQuestions}
              onNewConversation={() => requestNewConversation(activeConversationMode)}
              onOpenHistory={() => navigateWorkspaceRoute("library")}
              onSelectFollowUp={handleUseRelatedResearch}
              scrollContainerRef={scrollContainerRef}
              messagesEndRef={messagesEndRef}
              canShowFollowUps={followUpQuestions.length > 0 && !isLoading && !isStreaming}
              scrollButton={showScrollButton ? (
                <button
                  type="button"
                  onClick={() => scrollToBottom()}
                  className="ui-message-enter fixed bottom-32 right-6 md:right-8 min-h-10 min-w-10 p-2.5 rounded-full surface-raised border-[var(--border-subtle)] shadow-lg text-[var(--text-muted)] transition-colors cursor-pointer z-30"
                  aria-label="Scroll to bottom"
                >
                  <ChevronDown className="w-5 h-5" />
                </button>
              ) : null}
              composer={composer}
            >
              <Suspense
                fallback={
                  <div className="flex items-center gap-2 max-w-4xl mx-auto w-full px-3 py-4 text-sm text-slate-500 dark:text-slate-400" role="status">
                    <span className="w-2 h-2 rounded-full bg-brand-indigo animate-pulse" />
                    Loading response renderer…
                  </div>
                }
              >
                {messages.length === 0 ? (
                  <section className="research-empty-state max-w-2xl mx-auto w-full px-4 py-10 md:py-16" aria-labelledby="conversation-empty-title" data-empty-mode={activeConversationMode}>
                    {activeConversationMode === "research" && (
                      <p className="research-empty-state__eyebrow">{t("conversation.researchEmptyEyebrow")}</p>
                    )}
                    <h1 id="conversation-empty-title">
                      {activeConversationMode === "chat" ? t("conversation.chatEmptyTitle") : t("conversation.researchEmptyTitle")}
                    </h1>
                    <p>
                      {activeConversationMode === "chat" ? t("conversation.chatEmptyBody") : t("conversation.researchEmptyBody")}
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
                        ? () => { void answerActions.bookmark({ conversationId: activeConversationId, messageId: msg.id, variantId: null }); }
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
                        ? (target) => { void handleSaveAnswerVersion(target); }
                        : undefined
                    }
                    saveVariantStatus={
                      toLegacySaveStatus(answerActions.getState("save_version", { conversationId: activeConversationId, messageId: msg.id, variantId: displayedAnswerContext?.messageId === msg.id ? displayedAnswerContext.variantId : null }).status)
                    }
                    answerActionStates={{
                      bookmark: answerActions.getState("bookmark", { conversationId: activeConversationId, messageId: msg.id, variantId: null }),
                      feedback: answerActions.getState("feedback", { conversationId: activeConversationId, messageId: msg.id, variantId: displayedAnswerContext?.messageId === msg.id ? displayedAnswerContext.variantId : null }),
                      note: answerActions.getState("note", { conversationId: activeConversationId, messageId: msg.id, variantId: null }),
                      save_version: answerActions.getState("save_version", { conversationId: activeConversationId, messageId: msg.id, variantId: displayedAnswerContext?.messageId === msg.id ? displayedAnswerContext.variantId : null }),
                    }}
                    onRetrySaveVariant={
                      msg.sender === "assistant" && !msg.isStreaming && msg.text
                        ? (target) => { void handleSaveAnswerVersion(target); }
                        : undefined
                    }
                    onViewSavedVersion={handleViewSavedVersion}
                    onInspectSource={handleInspectSource}
                    onDisplayedAnswerContext={handleDisplayedAnswerContext}
                    pipelineStages={stageEventsByMessage[msg.id]}
                    availableSections={sections}
                    onUseRelatedResearch={undefined}
                    initialVariantId={pendingOpenVariant?.conversationId === activeConversationId && pendingOpenVariant.messageId === msg.id ? pendingOpenVariant.variantId : undefined}
                    tabIndex={0}
                  />
                ))}
              </Suspense>
            </ConversationPageShell>
                )}
              </Suspense>
            </div>
          </div>
        </main>

    </ApplicationWorkspace>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppWorkspace />
    </BrowserRouter>
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
