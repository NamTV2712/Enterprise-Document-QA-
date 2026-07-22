/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { motion } from 'motion/react';
import { HelpCircle } from 'lucide-react';

export interface SampleQuestion {
  text: string;
  label: string;
  ticker?: string;
  section?: string;
}

export const SAMPLE_QUESTIONS: SampleQuestion[] = [
  {
    text: 'Compare the primary business risk factors between Apple (AAPL) and Microsoft (MSFT) for the latest fiscal year.',
    label: 'AAPL vs MSFT Risk Factors',
    ticker: '',
    section: 'risk_factors',
  },
  {
    text: "What are Google's (GOOGL) main sources of business revenue and products according to their 10-K?",
    label: 'GOOGL Business Segments',
    ticker: 'GOOGL',
    section: 'business',
  },
  {
    text: 'Summarize the primary MD&A (Management Discussion & Analysis) findings in Amazon (AMZN) latest 10-K.',
    label: 'AMZN MD&A Highlights',
    ticker: 'AMZN',
    section: 'mdna',
  },
  {
    text: 'What are the major financial tables or statements trends highlighted in Tesla (TSLA) filings?',
    label: 'TSLA Financial Statements',
    ticker: 'TSLA',
    section: 'financial_statements',
  },
];

interface SampleQuestionChipsProps {
  onSelect: (question: SampleQuestion) => void;
}

export const SampleQuestionChips: React.FC<SampleQuestionChipsProps> = ({ onSelect }) => {
  return (
    <div className="w-full space-y-2 py-2">
      <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-450 dark:text-slate-500 uppercase tracking-wider">
        <HelpCircle className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
        <span>Suggested research questions</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {SAMPLE_QUESTIONS.map((q, index) => (
          <motion.button
            key={index}
            whileHover={{ scale: 1.01, x: 4 }}
            whileTap={{ scale: 0.99 }}
            type="button"
            id={`sample-question-chip-${index}`}
            onClick={() => onSelect(q)}
            className="group text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white hover:bg-brand-indigo/[0.02] dark:bg-[#1B2430]/20 dark:hover:bg-brand-indigo/[0.04] border border-slate-200 dark:border-slate-800 hover:border-brand-indigo/40 dark:hover:border-brand-indigo/40 px-3.5 py-2.5 rounded text-left cursor-pointer transition-all duration-300 shadow-4xs font-mono flex items-center gap-2"
          >
            <span className="text-slate-400 dark:text-slate-600 group-hover:text-brand-indigo transition-all duration-300 transform group-hover:translate-x-0.5">▸</span>
            <span className="group-hover:text-[#1B2430] dark:group-hover:text-[#F7F7F5] transition-colors duration-300">{q.label}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
};
