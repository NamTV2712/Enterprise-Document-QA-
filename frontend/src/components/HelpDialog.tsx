/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { useLocale } from "../lib/i18n";

interface HelpDialogProps {
  open: boolean;
  onClose: () => void;
}

const SECTIONS: { title: string; items: string[] }[] = [
  {
    title: "Asking questions",
    items: [
      "Name the company, the metric, and the year when you can — for example: \"What was Apple's total net sales in fiscal year 2024?\"",
      "Questions must be between 5 and 500 characters. Press Enter to send; Shift+Enter adds a new line.",
      "If the filings do not contain the answer, the assistant says so instead of guessing.",
    ],
  },
  {
    title: "Search filters",
    items: [
      "Company limits retrieval to one issuer's filings; leave it on All companies for comparisons.",
      "10-K section limits retrieval to one filing section, such as Risk Factors or MD&A.",
      "Context breadth (Top-K) controls how many filing excerpts are kept after re-ranking.",
      "Query decomposition breaks comparative questions into one focused sub-query per company.",
    ],
  },
  {
    title: "Comparison limits",
    items: [
      "Comparative answers quote each company's own disclosed figures side by side.",
      "The assistant does not calculate rankings, ratios, or percentages that the filings do not state.",
      "Different companies may disclose different measures, so some questions have no like-for-like answer.",
    ],
  },
  {
    title: "Citations and evidence",
    items: [
      "Every factual claim cites a filing excerpt as [Source N]. Select a citation to jump to that excerpt.",
      "Rank score orders excerpts within one answer; it is not a probability or confidence percentage.",
      "Filing dates describe when the document was filed; they are not the fiscal period of a number.",
    ],
  },
  {
    title: "Local storage",
    items: [
      "Conversations are saved in this browser only — up to 100 conversations and 25 MB in total.",
      "The backend keeps only a few recent turns per session and expires them after 30 minutes.",
      "When backend context expires, saved conversations become read-only copies you can still search and export.",
    ],
  },
];

const SECTIONS_VI: { title: string; items: string[] }[] = [
  {
    title: "Đặt câu hỏi",
    items: [
      "Nêu công ty, chỉ tiêu và năm nếu có thể — ví dụ: “Doanh thu thuần của Apple trong năm tài chính 2024 là bao nhiêu?”",
      "Câu hỏi dài từ 5 đến 500 ký tự. Nhấn Enter để gửi; Shift+Enter để xuống dòng.",
      "Nếu filing không có câu trả lời, trợ lý sẽ nói rõ thay vì đoán.",
    ],
  },
  {
    title: "Bộ lọc tìm kiếm",
    items: [
      "Company giới hạn việc tìm kiếm vào filing của một tổ chức; để Tất cả công ty cho câu hỏi so sánh.",
      "Mục 10-K giới hạn việc tìm kiếm vào một phần filing như Risk Factors hoặc MD&A.",
      "Độ rộng ngữ cảnh (Top-K) quyết định số đoạn filing được giữ lại sau rerank.",
      "Tách câu hỏi chia câu hỏi so sánh thành một truy vấn tập trung cho mỗi công ty.",
    ],
  },
  {
    title: "Giới hạn so sánh",
    items: [
      "Câu trả lời so sánh đặt các số liệu do từng công ty công bố cạnh nhau.",
      "Trợ lý không tự tính thứ hạng, tỷ lệ hoặc phần trăm mà filing không nêu.",
      "Các công ty có thể công bố chỉ tiêu khác nhau nên không phải câu hỏi nào cũng so sánh được trực tiếp.",
    ],
  },
  {
    title: "Trích dẫn và bằng chứng",
    items: [
      "Mọi khẳng định thực tế đều dẫn tới đoạn filing bằng dạng [Source N]. Chọn citation để mở đoạn nguồn.",
      "Điểm rank chỉ sắp xếp các đoạn trong một câu trả lời; đây không phải xác suất hay phần trăm tin cậy.",
      "Ngày filing là ngày tài liệu được nộp, không phải kỳ tài chính của số liệu.",
    ],
  },
  {
    title: "Lưu trữ cục bộ",
    items: [
      "Cuộc trò chuyện chỉ được lưu trong trình duyệt này — tối đa 100 cuộc trò chuyện và tổng 25 MB.",
      "Backend chỉ giữ một số lượt gần nhất và hết hạn sau 30 phút.",
      "Khi context backend hết hạn, cuộc trò chuyện đã lưu chuyển sang chỉ đọc nhưng vẫn tìm kiếm và xuất được.",
    ],
  },
];

const GLOSSARY = [
  ["Top-K", "The number of retrieved filing excerpts retained before the answer is generated."],
  ["RRF", "Reciprocal Rank Fusion: the hybrid ranking layer combining lexical and semantic retrieval."],
  ["Citation", "A [Source N] reference pointing to the excerpt shown in the evidence panel."],
  ["Fiscal period", "The reporting period for a number; it can differ from the date the filing was submitted."],
  ["Read-only", "A saved local conversation whose backend session has expired; it can still be searched, read, exported, and bookmarked."],
] as const;

const GLOSSARY_VI = [
  ["Top-K", "Số đoạn filing được giữ lại sau truy xuất và trước khi tạo câu trả lời."],
  ["RRF", "Reciprocal Rank Fusion: lớp xếp hạng kết hợp tìm kiếm theo từ khóa và ngữ nghĩa."],
  ["Citation", "Tham chiếu [Source N] trỏ tới đoạn nguồn hiển thị trong bảng bằng chứng."],
  ["Kỳ tài chính", "Kỳ báo cáo của một số liệu; có thể khác ngày filing được nộp."],
  ["Chỉ đọc", "Cuộc trò chuyện cục bộ có session backend đã hết hạn; vẫn có thể tìm, đọc, xuất và đánh dấu."],
] as const;

export const HelpDialog: React.FC<HelpDialogProps> = ({ open, onClose }) => {
  const { locale, t } = useLocale();
  const sections = locale === "vi" ? SECTIONS_VI : SECTIONS;
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), [href], [tabindex]:not([tabindex="-1"])',
        ) || [],
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown, true);
    return () => {
      document.removeEventListener("keydown", handleKeyDown, true);
      previouslyFocused?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overlay-backdrop p-4"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-dialog-title"
        className="w-full max-w-lg rounded-2xl surface-raised border-[var(--border-subtle)] p-5 shadow-2xl max-h-[85dvh] overflow-y-auto"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="help-dialog-title" className="text-base font-semibold text-[var(--text-primary)]">
            {t("help.title")}
          </h2>
          <button
            type="button"
            ref={closeRef}
            onClick={onClose}
            aria-label={t("help.close")}
            className="min-h-9 min-w-9 rounded-lg p-2 text-[var(--text-subtle)] hover:surface-muted-hover"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-3 space-y-4">
          {sections.map((section) => (
            <section key={section.title}>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
                {section.title}
              </h3>
              <ul className="mt-1.5 space-y-1.5">
                {section.items.map((item) => (
                  <li
                    key={item}
                    className="text-sm leading-relaxed text-[var(--text-muted)] list-disc pl-4 marker:text-[var(--text-subtle)]"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </section>
          ))}
          <section>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
              {locale === "vi" ? "Thuật ngữ nhanh" : "Quick glossary"}
            </h3>
            <dl className="mt-2 space-y-2">
              {(locale === "vi" ? GLOSSARY_VI : GLOSSARY).map(([term, definition]) => (
                <div key={term} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-3 py-2">
                  <dt className="text-xs font-semibold text-[var(--text-primary)]">{term}</dt>
                  <dd className="mt-0.5 text-sm leading-relaxed text-[var(--text-muted)]">{definition}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      </div>
    </div>
  );
};
