import { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, BookOpen, FileText, FlaskConical, HelpCircle, Search, Settings2, Sparkles } from "lucide-react";
import { RESEARCH_TEMPLATES, ResearchTemplate } from "../lib/researchTemplates";
import { useLocale } from "../lib/i18n";

export type PaletteView = "overview" | "conversation" | "retrieval" | "documents" | "evaluation" | "analytics" | "system";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onNavigate: (view: PaletteView) => void;
  onTemplate: (template: ResearchTemplate) => void;
  onHelp: () => void;
  onNewConversation: () => void;
}

export function CommandPalette({ open, onClose, onNavigate, onTemplate, onHelp, onNewConversation }: CommandPaletteProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const filtered = useMemo(() => {
    const folded = query.trim().toLocaleLowerCase();
    return RESEARCH_TEMPLATES.filter((template) => !folded || `${template.label} ${template.description} ${template.question}`.toLocaleLowerCase().includes(folded));
  }, [query]);
  useEffect(() => {
    if (open) window.requestAnimationFrame(() => inputRef.current?.focus());
    if (!open) setQuery("");
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);
  if (!open) return null;
  const navItems: Array<{ view: PaletteView; label: string; icon: typeof BookOpen }> = [
    { view: "overview", label: vi ? "Tổng quan" : "Overview", icon: BookOpen },
    { view: "conversation", label: vi ? "Nghiên cứu" : "Research", icon: Sparkles },
    { view: "retrieval", label: "Retrieval Lab", icon: FlaskConical },
    { view: "documents", label: vi ? "Tài liệu" : "Documents", icon: FileText },
    { view: "evaluation", label: vi ? "Đánh giá" : "Evaluation", icon: BarChart3 },
    { view: "analytics", label: "Analytics", icon: BarChart3 },
    { view: "system", label: vi ? "Hệ thống" : "System", icon: Settings2 },
  ];
  return <div className="fixed inset-0 z-[70] flex items-start justify-center bg-slate-950/40 p-4 pt-[12vh] backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-[var(--border-subtle)] surface-raised shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="command-palette-title"><div className="flex items-center gap-3 border-b border-[var(--border-subtle)] p-3"><Search className="h-5 w-5 text-[var(--text-subtle)]" /><input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={vi ? "Tìm tính năng hoặc template..." : "Search actions or templates..."} aria-label={vi ? "Tìm trong command palette" : "Search command palette"} className="min-w-0 flex-1 bg-transparent text-sm text-[var(--text-primary)] outline-none" /><kbd className="hidden rounded border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--text-muted)] sm:inline">Esc</kbd></div><div className="max-h-[60vh] overflow-y-auto p-2"><div className="px-2 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--text-subtle)]">{vi ? "Điều hướng" : "Navigate"}</div>{navItems.map(({ view, label, icon: Icon }) => <button key={view} type="button" className="flex min-h-10 w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-[var(--text-primary)] hover:surface-muted-hover" onClick={() => { onNavigate(view); onClose(); }}><Icon className="h-4 w-4 text-violet-600 dark:text-violet-300" />{label}</button>)}<div className="mt-2 px-2 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--text-subtle)]">{vi ? "Tiện ích" : "Utilities"}</div><button type="button" className="flex min-h-10 w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-[var(--text-primary)] hover:surface-muted-hover" onClick={() => { onNewConversation(); onClose(); }}><Sparkles className="h-4 w-4 text-emerald-600 dark:text-emerald-300" />{vi ? "Cuộc trò chuyện mới" : "New conversation"}</button><button type="button" className="flex min-h-10 w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-[var(--text-primary)] hover:surface-muted-hover" onClick={() => { onHelp(); onClose(); }}><HelpCircle className="h-4 w-4 text-sky-600 dark:text-sky-300" />{vi ? "Mở hướng dẫn" : "Open help"}</button><div className="mt-2 px-2 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--text-subtle)]">{vi ? "Mẫu câu hỏi (không tự gửi)" : "Research templates (never auto-send)"}</div>{filtered.length === 0 ? <p className="px-3 py-4 text-sm text-[var(--text-muted)]">{vi ? "Không có template phù hợp." : "No templates match."}</p> : filtered.map((template) => <button key={template.id} type="button" className="flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left hover:surface-muted-hover" onClick={() => { onTemplate(template); onClose(); }}><Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-300" /><span className="min-w-0"><span className="block text-sm font-semibold text-[var(--text-primary)]">{template.label}</span><span className="block text-xs text-[var(--text-muted)]">{template.description}</span></span></button>)}</div></div></div>;
}
