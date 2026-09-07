/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { HelpCircle } from 'lucide-react';
import { useLocale } from "../lib/i18n";

export interface SampleQuestion {
  text: string;
  label: string;
  ticker?: string;
  section?: string;
}

export const SAMPLE_QUESTIONS: SampleQuestion[] = [
  {
    text: 'Compare the primary business risk factors between Apple (AAPL) and Microsoft (MSFT) for the latest fiscal year.',
    label: 'Apple vs Microsoft — Risk Factors',
    ticker: '',
    section: 'risk_factors',
  },
  {
    text: "What are Google's (GOOGL) main sources of business revenue and products according to their 10-K?",
    label: 'Alphabet (Google) — Business Segments',
    ticker: 'GOOGL',
    section: 'business',
  },
  {
    text: 'Summarize the primary MD&A (Management Discussion & Analysis) findings in Amazon (AMZN) latest 10-K.',
    label: 'Amazon — MD&A Highlights',
    ticker: 'AMZN',
    section: 'mdna',
  },
  {
    text: 'What are the major financial tables or statements trends highlighted in Tesla (TSLA) filings?',
    label: 'Tesla — Financial Statements',
    ticker: 'TSLA',
    section: 'financial_statements',
  },
];

const SAMPLE_QUESTIONS_VI: SampleQuestion[] = [
  {
    text: 'So sánh các yếu tố rủi ro kinh doanh chính giữa Apple (AAPL) và Microsoft (MSFT) trong năm tài chính gần nhất.',
    label: 'Apple và Microsoft — Yếu tố rủi ro',
    ticker: '',
    section: 'risk_factors',
  },
  {
    text: 'Theo báo cáo 10-K, các nguồn doanh thu và sản phẩm kinh doanh chính của Google (GOOGL) là gì?',
    label: 'Alphabet (Google) — Mảng kinh doanh',
    ticker: 'GOOGL',
    section: 'business',
  },
  {
    text: 'Tóm tắt các điểm chính trong MD&A của báo cáo 10-K gần nhất của Amazon (AMZN).',
    label: 'Amazon — Điểm chính MD&A',
    ticker: 'AMZN',
    section: 'mdna',
  },
  {
    text: 'Các xu hướng chính trong bảng hoặc báo cáo tài chính của Tesla (TSLA) là gì?',
    label: 'Tesla — Báo cáo tài chính',
    ticker: 'TSLA',
    section: 'financial_statements',
  },
];

interface SampleQuestionChipsProps {
  onSelect: (question: SampleQuestion) => void;
}

export const SampleQuestionChips: React.FC<SampleQuestionChipsProps> = ({ onSelect }) => {
  const { locale, t } = useLocale();
  const questions = locale === "vi" ? SAMPLE_QUESTIONS_VI : SAMPLE_QUESTIONS;
  return (
    <div className="w-full space-y-2 py-2">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">
        <HelpCircle className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
        <span>{t("suggested.title")}</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {questions.map((q, index) => (
          <button
            key={index}
            type="button"
            id={`sample-question-chip-${index}`}
            onClick={() => onSelect(q)}
            className="group min-h-11 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white hover:bg-brand-indigo/[0.02] dark:bg-[#26324A]/20 dark:hover:bg-brand-indigo/[0.04] border border-slate-200 dark:border-slate-800 hover:border-brand-indigo/40 dark:hover:border-brand-indigo/40 px-3.5 py-2.5 rounded-lg text-left cursor-pointer transition-all duration-300 shadow-4xs font-sans flex items-center gap-2"
          >
            <span className="text-slate-400 dark:text-slate-600 group-hover:text-brand-indigo transition-all duration-300 transform group-hover:translate-x-0.5">▸</span>
            <span className="group-hover:text-[#26324A] dark:group-hover:text-[#FCFBF8] transition-colors duration-300">{q.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
