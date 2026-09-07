import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "en" | "vi";
export type LocalePreference = Locale | "system";

type MessageKey = keyof typeof MESSAGES.en;

const MESSAGES = {
  en: {
    "nav.overview": "Overview",
    "nav.showOverview": "Show overview",
    "nav.conversation": "Conversation",
    "nav.retrieval": "Retrieval Lab",
    "nav.documents": "Documents",
    "nav.evaluation": "Evaluation",
    "nav.analytics": "Analytics",
    "nav.system": "System",
    "nav.workspaceViews": "Workspace view",
    "nav.closeSearch": "Close search controls",
    "nav.openSearch": "Open search controls",
    "nav.help": "Open help",
    "nav.newConversation": "New conversation",
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
    "nav.showOverview": "Hiện tổng quan",
    "nav.conversation": "Cuộc trò chuyện",
    "nav.retrieval": "Phòng Retrieval",
    "nav.documents": "Tài liệu",
    "nav.evaluation": "Đánh giá",
    "nav.analytics": "Analytics",
    "nav.system": "Hệ thống",
    "nav.workspaceViews": "Chế độ workspace",
    "nav.closeSearch": "Đóng bộ lọc tìm kiếm",
    "nav.openSearch": "Mở bộ lọc tìm kiếm",
    "nav.help": "Mở hướng dẫn",
    "nav.newConversation": "Cuộc trò chuyện mới",
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
    } catch {
      // Keep the preference for the current tab.
    }
  };

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

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
