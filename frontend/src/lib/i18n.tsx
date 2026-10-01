import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "en" | "vi";
export type LocalePreference = Locale | "system";

export type MessageKey = keyof typeof MESSAGES.en;

const MESSAGES = {
  en: {
    "nav.overview": "Overview",
    "nav.research": "Research",
    "nav.chat": "Chat",
    "nav.showOverview": "Show overview",
    "nav.conversation": "Conversation",
    "nav.currentConversation": "Current conversation",
    "nav.search": "Search",
    "nav.retrieval": "Retrieval Lab",
    "nav.models": "Models",
    "nav.pipeline": "Pipeline",
    "nav.agent": "Agent",
    "nav.documents": "Documents",
    "nav.library": "Library",
    "nav.collections": "Collections",
    "nav.architecture": "Architecture",
    "nav.evaluation": "Evaluation",
    "nav.analytics": "Analytics",
    "nav.system": "System",
    "nav.reranker": "Reranker",
    "nav.datasets": "Datasets",
    "nav.settings": "Settings",
    "nav.logs": "Logs",
    "nav.groupWorkspace": "Workspace",
    "nav.groupBuild": "Build",
    "nav.groupRetrieval": "Retrieval",
    "nav.groupEvaluate": "Evaluate",
    "nav.groupSystem": "System",
    "nav.groupManage": "Manage",
    "nav.workspaceViews": "Workspace view",
    "nav.closeSearch": "Close search controls",
    "nav.openSearch": "Open search controls",
    "nav.closeNavigation": "Close navigation",
    "nav.openNavigation": "Open navigation",
    "nav.expandNavigation": "Expand navigation",
    "nav.compactNavigation": "Use compact navigation",
    "nav.help": "Open help",
    "nav.newConversation": "New conversation",
    "conversation.chatTitle": "Chat",
    "conversation.chatSubtitle": "Ask a direct question and read the grounded answer with its citations.",
    "conversation.researchTitle": "Research",
    "conversation.researchSubtitle": "Ask grounded questions and get answers with citations from your documents.",
    "conversation.newChat": "New Chat",
    "conversation.newResearch": "New Research",
    "conversation.history": "History",
    "conversation.followUps": "Follow-up questions",
    "conversation.insights": "Insights",
    "conversation.insightSourcesUsed": "Sources used",
    "conversation.insightTotalChunks": "Total chunks",
    "conversation.insightTopScore": "Top retrieval score",
    "conversation.insightResponseTime": "Response time",
    "conversation.chatEmptyTitle": "Ask a filing question",
    "conversation.chatEmptyBody": "Type your question below. The answer stays grounded in retrieved 10-K evidence with citations.",
    "conversation.researchEmptyEyebrow": "New research",
    "conversation.researchEmptyTitle": "Start with a filing question",
    "conversation.researchEmptyBody": "Choose a focused example or write your own question below. The answer will stay grounded in retrieved 10-K evidence.",
    "workbench.layout": "Research workbench layout",
    "workbench.research": "Research",
    "workbench.sources": "Retrieved sources",
    "workbench.document": "Document viewer",
    "workbench.header": "Workspace toolbar",
    "nav.researchDescription": "Choose a scope and start a filing question.",
    "nav.chatDescription": "Ask a direct grounded filing question.",
    "nav.currentConversationDescription": "Read the active answer and its evidence.",
    "nav.documentsDescription": "Browse indexed filings and excerpts.",
    "nav.searchDescription": "Search indexed filing text and metadata.",
    "nav.libraryDescription": "Reopen saved research and evidence.",
    "nav.collectionsDescription": "Review saved research and evidence.",
    "nav.retrievalDescription": "Inspect retrieval, ranking and reranking.",
    "nav.modelsDescription": "Inspect configured and observed runtime model identities.",
    "nav.pipelineDescription": "Monitor the offline ingestion pipeline and corpus builds.",
    "nav.agentDescription": "Inspect private Agent runs and safe operational activity.",
    "nav.rerankerDescription": "Inspect the existing reranking workflow.",
    "nav.evaluationDescription": "Inspect published evaluation runs.",
    "nav.analyticsDescription": "Review server terminal request and job populations.",
    "nav.datasetsDescription": "Inspect serving-corpus coverage and evaluation metadata.",
    "nav.architectureDescription": "Explore verified system workflows.",
    "nav.systemDescription": "Check service and corpus readiness.",
    "nav.settingsDescription": "Review truthful system and workspace configuration.",
    "nav.logsDescription": "Inspect sanitized terminal request and job records.",
    "nav.newConversationDescription": "Start a fresh research session.",
    "header.openCommandPalette": "Open command palette",
    "header.commandPaletteTitle": "Search documents, conversations, or actions (⌘ K)",
    "header.openSettings": "Open settings",
    "header.moreControls": "More workspace controls",
    "header.workspaceControls": "Workspace controls",
    "header.closeWorkspaceControls": "Close workspace controls",
    "header.workspace": "Workspace",
    "header.noTicker": "No ticker selected",
    "header.sec10kScope": "{ticker} SEC 10-K",
    "header.modelUnavailable": "Model unavailable",
    "header.noAccount": "No account identity",
    "header.localWorkspace": "Local workspace",
    "header.localSession": "Local session",
    "palette.title": "Command palette",
    "palette.search": "Search actions or templates...",
    "palette.searchAria": "Search command palette",
    "palette.navigate": "Navigate",
    "palette.utilities": "Utilities",
    "palette.templates": "Research templates (never auto-send)",
    "palette.copyAnswer": "Copy current answer",
      "palette.copyAnswerDescription": "Copy the focused grounded answer to the clipboard.",
    "palette.inspectSources": "Inspect current sources",
    "palette.inspectSourcesDescription": "Open the selected answer evidence and source excerpts.",
    "palette.saveSource": "Save selected source",
    "palette.saveSourceDescription": "Add the selected excerpt to the evidence collection.",
    "palette.openScope": "Open scope editor",
    "palette.openScopeDescription": "Review the active company, section, and Top-K settings.",
    "palette.noMatch": "No actions or templates match.",
    "nav.resetting": "Resetting...",
    "theme.system": "System",
    "theme.light": "Light",
    "theme.dark": "Dark",
    "theme.choose": "Choose light, dark, or system theme",
    "theme.preference": "Theme preference",
    "language.label": "Language",
    "language.english": "English",
    "language.vietnamese": "Tiếng Việt",
    "answerLanguage.label": "Answer language",
    "answerLanguage.follow": "Follow interface",
    "answerLanguage.english": "English",
    "answerLanguage.vietnamese": "Tiếng Việt",
    "input.ask": "Ask",
    "input.sendAria": "Send question",
    "input.stop": "Stop",
    "input.question": "Research question",
    "input.scope": "Scope",
    "input.activeScope": "Active search scope",
    "input.connecting": "Connecting to the FastAPI backend...",
    "input.unavailable": "Connect the FastAPI backend to start asking questions",
    "input.loading": "Pipeline index loading...",
    "input.placeholder": "Ask a question about 10-K filings (e.g. Compare risk factors...)",
    "input.readOnly": "This saved conversation is read-only; ask follow-ups in a new conversation",
    "input.min": "Query must be at least 5 characters.",
    "input.max": "Query must not exceed 500 characters.",
    "input.hint": "Press enter to ask, shift+enter for new line.",
    "input.enter": "Enter to ask",
    "input.newline": "Shift + Enter for new line",
    "connection.connecting": "Connecting to the research service...",
    "connection.unavailable": "The research service is unavailable. Check the connection and try again.",
    "connection.loading": "System status: the document index is still loading.",
    "suggested.title": "Suggested research questions",
    "sidebar.systemMetrics": "System metrics",
    "sidebar.activeSessions": "Active sessions",
    "sidebar.inMemory": "In-memory conversations",
    "sidebar.totalTurns": "Total turns",
    "sidebar.retained": "Retained messages",
    "help.title": "How to use this research workspace",
    "help.close": "Close help",
    "library.title": "Saved conversations",
    "library.search": "Search questions and answers",
    "library.searchSaved": "Search saved conversations",
    "library.bookmarks": "Bookmarked answers",
    "library.empty": "Your saved conversations will appear here.",
    "library.noMatch": "No conversations match this search.",
    "library.noBookmarkMatch": "No bookmarked answers match this search.",
    "library.bookmarkHint": "Bookmark an answer to find it quickly here.",
    "library.saved": "Saved on this device",
    "library.memory": "Only kept in this tab",
    "library.fallback": "Browser storage fallback",
    "common.allCompanies": "All companies",
    "common.allSections": "All sections",
    "common.copy": "Copy",
    "common.copied": "Copied",
    "common.export": "Export",
    "common.retry": "Retry",
  },
  vi: {
    "nav.overview": "Tổng quan",
    "nav.research": "Nghiên cứu",
    "nav.chat": "Trò chuyện",
    "nav.showOverview": "Hiện tổng quan",
    "nav.conversation": "Cuộc trò chuyện",
    "nav.currentConversation": "Cuộc trò chuyện hiện tại",
    "nav.search": "Tìm kiếm",
    "nav.retrieval": "Phòng Retrieval",
    "nav.models": "Mô hình",
    "nav.pipeline": "Pipeline",
    "nav.agent": "Agent",
    "nav.documents": "Tài liệu",
    "nav.library": "Thư viện",
    "nav.collections": "Bộ sưu tập",
    "nav.architecture": "Kiến trúc",
    "nav.evaluation": "Đánh giá",
    "nav.analytics": "Analytics",
    "nav.system": "Hệ thống",
    "nav.reranker": "Xếp hạng lại",
    "nav.datasets": "Bộ dữ liệu",
    "nav.settings": "Cài đặt",
    "nav.logs": "Nhật ký",
    "nav.groupWorkspace": "Workspace",
    "nav.groupBuild": "Xây dựng",
    "nav.groupRetrieval": "Retrieval",
    "nav.groupEvaluate": "Đánh giá",
    "nav.groupSystem": "Hệ thống",
    "nav.groupManage": "Quản lý",
    "nav.workspaceViews": "Chế độ workspace",
    "nav.closeSearch": "Đóng bộ lọc tìm kiếm",
    "nav.openSearch": "Mở bộ lọc tìm kiếm",
    "nav.closeNavigation": "Đóng điều hướng",
    "nav.openNavigation": "Mở điều hướng",
    "nav.expandNavigation": "Mở rộng điều hướng",
    "nav.compactNavigation": "Dùng điều hướng thu gọn",
    "nav.help": "Mở hướng dẫn",
    "nav.newConversation": "Cuộc trò chuyện mới",
    "conversation.chatTitle": "Trò chuyện",
    "conversation.chatSubtitle": "Đặt câu hỏi trực tiếp và đọc câu trả lời có căn cứ kèm trích dẫn.",
    "conversation.researchTitle": "Nghiên cứu",
    "conversation.researchSubtitle": "Đặt câu hỏi có căn cứ và nhận câu trả lời kèm trích dẫn từ tài liệu của bạn.",
    "conversation.newChat": "Trò chuyện mới",
    "conversation.newResearch": "Nghiên cứu mới",
    "conversation.history": "Lịch sử",
    "conversation.followUps": "Câu hỏi tiếp theo",
    "conversation.insights": "Số liệu nhanh",
    "conversation.insightSourcesUsed": "Nguồn đã dùng",
    "conversation.insightTotalChunks": "Tổng số đoạn",
    "conversation.insightTopScore": "Điểm truy xuất cao nhất",
    "conversation.insightResponseTime": "Thời gian phản hồi",
    "conversation.chatEmptyTitle": "Đặt câu hỏi về filing",
    "conversation.chatEmptyBody": "Nhập câu hỏi bên dưới. Câu trả lời luôn dựa trên bằng chứng 10-K đã truy xuất kèm trích dẫn.",
    "conversation.researchEmptyEyebrow": "Nghiên cứu mới",
    "conversation.researchEmptyTitle": "Bắt đầu với câu hỏi về filing",
    "conversation.researchEmptyBody": "Chọn một ví dụ cụ thể hoặc tự viết câu hỏi bên dưới. Câu trả lời sẽ dựa trên bằng chứng 10-K đã truy xuất.",
    "workbench.layout": "Bố cục workspace nghiên cứu",
    "workbench.research": "Nghiên cứu",
    "workbench.sources": "Nguồn đã truy xuất",
    "workbench.document": "Trình xem tài liệu",
    "workbench.header": "Thanh công cụ workspace",
    "nav.researchDescription": "Chọn phạm vi và bắt đầu câu hỏi filing.",
    "nav.chatDescription": "Đặt câu hỏi trực tiếp dựa trên filing.",
    "nav.currentConversationDescription": "Đọc câu trả lời hiện tại và bằng chứng.",
    "nav.documentsDescription": "Duyệt filing và excerpt đã lập chỉ mục.",
    "nav.searchDescription": "Tìm văn bản và metadata trong filing.",
    "nav.libraryDescription": "Mở lại nghiên cứu và evidence đã lưu.",
    "nav.collectionsDescription": "Xem nghiên cứu và evidence đã lưu.",
    "nav.retrievalDescription": "Kiểm tra retrieval, xếp hạng và reranking.",
    "nav.modelsDescription": "Xem danh tính mô hình đã cấu hình và runtime được ghi nhận.",
    "nav.pipelineDescription": "Theo dõi pipeline nạp dữ liệu offline và các lần build corpus.",
    "nav.agentDescription": "Xem các lần chạy Agent riêng tư và hoạt động vận hành an toàn.",
    "nav.rerankerDescription": "Kiểm tra workflow reranking hiện có.",
    "nav.evaluationDescription": "Xem các lần đánh giá đã công bố.",
    "nav.analyticsDescription": "Xem quần thể yêu cầu và job kết thúc từ server.",
    "nav.datasetsDescription": "Xem coverage corpus phục vụ và metadata đánh giá.",
    "nav.architectureDescription": "Khám phá workflow hệ thống đã xác minh.",
    "nav.systemDescription": "Kiểm tra trạng thái dịch vụ và corpus.",
    "nav.settingsDescription": "Xem cấu hình hệ thống và workspace chính xác.",
    "nav.logsDescription": "Xem bản ghi yêu cầu và job kết thúc đã làm sạch.",
    "nav.newConversationDescription": "Bắt đầu phiên nghiên cứu mới.",
    "header.openCommandPalette": "Mở bảng lệnh",
    "header.commandPaletteTitle": "Tìm tài liệu, cuộc trò chuyện hoặc hành động (⌘ K)",
    "header.openSettings": "Mở cài đặt",
    "header.moreControls": "Mở điều khiển workspace",
    "header.workspaceControls": "Điều khiển workspace",
    "header.closeWorkspaceControls": "Đóng điều khiển workspace",
    "header.workspace": "Workspace",
    "header.noTicker": "Chưa chọn mã",
    "header.sec10kScope": "{ticker} SEC 10-K",
    "header.modelUnavailable": "Chưa có mô hình",
    "header.noAccount": "Chưa có danh tính tài khoản",
    "header.localWorkspace": "Workspace cục bộ",
    "header.localSession": "Phiên cục bộ",
    "palette.title": "Bảng lệnh",
    "palette.search": "Tìm tính năng hoặc template...",
    "palette.searchAria": "Tìm trong bảng lệnh",
    "palette.navigate": "Điều hướng",
    "palette.utilities": "Tiện ích",
    "palette.templates": "Mẫu câu hỏi (không tự gửi)",
    "palette.copyAnswer": "Sao chép câu trả lời hiện tại",
      "palette.copyAnswerDescription": "Sao chép câu trả lời có dẫn nguồn đang chọn.",
    "palette.inspectSources": "Kiểm tra nguồn hiện tại",
    "palette.inspectSourcesDescription": "Mở bằng chứng và excerpt của câu trả lời đang chọn.",
    "palette.saveSource": "Lưu nguồn đang chọn",
    "palette.saveSourceDescription": "Thêm excerpt đang chọn vào bộ evidence.",
    "palette.openScope": "Mở trình chỉnh phạm vi",
    "palette.openScopeDescription": "Xem công ty, mục và Top-K đang hoạt động.",
    "palette.noMatch": "Không có hành động hoặc template phù hợp.",
    "nav.resetting": "Đang đặt lại...",
    "theme.system": "Theo hệ thống",
    "theme.light": "Sáng",
    "theme.dark": "Tối",
    "theme.choose": "Chọn giao diện sáng, tối hoặc theo hệ thống",
    "theme.preference": "Tùy chọn giao diện",
    "language.label": "Ngôn ngữ",
    "language.english": "English",
    "language.vietnamese": "Tiếng Việt",
    "answerLanguage.label": "Ngôn ngữ trả lời",
    "answerLanguage.follow": "Theo giao diện",
    "answerLanguage.english": "English",
    "answerLanguage.vietnamese": "Tiếng Việt",
    "input.ask": "Hỏi",
    "input.sendAria": "Gửi câu hỏi",
    "input.stop": "Dừng",
    "input.question": "Câu hỏi nghiên cứu",
    "input.scope": "Phạm vi",
    "input.activeScope": "Phạm vi tìm kiếm hiện tại",
    "input.connecting": "Đang kết nối tới backend FastAPI...",
    "input.unavailable": "Hãy kết nối backend FastAPI để bắt đầu hỏi",
    "input.loading": "Đang tải chỉ mục tài liệu...",
    "input.placeholder": "Đặt câu hỏi về báo cáo 10-K (ví dụ: So sánh các yếu tố rủi ro...)",
    "input.readOnly": "Cuộc trò chuyện đã lưu chỉ đọc; hãy hỏi tiếp trong cuộc trò chuyện mới",
    "input.min": "Câu hỏi phải có ít nhất 5 ký tự.",
    "input.max": "Câu hỏi không được vượt quá 500 ký tự.",
    "input.hint": "Nhấn Enter để hỏi, Shift+Enter để xuống dòng.",
    "input.enter": "Enter để hỏi",
    "input.newline": "Shift + Enter để xuống dòng",
    "connection.connecting": "Đang kết nối tới dịch vụ nghiên cứu...",
    "connection.unavailable": "Dịch vụ nghiên cứu không khả dụng. Hãy kiểm tra kết nối và thử lại.",
    "connection.loading": "Trạng thái hệ thống: chỉ mục tài liệu vẫn đang được tải.",
    "suggested.title": "Câu hỏi nghiên cứu gợi ý",
    "sidebar.systemMetrics": "Chỉ số hệ thống",
    "sidebar.activeSessions": "Phiên đang hoạt động",
    "sidebar.inMemory": "Cuộc trò chuyện trong bộ nhớ",
    "sidebar.totalTurns": "Tổng lượt trao đổi",
    "sidebar.retained": "Tin nhắn được giữ lại",
    "help.title": "Cách sử dụng workspace nghiên cứu",
    "help.close": "Đóng hướng dẫn",
    "library.title": "Cuộc trò chuyện đã lưu",
    "library.search": "Tìm trong câu hỏi và câu trả lời",
    "library.searchSaved": "Tìm trong cuộc trò chuyện đã lưu",
    "library.bookmarks": "Câu trả lời đã đánh dấu",
    "library.empty": "Các cuộc trò chuyện đã lưu sẽ xuất hiện ở đây.",
    "library.noMatch": "Không có cuộc trò chuyện phù hợp.",
    "library.noBookmarkMatch": "Không có câu trả lời đã đánh dấu phù hợp.",
    "library.bookmarkHint": "Đánh dấu câu trả lời để tìm lại nhanh hơn.",
    "library.saved": "Đã lưu trên thiết bị này",
    "library.memory": "Chỉ giữ trong tab này",
    "library.fallback": "Đang dùng bộ nhớ trình duyệt dự phòng",
    "common.allCompanies": "Tất cả công ty",
    "common.allSections": "Tất cả mục",
    "common.copy": "Sao chép",
    "common.copied": "Đã sao chép",
    "common.export": "Xuất",
    "common.retry": "Thử lại",
  },
} as const satisfies Record<Locale, Record<string, string>>;

interface LocaleContextValue {
  locale: Locale;
  preference: LocalePreference;
  setPreference: (preference: LocalePreference) => void;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

function systemLocale(): Locale {
  return typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("vi")
    ? "vi"
    : "en";
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreferenceState] = useState<LocalePreference>(() => {
    try {
      const saved = localStorage.getItem("sec_qa_locale");
      if (saved === "en" || saved === "vi" || saved === "system") return saved;

      // Migration: earlier versions stored the answer language separately from
      // the interface locale. Adopt that value only when no locale preference
      // exists, then keep one preference for both the UI and new requests.
      const legacyAnswerLanguage = localStorage.getItem("sec_qa_answer_language");
      if (legacyAnswerLanguage === "en" || legacyAnswerLanguage === "vi") {
        return legacyAnswerLanguage;
      }
    } catch {
      // The UI remains usable when browser storage is unavailable.
    }
    return "system";
  });
  const locale = preference === "system" ? systemLocale() : preference;

  const setPreference = (next: LocalePreference) => {
    setPreferenceState(next);
    try {
      localStorage.setItem("sec_qa_locale", next);
      // Do not keep writing the legacy key. Removing it prevents an old stale
      // answer-only preference from reintroducing language desynchronization.
      localStorage.removeItem("sec_qa_answer_language");
    } catch {
      // Keep the preference for the current tab.
    }
  };

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== "sec_qa_locale") return;
      if (event.newValue === "en" || event.newValue === "vi" || event.newValue === "system") {
        setPreferenceState(event.newValue);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      preference,
      setPreference,
      setLocale: (next) => setPreference(next),
      t: (key) => MESSAGES[locale][key] ?? MESSAGES.en[key] ?? key,
    }),
    [locale, preference],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (context) return context;
  // Components remain renderable in isolated unit tests and embedding hosts
  // that do not install the optional provider. The application mounts the
  // provider in main.tsx, so this fallback is never used in production.
  return {
    locale: "en",
    preference: "en",
    setPreference: () => {},
    setLocale: () => {},
    t: (key) => MESSAGES.en[key] ?? key,
  };
}

export function normalizeLocaleSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLocaleLowerCase();
}
