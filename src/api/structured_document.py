"""Safe, bounded structured representation of a canonical SEC HTML source."""
from __future__ import annotations

import hashlib
import html
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field

from configs.settings import settings
from src.api.original_viewer import OriginalViewer, OriginalViewerError
from src.api.original_location import whitespace_literal_matches


MAX_NESTING_DEPTH = 128
MAX_SOURCE_NODES = 250_000
MAX_SOURCE_CODEPOINTS = 4_000_000
MAX_SOURCE_SET_CODEPOINTS = 8_000_000
MAX_CONTENT_BLOCKS = 64
MAX_CONTENT_CODEPOINTS = 32_000
MAX_TABLE_CELLS = 2_000
MAX_RESPONSE_BYTES = 512 * 1024
MAX_SEARCH_RESULTS = 50
MAX_CACHE_BYTES = 128 * 1024 * 1024
MAX_CACHE_ENTRY_BYTES = 64 * 1024 * 1024
MAX_SERIALIZED_ENTRY_BYTES = 32 * 1024 * 1024


class StructuredDocumentError(OriginalViewerError):
    pass


class StructuredRun(BaseModel):
    text: str
    emphasis: bool = False
    strong: bool = False
    superscript: bool = False
    subscript: bool = False


class StructuredCell(BaseModel):
    text: str
    rowspan: int = Field(default=1, ge=1, le=128)
    colspan: int = Field(default=1, ge=1, le=128)
    header: bool = False


class StructuredBlock(BaseModel):
    block_id: str
    kind: Literal["heading", "paragraph", "list", "table", "separator", "unsupported"]
    text: str = ""
    runs: list[StructuredRun] = Field(default_factory=list)
    level: int | None = Field(default=None, ge=1, le=6)
    anchor: str | None = None
    items: list[str] = Field(default_factory=list)
    caption: str | None = None
    units: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[StructuredCell]] = Field(default_factory=list)
    continuation_index: int | None = None
    continuation_count: int | None = None
    source_text: str = ""


class OutlineItem(BaseModel):
    block_id: str
    label: str
    level: int
    anchor: str


class StructuredDocument(BaseModel):
    document_id: str
    source_document_id: str
    source_set_revision: str
    document_revision: str
    representation_revision: str
    blocks: list[StructuredBlock]
    outline: list[OutlineItem]
    complete: bool
    limitations: list[str] = Field(default_factory=list)


class StructuredOutlineResponse(BaseModel):
    document_id: str
    source_document_id: str
    source_set_revision: str
    document_revision: str
    items: list[OutlineItem]
    next_cursor: int | None
    complete: bool
    limitations: list[str]


class StructuredContentResponse(BaseModel):
    document_id: str
    source_document_id: str
    source_set_revision: str
    document_revision: str
    blocks: list[StructuredBlock]
    previous_cursor: int | None
    next_cursor: int | None
    complete: bool
    limitations: list[str]


class StructuredSearchMatch(BaseModel):
    block_id: str
    block_index: int
    start: int
    end: int
    quote: str


class StructuredSearchResponse(BaseModel):
    document_id: str
    source_document_id: str
    source_set_revision: str
    document_revision: str
    query: str
    matches: list[StructuredSearchMatch]
    total: int
    next_cursor: int | None
    complete: bool


def _text(tag: Tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def _slug(value: str, index: int) -> str:
    folded = "-".join(value.casefold().split())
    safe = "".join(char if char.isalnum() or char == "-" else "-" for char in folded).strip("-")
    return f"reader-{safe[:72] or 'section'}-{index}"


def _block_id(source_id: str, index: int, kind: str, value: str) -> str:
    digest = hashlib.sha256(f"{source_id}\0{index}\0{kind}\0{value}".encode("utf-8")).hexdigest()
    return f"block-{digest[:20]}"


def _runs(tag: Tag) -> list[StructuredRun]:
    result: list[StructuredRun] = []

    def visit(node: Any, *, emphasis: bool = False, strong: bool = False, superscript: bool = False, subscript: bool = False) -> None:
        if isinstance(node, str):
            value = " ".join(node.split())
            if value:
                result.append(StructuredRun(text=value, emphasis=emphasis, strong=strong, superscript=superscript, subscript=subscript))
            return
        if not isinstance(node, Tag) or node.name in {"script", "style", "noscript", "template"}:
            return
        name = node.name.casefold()
        for child in node.children:
            visit(child, emphasis=emphasis or name in {"em", "i"}, strong=strong or name in {"strong", "b"}, superscript=superscript or name == "sup", subscript=subscript or name == "sub")

    visit(tag)
    return result


def _table_blocks(tag: Tag, source_id: str, ordinal: int) -> list[StructuredBlock]:
    rows: list[list[StructuredCell]] = []
    caption = _text(tag.find("caption")) if tag.find("caption") else None
    for row in tag.find_all("tr"):
        cells: list[StructuredCell] = []
        for cell in row.find_all(["th", "td"], recursive=False):
            try:
                rowspan = min(128, max(1, int(cell.get("rowspan", 1))))
            except (TypeError, ValueError):
                rowspan = 1
            try:
                colspan = min(128, max(1, int(cell.get("colspan", 1))))
            except (TypeError, ValueError):
                colspan = 1
            cells.append(StructuredCell(text=_text(cell), rowspan=rowspan, colspan=colspan, header=cell.name == "th"))
        if cells:
            rows.append(cells)
    total_cells = sum(len(row) for row in rows)
    if not rows or total_cells > MAX_TABLE_CELLS:
        message = "This table is too large or malformed for structured rendering; use normalized text."
        return [StructuredBlock(block_id=_block_id(source_id, ordinal, "unsupported", message), kind="unsupported", text=message, source_text=message)]
    columns = [cell.text for cell in rows[0]] if rows else []
    chunks: list[StructuredBlock] = []
    chunk_rows: list[list[StructuredCell]] = []
    chunk_cells = 0
    for row in rows:
        if chunk_rows and chunk_cells + len(row) > MAX_TABLE_CELLS:
            chunks.append(StructuredBlock(block_id=_block_id(source_id, ordinal + len(chunks), "table", json.dumps([[cell.model_dump(mode="json") for cell in row] for row in chunk_rows], ensure_ascii=False, sort_keys=True)), kind="table", caption=caption, columns=columns, rows=chunk_rows, source_text=" ".join(cell.text for item in chunk_rows for cell in item)))
            chunk_rows = []
            chunk_cells = 0
        chunk_rows.append(row)
        chunk_cells += len(row)
    if chunk_rows:
        chunks.append(StructuredBlock(block_id=_block_id(source_id, ordinal + len(chunks), "table", json.dumps([[cell.model_dump(mode="json") for cell in row] for row in chunk_rows], ensure_ascii=False, sort_keys=True)), kind="table", caption=caption, columns=columns, rows=chunk_rows, source_text=" ".join(cell.text for item in chunk_rows for cell in item)))
    if len(chunks) > 1:
        for index, block in enumerate(chunks, 1):
            block.continuation_index = index
            block.continuation_count = len(chunks)
    return chunks


def parse_structured_document(raw: bytes, document_id: str, source_document_id: str, source_set_revision: str, document_revision: str) -> StructuredDocument:
    if len(raw) > settings.viewer_raw_file_max_bytes:
        raise StructuredDocumentError("source_too_large", "The source exceeds the structured reader size limit.", 200)
    try:
        soup = BeautifulSoup(raw, "lxml")
    except Exception as error:
        raise StructuredDocumentError("structured_parse_failed", "The source could not be parsed safely.", 200) from error
    nodes = soup.find_all(True)
    if len(nodes) > MAX_SOURCE_NODES:
        raise StructuredDocumentError("structured_too_complex", "The source has too many HTML nodes for safe rendering.", 200)
    max_depth = 0
    for node in nodes:
        depth = 0
        parent = node.parent
        while isinstance(parent, Tag):
            depth += 1
            parent = parent.parent
        max_depth = max(max_depth, depth)
    if max_depth > MAX_NESTING_DEPTH:
        raise StructuredDocumentError("structured_too_deep", "The source nesting exceeds the structured reader limit.", 200)
    body = soup.body or soup
    blocks: list[StructuredBlock] = []
    outline: list[OutlineItem] = []
    total_codepoints = 0
    supported = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "pre", "li", "table", "hr"}
    unsupported = {"img", "svg", "object", "embed", "iframe", "form", "canvas", "video", "audio"}
    for tag in body.find_all(list(supported | unsupported)):
        if any(parent.name in {"table", "ul", "ol"} for parent in tag.parents if isinstance(parent, Tag)) and tag.name not in {"table", "li"}:
            continue
        if tag.name == "li" and tag.find_parent("li") is not None:
            continue
        value = _text(tag)
        if tag.name in unsupported:
            value = "Unsupported document content is omitted from this text representation."
        if not value and tag.name != "hr":
            continue
        total_codepoints += len(value)
        if total_codepoints > MAX_SOURCE_CODEPOINTS:
            raise StructuredDocumentError("structured_text_too_large", "The source text exceeds the structured reader limit.", 200)
        ordinal = len(blocks)
        if tag.name in unsupported:
            blocks.append(StructuredBlock(block_id=_block_id(source_document_id, ordinal, "unsupported", value), kind="unsupported", text=value, source_text=value))
        elif tag.name == "hr":
            blocks.append(StructuredBlock(block_id=_block_id(source_document_id, ordinal, "separator", ""), kind="separator"))
        elif tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag.name[1:])
            anchor = _slug(value, ordinal)
            block_id = _block_id(source_document_id, ordinal, "heading", value)
            blocks.append(StructuredBlock(block_id=block_id, kind="heading", text=value, runs=_runs(tag), level=level, anchor=anchor, source_text=value))
            outline.append(OutlineItem(block_id=block_id, label=value, level=level, anchor=anchor))
        elif tag.name == "table":
            blocks.extend(_table_blocks(tag, source_document_id, ordinal))
        elif tag.name == "li":
            blocks.append(StructuredBlock(block_id=_block_id(source_document_id, ordinal, "list", value), kind="list", text=value, items=[value], runs=_runs(tag), source_text=value))
        else:
            blocks.append(StructuredBlock(block_id=_block_id(source_document_id, ordinal, "paragraph", value), kind="paragraph", text=value, runs=_runs(tag), source_text=value))
    if total_codepoints > MAX_SOURCE_SET_CODEPOINTS:
        raise StructuredDocumentError("structured_source_set_too_large", "The source set exceeds the structured reader limit.", 200)
    limitations = []
    if not outline:
        limitations.append("No source headings were detected; outline navigation is unavailable.")
    if any(block.kind == "unsupported" for block in blocks):
        limitations.append("Some graphics or unsupported objects are omitted from the text representation.")
    representation_payload = json.dumps(
        {"blocks": [block.model_dump(mode="json") for block in blocks], "outline": [item.model_dump(mode="json") for item in outline]},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    representation_revision = hashlib.sha256(b"sec-structured-reader-v1\0" + representation_payload).hexdigest()
    return StructuredDocument(document_id=document_id, source_document_id=source_document_id, source_set_revision=source_set_revision, document_revision=document_revision, representation_revision=representation_revision, blocks=blocks, outline=outline, complete=True, limitations=limitations)


def _response_size(value: BaseModel) -> int:
    return len(json.dumps(value.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


@dataclass
class _CacheEntry:
    value: StructuredDocument
    size: int


class StructuredDocumentService:
    def __init__(self, viewer: OriginalViewer) -> None:
        self.viewer = viewer
        self._lock = threading.RLock()
        self._cache: OrderedDict[tuple[str, str, str, str], _CacheEntry] = OrderedDict()
        self._cache_bytes = 0

    def _load(self, row: dict[str, Any], source_document_id: str, source_set_revision: str, document_revision: str) -> StructuredDocument:
        raw = self.viewer.source_bytes(row, source_document_id, source_set_revision, document_revision)
        with self._lock:
            key = (str(row["document_id"]), source_document_id, source_set_revision, document_revision)
            entry = self._cache.get(key)
            if entry is not None:
                self._cache.move_to_end(key)
                return entry.value
        value = parse_structured_document(raw, str(row["document_id"]), source_document_id, source_set_revision, document_revision)
        size = len(value.model_dump_json().encode("utf-8"))
        if size <= MAX_CACHE_ENTRY_BYTES and _response_size(value) <= MAX_SERIALIZED_ENTRY_BYTES:
            with self._lock:
                previous = self._cache.pop(key, None)
                if previous:
                    self._cache_bytes -= previous.size
                self._cache[key] = _CacheEntry(value, size)
                self._cache_bytes += size
                while self._cache and self._cache_bytes > MAX_CACHE_BYTES:
                    _, evicted = self._cache.popitem(last=False)
                    self._cache_bytes -= evicted.size
        return value

    def document(self, row: dict[str, Any], source_document_id: str, source_set_revision: str, document_revision: str) -> StructuredDocument:
        return self._load(row, source_document_id, source_set_revision, document_revision)

    def outline(self, row: dict[str, Any], source_document_id: str, source_set_revision: str, document_revision: str, cursor: int, limit: int) -> dict[str, Any]:
        document = self._load(row, source_document_id, source_set_revision, document_revision)
        items = document.outline[cursor : cursor + limit]
        next_cursor = cursor + len(items) if cursor + len(items) < len(document.outline) else None
        return StructuredOutlineResponse(document_id=document.document_id, source_document_id=document.source_document_id, source_set_revision=document.source_set_revision, document_revision=document.document_revision, items=items, next_cursor=next_cursor, complete=next_cursor is None, limitations=document.limitations).model_dump(mode="json")

    def content(self, row: dict[str, Any], source_document_id: str, source_set_revision: str, document_revision: str, cursor: int, limit: int) -> dict[str, Any]:
        document = self._load(row, source_document_id, source_set_revision, document_revision)
        selected: list[StructuredBlock] = []
        codepoints = 0
        cells = 0
        index = cursor
        while index < len(document.blocks) and len(selected) < min(limit, MAX_CONTENT_BLOCKS):
            block = document.blocks[index]
            block_size = len(block.text) + sum(len(item.text) for row in block.rows for item in row)
            block_cells = sum(len(row) for row in block.rows)
            if selected and (codepoints + block_size > MAX_CONTENT_CODEPOINTS or cells + block_cells > MAX_TABLE_CELLS):
                break
            selected.append(block)
            codepoints += block_size
            cells += block_cells
            index += 1
        response = StructuredContentResponse(document_id=document.document_id, source_document_id=document.source_document_id, source_set_revision=document.source_set_revision, document_revision=document.document_revision, blocks=selected, previous_cursor=max(0, cursor - limit) if cursor > 0 else None, next_cursor=index if index < len(document.blocks) else None, complete=index >= len(document.blocks), limitations=document.limitations)
        if _response_size(response) > MAX_RESPONSE_BYTES:
            raise StructuredDocumentError("structured_response_too_large", "The structured content response exceeds the response limit.", 200)
        return response.model_dump(mode="json")

    def search(self, row: dict[str, Any], source_document_id: str, source_set_revision: str, document_revision: str, query: str, cursor: int, limit: int) -> dict[str, Any]:
        document = self._load(row, source_document_id, source_set_revision, document_revision)
        results: list[StructuredSearchMatch] = []
        for block_index, block in enumerate(document.blocks):
            text = block.source_text or block.text
            for start, end in whitespace_literal_matches(text, query.strip()):
                results.append(StructuredSearchMatch(block_id=block.block_id, block_index=block_index, start=start, end=end, quote=text[max(0, start - 80) : min(len(text), end + 160)]))
        page = results[cursor : cursor + min(limit, MAX_SEARCH_RESULTS)]
        next_cursor = cursor + len(page) if cursor + len(page) < len(results) else None
        return StructuredSearchResponse(document_id=document.document_id, source_document_id=document.source_document_id, source_set_revision=document.source_set_revision, document_revision=document.document_revision, query=query.strip(), matches=page, total=len(results), next_cursor=next_cursor, complete=next_cursor is None).model_dump(mode="json")

    def export(self, row: dict[str, Any], source_document_id: str, source_set_revision: str, document_revision: str, output_format: str) -> tuple[bytes, str]:
        document = self._load(row, source_document_id, source_set_revision, document_revision)
        if output_format == "markdown":
            lines: list[str] = []
            for block in document.blocks:
                if block.kind == "heading": lines.append(f"{'#' * (block.level or 1)} {block.text}")
                elif block.kind in {"paragraph", "unsupported"}: lines.append(block.text)
                elif block.kind == "list": lines.extend(f"- {item}" for item in block.items)
                elif block.kind == "separator": lines.append("---")
                elif block.kind == "table":
                    lines.append("| " + " | ".join(block.columns) + " |")
                    lines.append("| " + " | ".join("---" for _ in block.columns) + " |")
                    lines.extend("| " + " | ".join(cell.text.replace("|", "\\|") for cell in row) + " |" for row in block.rows)
            return "\n\n".join(lines).encode("utf-8"), "text/markdown; charset=utf-8"
        parts = ["<article><p>Structured document representation; source values are application-rendered.</p>"]
        for block in document.blocks:
            if block.kind == "heading": parts.append(f'<h{block.level or 1} id="{html.escape(block.anchor or "")}">{html.escape(block.text)}</h{block.level or 1}>')
            elif block.kind in {"paragraph", "unsupported"}: parts.append(f"<p>{html.escape(block.text)}</p>")
            elif block.kind == "list": parts.append("<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in block.items) + "</ul>")
            elif block.kind == "separator": parts.append("<hr>")
            elif block.kind == "table":
                parts.append("<table><thead><tr>" + "".join(f"<th>{html.escape(column)}</th>" for column in block.columns) + "</tr></thead><tbody>")
                parts.extend("<tr>" + "".join(f"<{ 'th' if cell.header else 'td' } rowspan=\"{cell.rowspan}\" colspan=\"{cell.colspan}\">{html.escape(cell.text)}</{ 'th' if cell.header else 'td' }>" for cell in row) + "</tr>" for row in block.rows)
                parts.append("</tbody></table>")
        parts.append("</article>")
        return "".join(parts).encode("utf-8"), "text/html; charset=utf-8"
