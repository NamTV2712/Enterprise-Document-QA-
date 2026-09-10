import {
  Banknote,
  Building2,
  ChartNoAxesCombined,
  CircleHelp,
  ClipboardCheck,
  Compass,
  Copy,
  Files,
  FileText,
  FlaskConical,
  GitCompareArrows,
  Info,
  Library,
  ListFilter,
  MessageSquare,
  MessageSquarePlus,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Quote,
  Search,
  Server,
  ShieldAlert,
  StickyNote,
  TrendingUp,
  Workflow,
  BookmarkCheck,
  BookmarkPlus,
  Download,
  RefreshCw,
  type LucideIcon,
} from "lucide-react";

/** Semantic icon keys are shared by navigation, palette, panels and actions. */
export type SemanticIconKey =
  | "research"
  | "conversation"
  | "documents"
  | "search"
  | "library"
  | "retrieval"
  | "evaluation"
  | "analytics"
  | "architecture"
  | "system"
  | "sources"
  | "reader"
  | "citation"
  | "execution"
  | "metadata"
  | "help"
  | "newConversation"
  | "copy"
  | "saveSource"
  | "savedSource"
  | "note"
  | "export"
  | "retry"
  | "sidebarClose"
  | "sidebarOpen"
  | "templateRevenue"
  | "templateGrowth"
  | "templateDependency"
  | "templateRisk"
  | "templateSourceAudit"
  | "templateSummary";

export const SEMANTIC_ICONS: Record<SemanticIconKey, LucideIcon> = {
  research: Compass,
  conversation: MessageSquare,
  documents: Files,
  search: Search,
  library: Library,
  retrieval: FlaskConical,
  evaluation: ClipboardCheck,
  analytics: ChartNoAxesCombined,
  architecture: Network,
  system: Server,
  sources: ListFilter,
  reader: FileText,
  citation: Quote,
  execution: Workflow,
  metadata: Info,
  help: CircleHelp,
  newConversation: MessageSquarePlus,
  copy: Copy,
  saveSource: BookmarkPlus,
  savedSource: BookmarkCheck,
  note: StickyNote,
  export: Download,
  retry: RefreshCw,
  sidebarClose: PanelLeftClose,
  sidebarOpen: PanelLeftOpen,
  templateRevenue: Banknote,
  templateGrowth: TrendingUp,
  templateDependency: GitCompareArrows,
  templateRisk: ShieldAlert,
  templateSourceAudit: Quote,
  templateSummary: Building2,
};

export function getSemanticIcon(key: SemanticIconKey): LucideIcon {
  return SEMANTIC_ICONS[key];
}
