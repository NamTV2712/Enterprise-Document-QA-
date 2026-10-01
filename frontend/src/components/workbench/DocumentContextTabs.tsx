import React from "react";
import { useLocale } from "../../lib/i18n";
import type { DocumentContextTab } from "../../lib/workbench";

export interface DocumentContextTabsProps {
  activeTab: DocumentContextTab;
  onTabChange: (tab: DocumentContextTab) => void;
  hasNotes?: boolean;
  idPrefix?: string;
}

/**
 * Context tabs for the document lower panel. The tab list only exposes tabs
 * backed by supplied data; it never invents a notes surface.
 */
export function DocumentContextTabs({
  activeTab,
  onTabChange,
  hasNotes = false,
  idPrefix = "document-context",
}: DocumentContextTabsProps) {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const tabs: Array<{ id: DocumentContextTab; label: string }> = [
    { id: "evidence", label: vi ? "Bằng chứng" : "Evidence" },
    { id: "metadata", label: vi ? "Siêu dữ liệu" : "Metadata" },
  ];
  if (hasNotes) tabs.push({ id: "notes", label: vi ? "Ghi chú" : "Notes" });

  const activeIndex = Math.max(0, tabs.findIndex((tab) => tab.id === activeTab));
  const selectByIndex = (nextIndex: number) => {
    const nextTab = tabs[nextIndex];
    if (nextTab) {
      onTabChange(nextTab.id);
      window.requestAnimationFrame(() => {
        document.getElementById(idPrefix + "-tab-" + nextTab.id)?.focus();
      });
    }
  };
  const selectByOffset = (offset: number) => {
    selectByIndex(Math.min(tabs.length - 1, Math.max(0, activeIndex + offset)));
  };

  return (
    <div
      className="document-context-tabs"
      role="tablist"
      aria-label={vi ? "Ngữ cảnh tài liệu" : "Document context"}
    >
      {tabs.map((tab) => (
        <button
          id={idPrefix + "-tab-" + tab.id}
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-controls={idPrefix + "-panel-" + tab.id}
          tabIndex={activeTab === tab.id ? 0 : -1}
          onClick={() => onTabChange(tab.id)}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight" || event.key === "ArrowDown") {
              event.preventDefault();
              selectByOffset(1);
            } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
              event.preventDefault();
              selectByOffset(-1);
              } else if (event.key === "Home") {
                event.preventDefault();
                selectByIndex(0);
              } else if (event.key === "End") {
                event.preventDefault();
                selectByIndex(tabs.length - 1);
              }
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export default DocumentContextTabs;
