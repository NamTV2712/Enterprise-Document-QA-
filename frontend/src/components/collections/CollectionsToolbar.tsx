import { LayoutGrid, List, Plus, Search } from "lucide-react";

import type { CollectionSortDirection, CollectionSortField } from "../../types";
import { SelectField } from "../ui/SelectField";

interface CollectionsToolbarProps {
  vi: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  sort: CollectionSortField;
  direction: CollectionSortDirection;
  onSortChange: (value: string) => void;
  view: "grid" | "list";
  onViewChange: (value: "grid" | "list") => void;
  onCreate: () => void;
}

/**
 * The reference's header toolbar. Every control here maps to a real query the
 * DATA-003 list route supports (search, order) or to a real page action; the
 * layout switch is presentation only and stores nothing.
 */
export function CollectionsToolbar({
  vi,
  search,
  onSearchChange,
  sort,
  direction,
  onSortChange,
  view,
  onViewChange,
  onCreate,
}: CollectionsToolbarProps) {
  const sortOptions = [
    { value: "updated_at:desc", label: vi ? "Cập nhật gần nhất" : "Last updated" },
    { value: "updated_at:asc", label: vi ? "Cập nhật cũ nhất" : "Oldest updated" },
    { value: "created_at:desc", label: vi ? "Tạo gần nhất" : "Newest created" },
    { value: "name:asc", label: vi ? "Tên A → Z" : "Name A → Z" },
    { value: "name:desc", label: vi ? "Tên Z → A" : "Name Z → A" },
    { value: "item_count:desc", label: vi ? "Nhiều mục nhất" : "Most items" },
  ];

  return (
    <div className="collections-toolbar">
      <div className="collections-toolbar__search console-input-row">
        <Search aria-hidden="true" />
        <input
          id="collections-search-input"
          className="console-input"
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={vi ? "Tìm bộ sưu tập…" : "Search collections…"}
          aria-label={vi ? "Tìm bộ sưu tập" : "Search collections"}
        />
      </div>
      <SelectField
        className="collections-toolbar__sort"
        label={vi ? "Sắp xếp bộ sưu tập" : "Sort collections"}
        value={`${sort}:${direction}`}
        options={sortOptions}
        onValueChange={onSortChange}
      />
      <div className="collections-view-toggle" role="group" aria-label={vi ? "Kiểu hiển thị" : "Layout"}>
        <button
          type="button"
          className="collections-view-toggle__button"
          aria-pressed={view === "grid"}
          aria-label={vi ? "Xem dạng lưới" : "Grid view"}
          onClick={() => onViewChange("grid")}
        >
          <LayoutGrid className="h-4 w-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          className="collections-view-toggle__button"
          aria-pressed={view === "list"}
          aria-label={vi ? "Xem dạng danh sách" : "List view"}
          onClick={() => onViewChange("list")}
        >
          <List className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <button type="button" className="console-btn console-btn--primary collections-toolbar__create" onClick={onCreate}>
        <Plus className="h-4 w-4" aria-hidden="true" />
        {vi ? "Bộ sưu tập mới" : "New Collection"}
      </button>
    </div>
  );
}
