import type { Locale } from "./i18n";

export type ResearchTemplateId =
  | "revenue-fact"
  | "growth-comparison"
  | "dependency-comparison"
  | "risk-groups"
  | "source-audit"
  | "company-summary";

export interface ResearchTemplateCopy {
  label: string;
  description: string;
  question: string;
  keywords: readonly string[];
}

export interface ResearchScopePreset {
  ticker: string | null;
  section: string | null;
  topK: number;
  enableComparative: boolean;
}

export interface ResearchTemplate {
  id: ResearchTemplateId;
  copy: Record<Locale, ResearchTemplateCopy>;
  scope: ResearchScopePreset;
}

export const RESEARCH_TEMPLATES: readonly ResearchTemplate[] = [
  {
    id: "revenue-fact",
    copy: {
      en: {
        label: "Revenue fact",
        description: "Find a reported revenue figure and period.",
        question: "What total revenue did [company] report in [year]?",
        keywords: ["revenue", "sales", "reported", "period"],
      },
      vi: {
        label: "Doanh thu",
        description: "Tìm số doanh thu và kỳ báo cáo.",
        question: "[Công ty] báo cáo tổng doanh thu bao nhiêu trong [năm]?",
        keywords: ["doanh thu", "bán hàng", "báo cáo", "kỳ"],
      },
    },
    scope: { ticker: null, section: "financial_table", topK: 5, enableComparative: false },
  },
  {
    id: "growth-comparison",
    copy: {
      en: {
        label: "Growth comparison",
        description: "Compare a metric across two periods.",
        question: "How did [metric] change from [year 1] to [year 2] for [company]?",
        keywords: ["growth", "change", "compare", "periods"],
      },
      vi: {
        label: "So sánh tăng trưởng",
        description: "So sánh chỉ số qua hai kỳ.",
        question: "[Chỉ số] của [công ty] thay đổi thế nào từ [năm 1] đến [năm 2]?",
        keywords: ["tăng trưởng", "thay đổi", "so sánh", "kỳ"],
      },
    },
    scope: { ticker: null, section: "mdna", topK: 5, enableComparative: false },
  },
  {
    id: "dependency-comparison",
    copy: {
      en: {
        label: "Dependency comparison",
        description: "Check whether comparable share evidence exists.",
        question: "Which company depends more on [metric] and what evidence supports the comparison?",
        keywords: ["dependency", "comparison", "share", "evidence"],
      },
      vi: {
        label: "So sánh mức phụ thuộc",
        description: "Kiểm tra bằng chứng về tỷ trọng có so sánh được không.",
        question: "Công ty nào phụ thuộc nhiều hơn vào [chỉ số], và bằng chứng nào hỗ trợ so sánh?",
        keywords: ["phụ thuộc", "so sánh", "tỷ trọng", "bằng chứng"],
      },
    },
    scope: { ticker: null, section: "financial_table", topK: 5, enableComparative: true },
  },
  {
    id: "risk-groups",
    copy: {
      en: {
        label: "Risk groups",
        description: "Summarize filing-native primary risk groups.",
        question: "What major risk groups does [company] disclose? Cite each group.",
        keywords: ["risk", "groups", "disclosures", "cite"],
      },
      vi: {
        label: "Nhóm rủi ro",
        description: "Tóm tắt các nhóm rủi ro chính trong hồ sơ.",
        question: "[Công ty] công bố những nhóm rủi ro chính nào? Hãy dẫn nguồn cho từng nhóm.",
        keywords: ["rủi ro", "nhóm", "công bố", "dẫn nguồn"],
      },
    },
    scope: { ticker: null, section: "risk_factors", topK: 5, enableComparative: false },
  },
  {
    id: "source-audit",
    copy: {
      en: {
        label: "Source audit",
        description: "Inspect the evidence behind an answer.",
        question: "Which filing sections support this claim, and what does each source actually say?",
        keywords: ["source", "audit", "evidence", "claim"],
      },
      vi: {
        label: "Kiểm tra nguồn",
        description: "Kiểm tra bằng chứng đứng sau câu trả lời.",
        question: "Những mục nào trong hồ sơ hỗ trợ khẳng định này, và mỗi nguồn thực sự nói gì?",
        keywords: ["nguồn", "kiểm tra", "bằng chứng", "khẳng định"],
      },
    },
    scope: { ticker: null, section: null, topK: 5, enableComparative: false },
  },
  {
    id: "company-summary",
    copy: {
      en: {
        label: "Company summary",
        description: "Create a bounded filing summary.",
        question: "Summarize the most important business and financial disclosures for [company] in [year].",
        keywords: ["company", "summary", "business", "financial"],
      },
      vi: {
        label: "Tóm tắt công ty",
        description: "Tóm tắt có giới hạn theo filing.",
        question: "Tóm tắt các công bố kinh doanh và tài chính quan trọng nhất của [công ty] trong [năm].",
        keywords: ["công ty", "tóm tắt", "kinh doanh", "tài chính"],
      },
    },
    scope: { ticker: null, section: null, topK: 5, enableComparative: false },
  },
];

export function getResearchTemplateCopy(
  template: ResearchTemplate,
  locale: Locale,
): ResearchTemplateCopy {
  return template.copy[locale] ?? template.copy.en;
}
