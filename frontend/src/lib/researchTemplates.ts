export interface ResearchTemplate {
  id: string;
  label: string;
  description: string;
  language: "en" | "vi";
  question: string;
  ticker?: string;
  section?: string;
}

export const RESEARCH_TEMPLATES: ResearchTemplate[] = [
  { id: "en-revenue", label: "Revenue fact", description: "Find a reported revenue figure and period.", language: "en", question: "What total revenue did [company] report in [year]?", section: "financial_table" },
  { id: "vi-revenue", label: "Doanh thu", description: "Tìm số doanh thu và kỳ báo cáo.", language: "vi", question: "[Công ty] báo cáo tổng doanh thu bao nhiêu trong [năm]?", section: "financial_table" },
  { id: "en-growth", label: "Growth comparison", description: "Compare a metric across two periods.", language: "en", question: "How did [metric] change from [year 1] to [year 2] for [company]?", section: "mdna" },
  { id: "vi-growth", label: "So sánh tăng trưởng", description: "So sánh chỉ số qua hai kỳ.", language: "vi", question: "[Chỉ số] của [công ty] thay đổi thế nào từ [năm 1] đến [năm 2]?", section: "mdna" },
  { id: "en-dependency", label: "Dependency comparison", description: "Check whether comparable share evidence exists.", language: "en", question: "Which company depends more on [metric] and what evidence supports the comparison?", section: "financial_table" },
  { id: "vi-dependency", label: "So sánh mức phụ thuộc", description: "Kiểm tra evidence share có so sánh được không.", language: "vi", question: "Công ty nào phụ thuộc nhiều hơn vào [chỉ số], và bằng chứng nào hỗ trợ so sánh?", section: "financial_table" },
  { id: "en-risk", label: "Risk groups", description: "Summarize filing-native primary risk groups.", language: "en", question: "What major risk groups does [company] disclose? Cite each group.", section: "risk_factors" },
  { id: "vi-risk", label: "Nhóm rủi ro", description: "Tóm tắt các nhóm rủi ro chính trong hồ sơ.", language: "vi", question: "[Công ty] công bố những nhóm rủi ro chính nào? Hãy dẫn nguồn cho từng nhóm.", section: "risk_factors" },
  { id: "en-source", label: "Source audit", description: "Inspect the evidence behind an answer.", language: "en", question: "Which filing sections support this claim, and what does each source actually say?" },
  { id: "vi-source", label: "Kiểm tra nguồn", description: "Kiểm tra evidence đứng sau câu trả lời.", language: "vi", question: "Những mục nào trong hồ sơ hỗ trợ khẳng định này, và mỗi nguồn thực sự nói gì?" },
  { id: "en-summary", label: "Company summary", description: "Create a bounded filing summary.", language: "en", question: "Summarize the most important business and financial disclosures for [company] in [year]." },
  { id: "vi-summary", label: "Tóm tắt công ty", description: "Tóm tắt có giới hạn theo filing.", language: "vi", question: "Tóm tắt các công bố kinh doanh và tài chính quan trọng nhất của [công ty] trong [năm]." },
];
