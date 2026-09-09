/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { HelpCircle } from 'lucide-react';
import { useLocale } from "../lib/i18n";
import { getResearchTemplateCopy, RESEARCH_TEMPLATES, type ResearchTemplate } from "../lib/researchTemplates";

export interface SampleQuestion {
  text: string;
  label: string;
  ticker?: string;
  section?: string;
}

interface SampleQuestionChipsProps {
  onSelect: (template: ResearchTemplate) => void;
}

export const SampleQuestionChips: React.FC<SampleQuestionChipsProps> = ({ onSelect }) => {
  const { locale, t } = useLocale();
  return (
    <div className="w-full space-y-2 py-2">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--text-muted)]">
        <HelpCircle className="w-3.5 h-3.5 text-[var(--text-subtle)]" />
        <span>{t("suggested.title")}</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {RESEARCH_TEMPLATES.slice(0, 4).map((template, index) => {
          const copy = getResearchTemplateCopy(template, locale);
          return (
          <button
            key={template.id}
            type="button"
            id={`sample-question-chip-${index}`}
            onClick={() => onSelect(template)}
            className="group flex min-h-11 items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-3.5 py-2.5 text-left font-sans text-sm font-medium text-[var(--text-primary)] shadow-4xs transition-[background-color,border-color,color,transform] duration-150 hover:border-[var(--primary)]/40 hover:bg-[var(--primary-soft)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/30"
          >
            <span className="text-[var(--text-subtle)] transition-[color,transform] duration-150 group-hover:translate-x-0.5 group-hover:text-[var(--accent-text)]">▸</span>
            <span className="transition-colors duration-150 group-hover:text-[var(--accent-text)]">{copy.label}</span>
          </button>
          );
        })}
      </div>
    </div>
  );
};
