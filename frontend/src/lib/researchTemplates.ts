import type { Locale } from "./i18n";
import type { SemanticIconKey } from "./semanticIcons";

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
  iconKey: Extract<SemanticIconKey, `template${string}`>;
  copy: Record<Locale, ResearchTemplateCopy>;
  scope: ResearchScopePreset;
}

export type TemplateParameterKind = "ticker" | "year" | "metric" | "claim";

export interface ResearchTemplateParameter {
  key: string;
  kind: TemplateParameterKind;
  required: boolean;
  label: Record<Locale, string>;
  help?: Record<Locale, string>;
}

export interface TemplateValidationIssue {
  key: string;
  code:
    | "required"
    | "invalid-ticker"
    | "ticker-unavailable"
    | "invalid-year"
    | "invalid-length"
    | "duplicate-company"
    | "unresolved-placeholder"
    | "question-too-long";
}

export interface TemplateValidationResult {
  valid: boolean;
  values: Record<string, string>;
  issues: TemplateValidationIssue[];
}

export interface ResearchTemplateApplyPayload {
  templateId: ResearchTemplateId;
  locale: Locale;
  question: string;
  scope: ResearchScopePreset;
  values: Readonly<Record<string, string>>;
}

const TEMPLATE_PARAMETER_SCHEMAS: Record<ResearchTemplateId, readonly ResearchTemplateParameter[]> = {
  "revenue-fact": [
    { key: "company", kind: "ticker", required: true, label: { en: "Company", vi: "Công ty" } },
    { key: "year", kind: "year", required: true, label: { en: "Fiscal year", vi: "Năm tài chính" } },
  ],
  "growth-comparison": [
    { key: "company", kind: "ticker", required: true, label: { en: "Company", vi: "Công ty" } },
    { key: "metric", kind: "metric", required: true, label: { en: "Metric", vi: "Chỉ số" } },
    { key: "year1", kind: "year", required: true, label: { en: "Earlier year", vi: "Năm trước" } },
    { key: "year2", kind: "year", required: true, label: { en: "Later year", vi: "Năm sau" } },
  ],
  "dependency-comparison": [
    { key: "companyA", kind: "ticker", required: true, label: { en: "First company", vi: "Công ty thứ nhất" } },
    { key: "companyB", kind: "ticker", required: true, label: { en: "Second company", vi: "Công ty thứ hai" } },
    { key: "metric", kind: "metric", required: true, label: { en: "Dependency metric", vi: "Chỉ số phụ thuộc" } },
    { key: "year", kind: "year", required: false, label: { en: "Filing year (optional)", vi: "Năm filing (tùy chọn)" } },
  ],
  "risk-groups": [
    { key: "company", kind: "ticker", required: true, label: { en: "Company", vi: "Công ty" } },
  ],
  "source-audit": [
    { key: "company", kind: "ticker", required: true, label: { en: "Company", vi: "Công ty" } },
    { key: "claim", kind: "claim", required: true, label: { en: "Claim to audit", vi: "Khẳng định cần kiểm tra" } },
    { key: "year", kind: "year", required: false, label: { en: "Filing year (optional)", vi: "Năm filing (tùy chọn)" } },
  ],
  "company-summary": [
    { key: "company", kind: "ticker", required: true, label: { en: "Company", vi: "Công ty" } },
    { key: "year", kind: "year", required: true, label: { en: "Fiscal year", vi: "Năm tài chính" } },
  ],
};

const RESERVED_TEMPLATE_PLACEHOLDERS = /\[(?:companyA|companyB|company|metric|year1|year2|year|claim|công ty|năm)\]/iu;

const TEMPLATE_TOKEN_ALIASES: Record<string, string> = {
  "companya": "companyA",
  "companyb": "companyB",
  company: "company",
  metric: "metric",
  year1: "year1",
  year2: "year2",
  year: "year",
  claim: "claim",
  "công ty": "company",
  năm: "year",
};

export function getResearchTemplateSchema(template: ResearchTemplate): readonly ResearchTemplateParameter[] {
  return TEMPLATE_PARAMETER_SCHEMAS[template.id];
}

export function hasUnresolvedTemplatePlaceholders(question: string): boolean {
  return RESERVED_TEMPLATE_PLACEHOLDERS.test(question);
}

export function isSendableResearchQuestion(question: string): boolean {
  const trimmed = question.trim();
  return trimmed.length >= 5 && trimmed.length <= 500 && !hasUnresolvedTemplatePlaceholders(trimmed);
}

function normalizeTicker(value: string): string {
  return value.trim().toUpperCase();
}

function replaceTemplateTokens(question: string, values: Record<string, string>): string {
  return question.replace(/\[(companyA|companyB|company|metric|year1|year2|year|claim|công ty|năm)\]/giu, (_token, key: string) => {
    const canonicalKey = TEMPLATE_TOKEN_ALIASES[key.toLocaleLowerCase()] ?? key;
    return values[canonicalKey] ?? "";
  });
}

export function renderResearchTemplate(
  template: ResearchTemplate,
  locale: Locale,
  values: Record<string, string>,
): string {
  const copy = getResearchTemplateCopy(template, locale);
  let question = replaceTemplateTokens(copy.question, values).replace(/\s{2,}/g, " ").trim();
  if (values.year && (template.id === "dependency-comparison" || template.id === "source-audit")) {
    question += locale === "vi"
      ? ` Sử dụng các filing của năm ${values.year}.`
      : ` Use ${values.year} filings.`;
  }
  return question;
}

/**
 * Convert validated template parameters into the scope that belongs with the
 * question. Comparative templates deliberately keep an all-company scope so
 * both selected companies remain in the question instead of narrowing the
 * retrieval to one side of the comparison.
 */
export function deriveResearchTemplateScope(
  template: ResearchTemplate,
  values: Record<string, string>,
): ResearchScopePreset {
  const tickerParameters = getResearchTemplateSchema(template).filter(
    (parameter) => parameter.kind === "ticker",
  );
  const ticker = tickerParameters.length === 1
    ? normalizeTicker(values[tickerParameters[0].key] ?? "") || null
    : null;
  return { ...template.scope, ticker };
}

export function validateResearchTemplateValues(
  template: ResearchTemplate,
  rawValues: Record<string, string>,
  availableTickers: readonly string[],
  currentYear = new Date().getFullYear(),
): TemplateValidationResult {
  const values = Object.fromEntries(Object.entries(rawValues).map(([key, value]) => [key, value.trim()])) as Record<string, string>;
  const issues: TemplateValidationIssue[] = [];
  const tickerSet = new Set(availableTickers.map(normalizeTicker));

  for (const parameter of getResearchTemplateSchema(template)) {
    const value = values[parameter.key] ?? "";
    if (!value) {
      if (parameter.required) issues.push({ key: parameter.key, code: "required" });
      continue;
    }
    if (parameter.kind === "ticker") {
      values[parameter.key] = normalizeTicker(value);
      if (!/^[A-Z0-9][A-Z0-9._-]{0,9}$/.test(values[parameter.key])) {
        issues.push({ key: parameter.key, code: "invalid-ticker" });
      } else if (!tickerSet.has(values[parameter.key])) {
        issues.push({ key: parameter.key, code: availableTickers.length > 0 ? "invalid-ticker" : "ticker-unavailable" });
      }
    } else if (parameter.kind === "year") {
      if (!/^\d{4}$/.test(value) || Number(value) < 1900 || Number(value) > currentYear) {
        issues.push({ key: parameter.key, code: "invalid-year" });
      }
    } else {
      const maxLength = parameter.kind === "metric" ? 80 : 240;
      if (value.length < 1 || value.length > maxLength) {
        issues.push({ key: parameter.key, code: "invalid-length" });
      }
    }
  }

  if (template.id === "dependency-comparison" && values.companyA && values.companyA === values.companyB) {
    issues.push({ key: "companyB", code: "duplicate-company" });
  }

  const question = renderResearchTemplate(template, "en", values);
  if (hasUnresolvedTemplatePlaceholders(question)) {
    issues.push({ key: "question", code: "unresolved-placeholder" });
  }
  if (question.length < 5 || question.length > 500) {
    issues.push({ key: "question", code: "question-too-long" });
  }

  return { valid: issues.length === 0, values, issues };
}

export const RESEARCH_TEMPLATES: readonly ResearchTemplate[] = [
  {
    id: "revenue-fact",
    iconKey: "templateRevenue",
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
    iconKey: "templateGrowth",
    copy: {
      en: {
        label: "Growth comparison",
        description: "Compare a metric across two periods.",
        question: "How did [metric] change from [year1] to [year2] for [company]?",
        keywords: ["growth", "change", "compare", "periods"],
      },
      vi: {
        label: "So sánh tăng trưởng",
        description: "So sánh chỉ số qua hai kỳ.",
        question: "[metric] của [company] thay đổi thế nào từ [year1] đến [year2]?",
        keywords: ["tăng trưởng", "thay đổi", "so sánh", "kỳ"],
      },
    },
    scope: { ticker: null, section: "mdna", topK: 5, enableComparative: false },
  },
  {
    id: "dependency-comparison",
    iconKey: "templateDependency",
    copy: {
      en: {
        label: "Dependency comparison",
        description: "Check whether comparable share evidence exists.",
        question: "Which company, [companyA] or [companyB], depends more on [metric], and what evidence supports the comparison?",
        keywords: ["dependency", "comparison", "share", "evidence"],
      },
      vi: {
        label: "So sánh mức phụ thuộc",
        description: "Kiểm tra bằng chứng về tỷ trọng có so sánh được không.",
        question: "Công ty nào, [companyA] hay [companyB], phụ thuộc nhiều hơn vào [metric], và bằng chứng nào hỗ trợ so sánh?",
        keywords: ["phụ thuộc", "so sánh", "tỷ trọng", "bằng chứng"],
      },
    },
    scope: { ticker: null, section: "financial_table", topK: 5, enableComparative: true },
  },
  {
    id: "risk-groups",
    iconKey: "templateRisk",
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
        question: "[company] công bố những nhóm rủi ro chính nào? Hãy dẫn nguồn cho từng nhóm.",
        keywords: ["rủi ro", "nhóm", "công bố", "dẫn nguồn"],
      },
    },
    scope: { ticker: null, section: "risk_factors", topK: 5, enableComparative: false },
  },
  {
    id: "source-audit",
    iconKey: "templateSourceAudit",
    copy: {
      en: {
        label: "Source audit",
        description: "Inspect the evidence behind an answer.",
        question: "For [company], which filing sections support this claim: \"[claim]\", and what does each source actually say?",
        keywords: ["source", "audit", "evidence", "claim"],
      },
      vi: {
        label: "Kiểm tra nguồn",
        description: "Kiểm tra bằng chứng đứng sau câu trả lời.",
        question: "Với [company], những mục nào trong hồ sơ hỗ trợ khẳng định \"[claim]\", và mỗi nguồn thực sự nói gì?",
        keywords: ["nguồn", "kiểm tra", "bằng chứng", "khẳng định"],
      },
    },
    scope: { ticker: null, section: null, topK: 5, enableComparative: false },
  },
  {
    id: "company-summary",
    iconKey: "templateSummary",
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
        question: "Tóm tắt các công bố kinh doanh và tài chính quan trọng nhất của [company] trong [year].",
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
