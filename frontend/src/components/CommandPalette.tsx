import { useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart3,
  BookOpen,
  FileText,
  FlaskConical,
  HelpCircle,
  Network,
  Search,
  Settings2,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import { COMMAND_REGISTRY, type CommandIcon } from "../lib/commandRegistry";
import { getResearchTemplateCopy, RESEARCH_TEMPLATES, type ResearchTemplate } from "../lib/researchTemplates";
import { normalizeLocaleSearch, useLocale } from "../lib/i18n";
import type { WorkspaceView } from "../lib/workspace";
import { ModalDialog } from "./ui/ModalDialog";

export type PaletteView = WorkspaceView;

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onNavigate: (view: PaletteView) => void;
  onTemplate: (template: ResearchTemplate) => void;
  onHelp: () => void;
  onNewConversation: () => void;
}

interface PaletteItem {
  id: string;
  kind: "navigation" | "utility" | "template";
  label: string;
  description?: string;
  icon: CommandIcon;
  run: () => void;
}

const ICONS: Record<CommandIcon, LucideIcon> = {
  analytics: BarChart3,
  book: BookOpen,
  file: FileText,
  flask: FlaskConical,
  help: HelpCircle,
  network: Network,
  search: Search,
  settings: Settings2,
  sparkles: Sparkles,
};

function optionId(id: string): string {
  return `command-palette-option-${id}`;
}

export function CommandPalette({
  open,
  onClose,
  onNavigate,
  onTemplate,
  onHelp,
  onNewConversation,
}: CommandPaletteProps) {
  const { locale, t } = useLocale();
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const items = useMemo<PaletteItem[]>(() => {
    const commandItems = COMMAND_REGISTRY.map((command) => ({
      id: command.id,
      kind: command.kind,
      label: t(command.labelKey),
      icon: command.icon,
      run: () => {
        if (command.action === "navigate" && command.view) onNavigate(command.view);
        if (command.action === "help") onHelp();
        if (command.action === "new-conversation") onNewConversation();
      },
    }));
    const templateItems = RESEARCH_TEMPLATES.map((template) => {
      const copy = getResearchTemplateCopy(template, locale);
      return {
        id: `template-${template.id}`,
        kind: "template" as const,
        label: copy.label,
        description: copy.description,
        icon: "sparkles" as const,
        run: () => onTemplate(template),
      };
    });
    return [...commandItems, ...templateItems];
  }, [locale, onHelp, onNavigate, onNewConversation, onTemplate, t]);

  const filtered = useMemo(() => {
    const folded = normalizeLocaleSearch(query.trim());
    return items.filter((item) => {
      if (!folded) return true;
      const template = item.kind === "template"
        ? RESEARCH_TEMPLATES.find((candidate) => `template-${candidate.id}` === item.id)
        : undefined;
      const copy = template ? getResearchTemplateCopy(template, locale) : undefined;
      const keywords = template?.copy[locale].keywords ?? [];
      return normalizeLocaleSearch(
        [item.label, item.description, ...(copy ? [copy.question] : []), ...keywords]
          .filter(Boolean)
          .join(" "),
      ).includes(folded);
    });
  }, [items, locale, query]);

  useEffect(() => {
    setActiveIndex(filtered.length > 0 ? 0 : -1);
  }, [filtered.length, locale, query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveIndex(0);
    }
  }, [open]);

  useEffect(() => {
    if (activeIndex < 0) return;
    document.getElementById(optionId(filtered[activeIndex]?.id ?? ""))?.scrollIntoView?.({ block: "nearest" });
  }, [activeIndex, filtered]);

  const moveActive = (direction: 1 | -1) => {
    if (filtered.length === 0) return;
    setActiveIndex((current) => (current + direction + filtered.length) % filtered.length);
  };

  const runActive = () => {
    const item = filtered[activeIndex];
    if (!item) return;
    item.run();
    onClose();
  };

  const onQueryKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveActive(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveActive(-1);
    } else if (event.key === "Home") {
      event.preventDefault();
      setActiveIndex(filtered.length > 0 ? 0 : -1);
    } else if (event.key === "End") {
      event.preventDefault();
      setActiveIndex(filtered.length - 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      runActive();
    }
  };

  const renderItem = (item: PaletteItem, index: number) => {
    const Icon = ICONS[item.icon];
    const active = index === activeIndex;
    return (
      <button
        key={item.id}
        id={optionId(item.id)}
        type="button"
        role="option"
        aria-selected={active}
        className={`command-palette__option ${active ? "is-active" : ""}`}
        onMouseEnter={() => setActiveIndex(index)}
        onFocus={() => setActiveIndex(index)}
        onClick={() => {
          item.run();
          onClose();
        }}
      >
        <Icon className="command-palette__icon" aria-hidden="true" />
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-[var(--text-primary)]">{item.label}</span>
          {item.description && <span className="block text-xs text-[var(--text-muted)]">{item.description}</span>}
        </span>
      </button>
    );
  };

  const navigationItems = filtered.filter((item) => item.kind === "navigation");
  const utilityItems = filtered.filter((item) => item.kind === "utility");
  const templateItems = filtered.filter((item) => item.kind === "template");

  return (
    <ModalDialog
      open={open}
      onClose={onClose}
      labelledBy="command-palette-title"
      initialFocusRef={inputRef}
      overlayClassName="items-start pt-[12vh]"
      className="w-full max-w-2xl overflow-hidden rounded-2xl border border-[var(--border-subtle)] surface-raised shadow-2xl"
    >
      <h2 id="command-palette-title" className="sr-only">{t("palette.title")}</h2>
      <div className="flex items-center gap-3 border-b border-[var(--border-subtle)] p-3">
        <Search className="h-5 w-5 text-[var(--text-subtle)]" aria-hidden="true" />
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onQueryKeyDown}
          placeholder={t("palette.search")}
          aria-label={t("palette.searchAria")}
          aria-controls="command-palette-options"
          aria-activedescendant={activeIndex >= 0 ? optionId(filtered[activeIndex]?.id ?? "") : undefined}
          className="min-w-0 flex-1 bg-transparent text-sm text-[var(--text-primary)] outline-none"
        />
        <kbd className="hidden rounded border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--text-muted)] sm:inline">Esc</kbd>
      </div>
      <div
        id="command-palette-options"
        role="listbox"
        aria-label={t("palette.title")}
        className="max-h-[60vh] overflow-y-auto p-2"
      >
        {navigationItems.length > 0 && <div className="command-palette__heading">{t("palette.navigate")}</div>}
        {navigationItems.map((item) => renderItem(item, filtered.indexOf(item)))}
        {utilityItems.length > 0 && <div className="command-palette__heading is-spaced">{t("palette.utilities")}</div>}
        {utilityItems.map((item) => renderItem(item, filtered.indexOf(item)))}
        {templateItems.length > 0 && <div className="command-palette__heading is-spaced">{t("palette.templates")}</div>}
        {templateItems.map((item) => renderItem(item, filtered.indexOf(item)))}
        {filtered.length === 0 && <p className="px-3 py-4 text-sm text-[var(--text-muted)]">{t("palette.noMatch")}</p>}
      </div>
    </ModalDialog>
  );
}
