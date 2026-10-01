import { useEffect, useMemo, useRef, useState } from "react";

import { deriveResearchTemplateScope, getResearchTemplateCopy, getResearchTemplateSchema, renderResearchTemplate, validateResearchTemplateValues, type ResearchTemplate, type ResearchTemplateApplyPayload, type ResearchTemplateParameter, type TemplateValidationIssue } from "../lib/researchTemplates";
import { formatCompanyLabel } from "../lib/displayMetadata";
import { useLocale } from "../lib/i18n";
import { ModalDialog } from "./ui/ModalDialog";
import { SelectField } from "./ui/SelectField";

interface TemplateQuestionDialogProps {
  open: boolean;
  template: ResearchTemplate | null;
  tickers: readonly string[];
  onClose: () => void;
  onApply: (payload: ResearchTemplateApplyPayload) => void;
}

function issueText(issue: TemplateValidationIssue, parameter: ResearchTemplateParameter | undefined, vi: boolean): string {
  const label = parameter?.label[vi ? "vi" : "en"] ?? (vi ? "Trường này" : "This field");
  switch (issue.code) {
    case "required": return vi ? `${label} là bắt buộc.` : `${label} is required.`;
    case "invalid-ticker": return vi ? `${label} phải là ticker có trong corpus hiện tại.` : `${label} must be a ticker in the current searchable corpus.`;
    case "ticker-unavailable": return vi ? "Chưa tải được danh sách ticker có thể tìm kiếm." : "Searchable ticker data is not available yet.";
    case "invalid-year": return vi ? `${label} phải là năm từ 1900 đến hiện tại.` : `${label} must be a year from 1900 through the current year.`;
    case "invalid-length": return vi ? `${label} vượt giới hạn độ dài cho phép.` : `${label} exceeds the allowed length.`;
    case "duplicate-company": return vi ? "Hai công ty phải khác nhau." : "Choose two different companies.";
    case "unresolved-placeholder": return vi ? "Câu hỏi vẫn còn placeholder chưa hoàn tất." : "The question still contains an unfinished placeholder.";
    case "question-too-long": return vi ? "Câu hỏi phải dài từ 5 đến 500 ký tự." : "The question must be between 5 and 500 characters.";
  }
}

function initialValues(template: ResearchTemplate | null): Record<string, string> {
  if (!template) return {};
  return Object.fromEntries(getResearchTemplateSchema(template).map((parameter) => [parameter.key, ""]));
}

export function TemplateQuestionDialog({
  open,
  template,
  tickers,
  onClose,
  onApply,
}: TemplateQuestionDialogProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [values, setValues] = useState<Record<string, string>>(() => initialValues(template));
  const [submitted, setSubmitted] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const schema = useMemo(() => (template ? getResearchTemplateSchema(template) : []), [template]);
  const errors = useMemo(() => {
    if (!template || !submitted) return new Map<string, TemplateValidationIssue>();
    return new Map(validateResearchTemplateValues(template, values, tickers).issues.map((issue) => [issue.key, issue]));
  }, [submitted, template, tickers, values]);

  useEffect(() => {
    if (!open || !template) return;
    setValues(initialValues(template));
    setSubmitted(false);
  }, [open, template]);

  if (!open || !template) return null;

  const updateValue = (key: string, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
    setSubmitted(false);
  };

  const apply = () => {
    const result = validateResearchTemplateValues(template, values, tickers);
    setSubmitted(true);
    if (!result.valid) return;
    onApply({
      templateId: template.id,
      locale,
      question: renderResearchTemplate(template, locale, result.values),
      scope: deriveResearchTemplateScope(template, result.values),
      values: result.values,
    });
  };

  const renderField = (parameter: ResearchTemplateParameter) => {
    const value = values[parameter.key] ?? "";
    const issue = errors.get(parameter.key);
    const label = parameter.label[locale];
    const help = parameter.help?.[locale];
    const errorId = `template-error-${parameter.key}`;
    if (parameter.kind === "ticker") {
      return (
        <div key={parameter.key} className="space-y-1">
          <SelectField
            label={label}
            value={value}
            options={tickers.map((ticker) => ({ value: ticker, label: formatCompanyLabel(ticker) }))}
            onValueChange={(next) => updateValue(parameter.key, next)}
            ariaInvalid={Boolean(issue)}
            ariaDescribedBy={issue ? errorId : undefined}
          />
          {help && <p className="text-xs text-[var(--text-muted)]">{help}</p>}
          {issue && <p id={errorId} className="text-xs text-[var(--state-error-text)]" role="alert">{issueText(issue, parameter, vi)}</p>}
        </div>
      );
    }
    const multiline = parameter.kind === "claim";
    return (
      <label key={parameter.key} className="block space-y-1">
        <span className="text-sm font-semibold text-[var(--text-primary)]">{label}</span>
        {multiline ? (
          <textarea
            value={value}
            rows={3}
            maxLength={240}
            aria-invalid={Boolean(issue)}
            aria-describedby={issue ? errorId : undefined}
            onChange={(event) => updateValue(parameter.key, event.target.value)}
            className="min-h-20 w-full resize-y rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary-soft)]"
          />
        ) : (
          <input
            type={parameter.kind === "year" ? "number" : "text"}
            value={value}
            min={parameter.kind === "year" ? 1900 : undefined}
            max={parameter.kind === "year" ? new Date().getFullYear() : undefined}
            maxLength={parameter.kind === "metric" ? 80 : undefined}
            placeholder={parameter.kind === "year" ? "YYYY" : undefined}
            aria-invalid={Boolean(issue)}
            aria-describedby={issue ? errorId : undefined}
            onChange={(event) => updateValue(parameter.key, event.target.value)}
            className="w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary-soft)]"
          />
        )}
        {help && <span className="block text-xs text-[var(--text-muted)]">{help}</span>}
        {issue && <span id={errorId} className="block text-xs text-[var(--state-error-text)]" role="alert">{issueText(issue, parameter, vi)}</span>}
      </label>
    );
  };

  const questionPreview = renderResearchTemplate(template, locale, values);
  const questionIssue = errors.get("question");

  return (
    <ModalDialog
      open={open}
      onClose={onClose}
      labelledBy="template-question-title"
      initialFocusRef={headingRef}
      className="w-full max-w-xl rounded-2xl border border-[var(--border-subtle)] surface-raised p-5 shadow-2xl"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 ref={headingRef} id="template-question-title" tabIndex={-1} className="text-lg font-semibold text-[var(--text-primary)]">
            {getResearchTemplateCopy(template, locale).label}
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{vi ? "Hoàn tất các trường trước khi đưa câu hỏi vào khung soạn thảo." : "Complete the fields before placing the question in the composer."}</p>
        </div>
      </div>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {schema.map(renderField)}
      </div>
      <div className="mt-5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-3">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-subtle)]">{vi ? "Xem trước câu hỏi" : "Question preview"}</p>
        <p className="mt-2 text-sm text-[var(--text-primary)]">{questionPreview}</p>
        {questionIssue && <p className="mt-2 text-xs text-[var(--state-error-text)]" role="alert">{issueText(questionIssue, undefined, vi)}</p>}
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <button type="button" className="library-secondary-action rounded-lg px-3 py-2 text-sm font-semibold" onClick={onClose}>{vi ? "Hủy" : "Cancel"}</button>
        <button type="button" className="primary-action-button rounded-lg px-3 py-2 text-sm font-semibold" onClick={apply}>{vi ? "Áp dụng vào câu hỏi" : "Use in question"}</button>
      </div>
    </ModalDialog>
  );
}
