"""Pure, local HTML-to-text normalization for the original-source viewer."""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Comment, NavigableString, Tag


NORMALIZER_VERSION = "sec-viewer-text-v1"


class NormalizedTextLimitError(ValueError):
    """Raised when a source exceeds the configured normalized-text limit."""


_SKIP_TAGS = {"head", "script", "style", "template", "noscript"}
_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "body", "caption", "dd", "div",
    "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p",
    "pre", "section", "summary", "table", "tbody", "tfoot", "thead",
    "tr", "ul",
}
_CELL_TAGS = {"td", "th"}


def _hidden(tag: Tag) -> bool:
    name = str(tag.name or "").lower()
    if name in _SKIP_TAGS or name == "ix:hidden": return True
    if tag.has_attr("hidden"): return True
    style = str(tag.get("style") or "")
    return bool(re.search(r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden)\s*(?:;|$)", style, re.I))


def _append_separator(output: list[str], separator: str) -> None:
    if not output or output[-1].endswith(separator): return
    output.append(separator)


def _walk(node: Any, output: list[str]) -> None:
    if isinstance(node, Comment): return
    if isinstance(node, NavigableString):
        output.append(str(node).replace("\r\n", "\n").replace("\r", "\n"))
        return
    if not isinstance(node, Tag) or _hidden(node): return
    name = str(node.name or "").lower()
    if name == "br":
        _append_separator(output, "\n")
        return
    block = name in _BLOCK_TAGS
    if block: _append_separator(output, "\n")
    for child in node.children:
        _walk(child, output)
    if name in _CELL_TAGS:
        _append_separator(output, "\t")
    elif name == "tr":
        _append_separator(output, "\n")
    elif block:
        _append_separator(output, "\n")


def _clean_structural_whitespace(value: str) -> str:
    lines: list[str] = []
    for raw_line in value.split("\n"):
        line = re.sub(r"[ ]+", " ", raw_line).strip(" \t")
        if line: lines.append(line)
    return "\n".join(lines)


def normalize_html(raw: bytes, *, max_codepoints: int = 8_000_000) -> str:
    """Return deterministic body text while executing no HTML, CSS, or URLs."""
    if not isinstance(raw, bytes): raise TypeError("Original source must be bytes")
    soup = BeautifulSoup(raw, "lxml")
    output: list[str] = []
    root = soup.body if soup.body is not None else soup
    _walk(root, output)
    normalized = _clean_structural_whitespace("".join(output))
    if len(normalized) > max_codepoints:
        raise NormalizedTextLimitError("Normalized original source exceeds the configured code-point limit.")
    return normalized
