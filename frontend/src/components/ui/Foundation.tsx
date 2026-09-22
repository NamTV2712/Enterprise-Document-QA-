import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Inbox,
  Info,
  Search,
  X,
  XCircle,
} from "lucide-react";
import {
  useId,
  useMemo,
  useRef,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type TableHTMLAttributes,
} from "react";

import { ModalDialog } from "./ModalDialog";

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export interface PanelProps extends HTMLAttributes<HTMLElement> {
  as?: "section" | "aside" | "div";
  tone?: "default" | "raised" | "muted";
  padding?: "none" | "compact" | "default";
}

export function Panel({ as: Component = "section", tone = "default", padding = "default", className, ...props }: PanelProps) {
  return <Component className={cx("ui-panel", `ui-panel--${tone}`, `ui-panel--padding-${padding}`, className)} {...props} />;
}

export interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  eyebrow?: ReactNode;
  breadcrumbs?: ReactNode;
  actions?: ReactNode;
  className?: string;
  titleId?: string;
}

export function PageHeader({ title, description, eyebrow, breadcrumbs, actions, className, titleId }: PageHeaderProps) {
  const generatedTitleId = useId();
  return (
    <header className={cx("ui-page-header", className)}>
      <div className="ui-page-header__content">
        {breadcrumbs && <div className="ui-page-header__breadcrumbs">{breadcrumbs}</div>}
        {eyebrow && <div className="ui-page-header__eyebrow">{eyebrow}</div>}
        <h1 id={titleId ?? generatedTitleId} className="ui-page-header__title">{title}</h1>
        {description && <div className="ui-page-header__description">{description}</div>}
      </div>
      {actions && <div className="ui-page-header__actions">{actions}</div>}
    </header>
  );
}

export interface MetricCardProps extends HTMLAttributes<HTMLElement> {
  label: ReactNode;
  value: ReactNode;
  detail?: ReactNode;
  trend?: ReactNode;
  trendTone?: "neutral" | "positive" | "warning" | "negative";
  icon?: ReactNode;
}

export function MetricCard({ label, value, detail, trend, trendTone = "neutral", icon, className, ...props }: MetricCardProps) {
  return (
    <article className={cx("ui-metric-card", className)} {...props}>
      <div className="ui-metric-card__header"><span>{label}</span>{icon && <span className="ui-metric-card__icon" aria-hidden="true">{icon}</span>}</div>
      <div className="ui-metric-card__value">{value}</div>
      {(detail || trend) && <div className="ui-metric-card__footer">{detail && <span>{detail}</span>}{trend && <span className={`ui-metric-card__trend ui-metric-card__trend--${trendTone}`}>{trend}</span>}</div>}
    </article>
  );
}

export interface SearchFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
  hideLabel?: boolean;
  onClear?: () => void;
  wrapperClassName?: string;
}

export function SearchField({ label, hideLabel = true, onClear, wrapperClassName, className, value, id, ...props }: SearchFieldProps) {
  const generatedInputId = useId();
  const inputId = id ?? generatedInputId;
  const hasValue = typeof value === "string" ? value.length > 0 : typeof value === "number";
  return (
    <label className={cx("ui-search-field", wrapperClassName)} htmlFor={inputId}>
      <span className={hideLabel ? "sr-only" : "ui-search-field__label"}>{label}</span>
      <span className="ui-search-field__control">
        <Search className="ui-search-field__icon" aria-hidden="true" />
        <input id={inputId} type="search" className={cx("ui-search-field__input", className)} value={value} {...props} />
        {onClear && hasValue && <button type="button" className="ui-search-field__clear" onClick={onClear} aria-label={`Clear ${label}`}><X aria-hidden="true" /></button>}
      </span>
    </label>
  );
}

export interface FilterBarProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  actions?: ReactNode;
}

export function FilterBar({ label, actions, children, className, ...props }: FilterBarProps) {
  return <div className={cx("ui-filter-bar", className)} role="group" aria-label={label} {...props}><div className="ui-filter-bar__fields">{children}</div>{actions && <div className="ui-filter-bar__actions">{actions}</div>}</div>;
}

export interface TabOption {
  id: string;
  label: ReactNode;
  disabled?: boolean;
  panelId?: string;
  badge?: ReactNode;
}

export interface TabsProps {
  label: string;
  value: string;
  options: TabOption[];
  onValueChange: (value: string) => void;
  variant?: "underline" | "contained";
  className?: string;
}

export function Tabs({ label, value, options, onValueChange, variant = "underline", className }: TabsProps) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const tabIdPrefix = useId().replaceAll(":", "");
  const enabled = options.map((option, index) => ({ option, index })).filter(({ option }) => !option.disabled);
  const move = (currentIndex: number, offset: -1 | 1) => {
    const currentEnabled = Math.max(0, enabled.findIndex(({ index }) => index === currentIndex));
    const next = enabled[(currentEnabled + offset + enabled.length) % enabled.length];
    if (!next) return;
    onValueChange(next.option.id);
    requestAnimationFrame(() => refs.current[next.index]?.focus());
  };
  return (
    <div className={cx("ui-tabs", `ui-tabs--${variant}`, className)} role="tablist" aria-label={label}>
      {options.map((option, index) => {
        const selected = option.id === value;
        return <button key={option.id} ref={(node) => { refs.current[index] = node; }} type="button" role="tab" id={`${tabIdPrefix}-tab-${index}`} aria-selected={selected} aria-controls={option.panelId} tabIndex={selected ? 0 : -1} disabled={option.disabled} className="ui-tabs__tab" onClick={() => onValueChange(option.id)} onKeyDown={(event) => {
          if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); move(index, 1); }
          if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); move(index, -1); }
          if (event.key === "Home" && enabled[0]) { event.preventDefault(); onValueChange(enabled[0].option.id); refs.current[enabled[0].index]?.focus(); }
          if (event.key === "End" && enabled.at(-1)) { event.preventDefault(); const last = enabled.at(-1)!; onValueChange(last.option.id); refs.current[last.index]?.focus(); }
        }}>{selected && <Check className="ui-tabs__selected-icon" aria-hidden="true" />}<span>{option.label}</span>{option.badge && <span className="ui-tabs__badge">{option.badge}</span>}</button>;
      })}
    </div>
  );
}

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
}

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return <span className={cx("ui-badge", `ui-badge--${tone}`, className)} {...props} />;
}

export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";

const statusIcon = {
  neutral: Info,
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
};

export interface StatusBadgeProps extends Omit<BadgeProps, "tone"> {
  status: StatusTone;
  children: ReactNode;
}

export function StatusBadge({ status, children, className, ...props }: StatusBadgeProps) {
  const Icon = statusIcon[status];
  return <Badge tone={status} className={cx("ui-status-badge", className)} {...props}><Icon aria-hidden="true" /><span>{children}</span></Badge>;
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  size?: "compact" | "default";
  variant?: "ghost" | "outline" | "danger";
}

export function IconButton({ label, size = "default", variant = "ghost", className, children, type = "button", ...props }: IconButtonProps) {
  return <button type={type} aria-label={label} title={props.title ?? label} className={cx("ui-icon-button", `ui-icon-button--${size}`, `ui-icon-button--${variant}`, className)} {...props}>{children}</button>;
}

export interface EmptyStateProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ title, description, icon = <Inbox aria-hidden="true" />, action, compact, className, ...props }: EmptyStateProps) {
  return <div className={cx("ui-empty-state", compact && "ui-empty-state--compact", className)} {...props}><div className="ui-empty-state__icon" aria-hidden="true">{icon}</div><strong className="ui-empty-state__title">{title}</strong>{description && <div className="ui-empty-state__description">{description}</div>}{action && <div className="ui-empty-state__action">{action}</div>}</div>;
}

export interface LoadingSkeletonProps extends HTMLAttributes<HTMLDivElement> {
  label?: string;
  lines?: number;
}

export function LoadingSkeleton({ label = "Loading", lines = 3, className, ...props }: LoadingSkeletonProps) {
  return <div className={cx("ui-loading-skeleton", className)} role="status" aria-label={label} {...props}>{Array.from({ length: Math.max(1, lines) }, (_, index) => <span key={index} className="ui-loading-skeleton__line" style={{ "--skeleton-line": `${Math.max(42, 100 - index * 14)}%` } as CSSProperties} />)}<span className="sr-only">{label}</span></div>;
}

export interface ScoreBadgeProps extends Omit<BadgeProps, "children"> {
  label: string;
  score: number | string;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
}

export function ScoreBadge({ label, score, tone = "info", className, ...props }: ScoreBadgeProps) {
  const display = typeof score === "number" ? (score <= 1 ? score.toFixed(2) : score.toLocaleString()) : score;
  return <Badge tone={tone} className={cx("ui-score-badge", className)} aria-label={`${label}: ${display}`} {...props}><span>{label}</span><strong>{display}</strong></Badge>;
}

function paginationItems(page: number, pageCount: number): Array<number | string> {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, index) => index + 1);
  const values = new Set([1, pageCount, page - 1, page, page + 1].filter((value) => value >= 1 && value <= pageCount));
  const sorted = [...values].sort((a, b) => a - b);
  const result: Array<number | string> = [];
  sorted.forEach((value, index) => {
    if (index > 0 && value - sorted[index - 1] > 1) result.push(`ellipsis-${value}`);
    result.push(value);
  });
  return result;
}

export interface PaginationProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  label?: string;
  className?: string;
}

export function Pagination({ page, pageCount, onPageChange, label = "Pagination", className }: PaginationProps) {
  const items = useMemo(() => paginationItems(page, pageCount), [page, pageCount]);
  if (pageCount <= 1) return null;
  return <nav className={cx("ui-pagination", className)} aria-label={label}><IconButton label="Previous page" size="compact" variant="outline" disabled={page <= 1} onClick={() => onPageChange(page - 1)}><ChevronLeft aria-hidden="true" /></IconButton><div className="ui-pagination__pages">{items.map((item) => typeof item === "number" ? <button key={item} type="button" className="ui-pagination__page" aria-current={item === page ? "page" : undefined} onClick={() => onPageChange(item)}>{item}</button> : <span key={item} className="ui-pagination__ellipsis" aria-hidden="true">…</span>)}</div><IconButton label="Next page" size="compact" variant="outline" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}><ChevronRight aria-hidden="true" /></IconButton></nav>;
}

export interface ChartCardProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  legend?: ReactNode;
  tableAlternative?: ReactNode;
}

export function ChartCard({ title, description, actions, legend, tableAlternative, children, className, ...props }: ChartCardProps) {
  return <section className={cx("ui-chart-card", className)} {...props}><header className="ui-chart-card__header"><div><h2>{title}</h2>{description && <div className="ui-chart-card__description">{description}</div>}</div>{actions && <div className="ui-chart-card__actions">{actions}</div>}</header>{legend && <div className="ui-chart-card__legend">{legend}</div>}<div className="ui-chart-card__plot">{children}</div>{tableAlternative && <details className="ui-chart-card__table"><summary>View data table</summary>{tableAlternative}</details>}</section>;
}

interface OverlayFrameProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  kind: "modal" | "drawer";
  side?: "left" | "right";
  size?: "small" | "medium" | "large";
}

function OverlayFrame({ open, onClose, title, description, children, footer, className, kind, side = "right", size = "medium" }: OverlayFrameProps) {
  const titleId = useId();
  const descriptionId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  return <ModalDialog open={open} onClose={onClose} labelledBy={titleId} describedBy={description ? descriptionId : undefined} initialFocusRef={closeRef} overlayClassName={cx("ui-overlay", kind === "drawer" && `ui-overlay--drawer-${side}`)} className={cx("ui-overlay__surface", `ui-overlay__surface--${kind}`, `ui-overlay__surface--${size}`, kind === "drawer" && `ui-overlay__surface--${side}`, className)}><header className="ui-overlay__header"><div><h2 id={titleId}>{title}</h2>{description && <p id={descriptionId}>{description}</p>}</div><button ref={closeRef} type="button" className="ui-icon-button ui-icon-button--default ui-icon-button--ghost" aria-label="Close" title="Close" onClick={onClose}><X aria-hidden="true" /></button></header><div className="ui-overlay__body">{children}</div>{footer && <footer className="ui-overlay__footer">{footer}</footer>}</ModalDialog>;
}

export type ModalProps = Omit<OverlayFrameProps, "kind" | "side">;
export function Modal(props: ModalProps) { return <OverlayFrame {...props} kind="modal" />; }

export type DrawerProps = Omit<OverlayFrameProps, "kind">;
export function Drawer(props: DrawerProps) { return <OverlayFrame {...props} kind="drawer" />; }

export interface DataTableProps extends TableHTMLAttributes<HTMLTableElement> {
  caption: ReactNode;
  captionHidden?: boolean;
  density?: "compact" | "comfortable";
  wrapperClassName?: string;
}

export function DataTable({ caption, captionHidden = false, density = "comfortable", wrapperClassName, className, children, ...props }: DataTableProps) {
  return <div className={cx("ui-data-table-wrap", wrapperClassName)} tabIndex={0} role="region" aria-label={typeof caption === "string" ? caption : undefined}><table className={cx("ui-data-table", `ui-data-table--${density}`, className)} {...props}><caption className={captionHidden ? "sr-only" : undefined}>{caption}</caption>{children}</table></div>;
}

export interface DetailRailProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function DetailRail({ title, description, actions, children, className, ...props }: DetailRailProps) {
  return <aside className={cx("ui-detail-rail", className)} {...props}><header className="ui-detail-rail__header"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{actions && <div className="ui-detail-rail__actions">{actions}</div>}</header><div className="ui-detail-rail__body">{children}</div></aside>;
}

export interface SplitPaneProps extends HTMLAttributes<HTMLDivElement> {
  primary: ReactNode;
  secondary: ReactNode;
  primaryLabel: string;
  secondaryLabel: string;
  secondaryPosition?: "left" | "right";
  secondaryWidth?: string;
}

export function SplitPane({ primary, secondary, primaryLabel, secondaryLabel, secondaryPosition = "right", secondaryWidth = "22rem", className, style, ...props }: SplitPaneProps) {
  const secondaryFirst = secondaryPosition === "left";
  const mergedStyle = { ...style, "--ui-split-secondary": secondaryWidth } as CSSProperties;
  const primaryPane = <div className="ui-split-pane__primary" aria-label={primaryLabel}>{primary}</div>;
  const secondaryPane = <div className="ui-split-pane__secondary" aria-label={secondaryLabel}>{secondary}</div>;
  return <div className={cx("ui-split-pane", `ui-split-pane--secondary-${secondaryPosition}`, className)} style={mergedStyle} {...props}>{secondaryFirst ? secondaryPane : primaryPane}{secondaryFirst ? primaryPane : secondaryPane}</div>;
}

export interface EvidenceCardProps extends Omit<HTMLAttributes<HTMLElement>, "title" | "onSelect"> {
  title: ReactNode;
  excerpt: ReactNode;
  metadata?: ReactNode;
  leading?: ReactNode;
  trailing?: ReactNode;
  selected?: boolean;
  onSelect?: () => void;
}

export function EvidenceCard({ title, excerpt, metadata, leading, trailing, selected = false, onSelect, className, ...props }: EvidenceCardProps) {
  const content = <>{leading && <div className="ui-evidence-card__leading" aria-hidden="true">{leading}</div>}<div className="ui-evidence-card__content"><div className="ui-evidence-card__title">{selected && <Check aria-hidden="true" />}<strong>{title}</strong></div>{metadata && <div className="ui-evidence-card__metadata">{metadata}</div>}<div className="ui-evidence-card__excerpt">{excerpt}</div></div>{trailing && <div className="ui-evidence-card__trailing">{trailing}</div>}</>;
  if (onSelect) return <button type="button" className={cx("ui-evidence-card", "ui-evidence-card--interactive", selected && "is-selected", className)} aria-pressed={selected} onClick={onSelect}>{content}</button>;
  return <article className={cx("ui-evidence-card", selected && "is-selected", className)} aria-current={selected ? "true" : undefined} {...props}>{content}</article>;
}
