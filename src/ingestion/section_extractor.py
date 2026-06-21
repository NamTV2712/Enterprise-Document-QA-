"""
Module: section_extractor.py
Purpose: Convert HTML filing into clean text and extract the 4 sections containing the values
"""

import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SECTION_PATTERNS: dict[str, str] = {
    "business": r"item\s+1[\.\:\-\s]+business",
    "risk_factors": r"item\s+1a[\.\:\-\s]+risk\s+factors",
    "mdna": r"item\s+7[\.\:\-\s]+management.?s\s+discussion",
    "financial_statements": r"item\s+8[\.\:\-\s]+financial\s+statements",
}

MIN_VALID_SECTION_LENGTH = 500  # The character indicates a warning threshold, not a rejection threshold


@dataclass
class ExtractionResult:
    """Return both the results AND warnings — this is the principle of 'fail loud, not
    fail silent'. If only returning a dict of sections, a section being extracted incorrectly
    (too short due to table of contents) will silently pass through the entire pipeline and only
    surface when RAG gives an incorrect answer — at which point debugging backwards is very time-consuming."""
    sections: dict[str, str]
    warnings: list[str] = field(default_factory=list)


def html_to_text(html_content: bytes) -> str:
    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text


def _find_section_starts(text_lower: str) -> dict[str, int]:
    starts: dict[str, int] = {}
    for name, pattern in SECTION_PATTERNS.items():
        matches = [m.start() for m in re.finditer(pattern, text_lower)]
        if matches:
            # Heuristic: Last occurrence = actual content, because the table of contents is always at the beginning of the file
            starts[name] = matches[-1]
        else:
            logger.warning("No match found for section '%s'", name)
    return starts


def extract_sections(text: str) -> ExtractionResult:
    text_lower = text.lower()
    starts = _find_section_starts(text_lower)
    ordered = sorted(starts.items(), key=lambda kv: kv[1])

    sections: dict[str, str] = {}
    warnings: list[str] = []

    for i, (name, start) in enumerate(ordered):
        end = ordered[i + 1][1] if i + 1 < len(ordered) else len(text)
        content = text[start:end].strip()
        sections[name] = content
        if len(content) < MIN_VALID_SECTION_LENGTH:
            warnings.append(
                f"Section '{name}' only has {len(content)} characters — suspicious "
                f"extraction (likely includes table of contents or truncated). Please verify manually."
            )

    for name in set(SECTION_PATTERNS) - set(sections):
        warnings.append(f"Section '{name}' NOT found in this filing")

    return ExtractionResult(sections=sections, warnings=warnings)