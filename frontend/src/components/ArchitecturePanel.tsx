import { ExternalLink, FileCode2, Network, Route, Workflow } from "lucide-react";
import { useLocale } from "../lib/i18n";
import { getWorkspaceNavItem } from "../lib/workspace";
import { getSemanticIcon } from "../lib/semanticIcons";

const WORKSPACE_META = getWorkspaceNavItem("architecture");

const DIAGRAMS = [
  {
    id: "architecture",
    label: "System architecture",
    vi: "Kiến trúc hệ thống",
    description: "Browser, API, retrieval, evidence storage, and the provider boundary.",
    viDescription: "Browser, API, retrieval, kho evidence và ranh giới provider.",
    file: "/architecture/sec-research-workspace.html",
    icon: Network,
  },
  {
    id: "dataflow",
    label: "Query data flow",
    vi: "Luồng dữ liệu truy vấn",
    description: "How a scoped question becomes ranked evidence and a cited answer.",
    viDescription: "Cách câu hỏi có scope trở thành evidence xếp hạng và câu trả lời có citation.",
    file: "/architecture/sec-research-query.html",
    icon: Route,
  },
  {
    id: "workflow",
    label: "Research workflow",
    vi: "Quy trình nghiên cứu",
    description: "The analyst journey from question to verification and recovery.",
    viDescription: "Hành trình từ câu hỏi đến kiểm chứng và recovery.",
    file: "/architecture/sec-research-workflow.html",
    icon: Workflow,
  },
] as const;

export function ArchitecturePanel() {
  const { locale, t } = useLocale();
  const vi = locale === "vi";
  const ToolIcon = getSemanticIcon(WORKSPACE_META.icon);

  return (
    <section className="workspace-page workspace-page--wide architecture-page" aria-labelledby="architecture-title">
      <div className="workspace-page__intro">
        <div>
          <div className="workspace-eyebrow"><ToolIcon className="h-3.5 w-3.5" />{vi ? "Bản đồ hệ thống" : "System map"}</div>
          <h1 id="architecture-title">Architecture</h1>
          <p>{vi ? `${t(WORKSPACE_META.descriptionKey)} Mở sơ đồ độc lập để tìm, phóng to và xuất bản đồ mà không tạo thêm vùng cuộn.` : `${t(WORKSPACE_META.descriptionKey)} Open a standalone diagram to search, zoom, and export the map without creating a second scroll region in the workspace.`}</p>
        </div>
      </div>
      <div className="architecture-launch-grid">
        {DIAGRAMS.map(({ id, label, vi: viLabel, description, viDescription, file, icon: Icon }) => (
          <article key={id} className="architecture-launch-card">
            <Icon className="h-5 w-5 text-[var(--primary)]" aria-hidden="true" />
            <h2>{vi ? viLabel : label}</h2>
            <p>{vi ? viDescription : description}</p>
            <a className="workspace-link-button" href={file} target="_blank" rel="noreferrer">
              {vi ? "Mở viewer" : "Open viewer"}<ExternalLink className="h-3.5 w-3.5" />
            </a>
          </article>
        ))}
      </div>
      <div className="architecture-note" role="note"><FileCode2 className="h-4 w-4" aria-hidden="true" />{vi ? "Các artifact được tạo deterministically từ source-backed Archify specification. Phiên bản tĩnh và giải thích dành cho repository nằm trong ARCHITECTURE.md." : "Artifacts are generated deterministically from source-backed Archify specifications. Static repository diagrams and explanations are in ARCHITECTURE.md."}</div>
    </section>
  );
}
