import type { Locale } from "./i18n";
import type { Message, Source } from "../types";

export interface RelatedResearchSuggestion {
  id: string;
  label: Record<Locale, string>;
  description: Record<Locale, string>;
  question: Record<Locale, string>;
  scope: { ticker: string | null; section: string | null };
}

const SECTION_ORDER = ["risk_factors", "financial_table", "mdna"] as const;

function normalizedSection(value: string | null | undefined): string | null {
  const normalized = value?.trim().toLowerCase().replace(/\s+/g, "_");
  return normalized || null;
}

function firstSource(message: Message): Source | null {
  return message.sources?.find((source) => source.ticker || source.section || source.filing_date) ?? message.sources?.[0] ?? null;
}

function tickerFor(message: Message, source: Source | null): string | null {
  return message.requestSnapshot?.ticker ?? source?.ticker ?? null;
}

/** Build bounded next questions from the answer's request and verified metadata. */
export function buildRelatedResearchSuggestions(
  message: Message,
  availableSections: readonly string[] = [],
): RelatedResearchSuggestion[] {
  if (message.sender !== "assistant" || message.error || !message.text.trim()) return [];
  const source = firstSource(message);
  const ticker = tickerFor(message, source);
  const currentSection = normalizedSection(message.requestSnapshot?.section ?? source?.section);
  const available = new Set(availableSections.map((item) => normalizedSection(item)).filter(Boolean));
  const suggestions: RelatedResearchSuggestion[] = [
    {
      id: "source-audit",
      label: { en: "Audit the cited sources", vi: "Kiểm tra các nguồn đã dẫn" },
      description: { en: "Inspect what each cited filing section actually supports.", vi: "Kiểm tra mỗi mục filing thực sự hỗ trợ điều gì." },
      question: {
        en: "Which filing sections support this answer, and what does each cited source actually say?",
        vi: "Những mục nào trong filing hỗ trợ câu trả lời này, và mỗi nguồn đã dẫn thực sự nói gì?",
      },
      scope: { ticker, section: null },
    },
  ];

  for (const section of SECTION_ORDER) {
    if (suggestions.length >= 3 || section === currentSection || (available.size > 0 && !available.has(section))) continue;
    const copy = section === "risk_factors"
      ? { label: { en: "Review disclosed risks", vi: "Xem các rủi ro đã công bố" }, section: { en: "risk factors", vi: "rủi ro" } }
      : section === "financial_table"
        ? { label: { en: "Check the financial tables", vi: "Kiểm tra các bảng tài chính" }, section: { en: "financial tables", vi: "bảng tài chính" } }
        : { label: { en: "Inspect management discussion", vi: "Xem phần thảo luận của ban quản lý" }, section: { en: "MD&A", vi: "MD&A" } };
    const subject = ticker ?? "the cited company";
    suggestions.push({
      id: `section-${section}`,
      label: copy.label,
      description: {
        en: `Search the available ${copy.section.en} section for related evidence.`,
        vi: `Tìm bằng chứng liên quan trong mục ${copy.section.vi} hiện có.`,
      },
      question: {
        en: `What does ${subject} disclose in its ${copy.section.en} section that relates to this question?`,
        vi: `${subject} công bố gì trong mục ${copy.section.vi} liên quan đến câu hỏi này?`,
      },
      scope: { ticker, section },
    });
  }
  return suggestions;
}
