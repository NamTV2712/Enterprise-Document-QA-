import { ArrowRight, GitBranch } from "lucide-react";
import type { RelatedResearchSuggestion } from "../lib/relatedResearch";
import { useLocale } from "../lib/i18n";

interface RelatedResearchPanelProps {
  suggestions: readonly RelatedResearchSuggestion[];
  onSelect: (suggestion: RelatedResearchSuggestion) => void;
}

export function RelatedResearchPanel({ suggestions, onSelect }: RelatedResearchPanelProps) {
  const { locale } = useLocale();
  if (suggestions.length === 0) return null;
  return (
    <section className="related-research-panel" aria-labelledby="related-research-title">
      <div className="related-research-panel__heading">
        <div className="flex min-w-0 items-center gap-2">
          <GitBranch className="h-3.5 w-3.5 shrink-0 text-[var(--accent-text)]" aria-hidden="true" />
          <h3 id="related-research-title">{locale === "vi" ? "Nghiên cứu tiếp theo" : "Related research"}</h3>
        </div>
        <span>{locale === "vi" ? "Chọn để điền vào bản nháp" : "Select to fill the draft"}</span>
      </div>
      <div className="related-research-panel__list">
        {suggestions.map((suggestion) => (
          <button key={suggestion.id} type="button" className="related-research-panel__item" onClick={() => onSelect(suggestion)}>
            <span className="min-w-0">
              <span className="related-research-panel__label">{suggestion.label[locale]}</span>
              <span className="related-research-panel__description">{suggestion.description[locale]}</span>
            </span>
            <ArrowRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
  );
}
