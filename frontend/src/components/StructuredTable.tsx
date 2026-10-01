import type { ReactNode } from "react";

interface StructuredTableProps {
  caption?: string | null;
  units?: string | null;
  columns: string[];
  rows: string[][];
  emptyLabel?: string;
}

export function StructuredTable({ caption, units, columns, rows, emptyLabel = "No rows" }: StructuredTableProps) {
  return (
    <div className="context-structured-table" role="region" aria-label={caption || "Structured financial table"} tabIndex={0}>
      {caption && <h3>{caption}</h3>}
      {units && <p className="context-structured-table__units">{units}</p>}
      <table>
        <thead><tr>{columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead>
        <tbody>
          {rows.length > 0
            ? rows.map((row, rowIndex) => <tr key={`${rowIndex}-${row[0] ?? ""}`}>{columns.map((_column, columnIndex) => <td key={`${rowIndex}-${columnIndex}`}>{row[columnIndex] ?? ""}</td>)}</tr>)
            : <tr><td colSpan={columns.length}>{emptyLabel}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export function renderStructuredTableNode(detail: { presentation?: { kind: string; caption?: string | null; units?: string | null; columns?: string[]; rows?: string[][] } }): ReactNode | null {
  const presentation = detail.presentation;
  if (presentation?.kind !== "markdown_table" || !presentation.columns || !presentation.rows) return null;
  return <StructuredTable caption={presentation.caption} units={presentation.units} columns={presentation.columns} rows={presentation.rows} />;
}
