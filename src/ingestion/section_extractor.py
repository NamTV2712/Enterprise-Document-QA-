"""
Module: section_extractor.py
Purpose: Convert HTML filing into clean text and extract the 4 sections containing the values
"""

import logging
import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = logging.getLogger(__name__)

BUSINESS = r"b\s*u\s*s\s*i\s*n\s*e\s*s\s*s"
RISK_FACTORS = r"r\s*i\s*s\s*k\s+f\s*a\s*c\s*t\s*o\s*r\s*s"
MDNA = r"management[�’']?s\s+discussion\s+and\s+analysis"
FINANCIAL_STATEMENTS = r"f\s*i\s*n\s*a\s*n\s*c\s*i\s*a\s*l\s+s\s*t\s*a\s*t\s*e\s*m\s*e\s*n\s*t\s*s"

SECTION_BOUNDARIES = {
    "business": {
        "start": rf"item\s+1\.?\s+{BUSINESS}",
        "end": [rf"item\s+1a\.?\s+{RISK_FACTORS}"],
    },
    "risk_factors": {
        "start": rf"item\s+1a\.?\s+{RISK_FACTORS}",
        "end": [r"item\s+1b\b", r"item\s+1c\b", r"item\s+2\b"],
    },
    "mdna": {
        "start": rf"item\s+7\.?\s+{MDNA}",
        "end": [
            r"statement\s+of\s+management[’']?s\s+responsibility\s+for\s+financial\s+statements",
            r"report\s+of\s+management\s+on\s+internal\s+c\s*ontrol\s+over\s+financial\s+reporting",
            r"item\s+7a\b",
            rf"item\s+8\.?\s+{FINANCIAL_STATEMENTS}",
        ],
    },
    "financial_statements": {
        "start": rf"item\s+8\.?\s+{FINANCIAL_STATEMENTS}",
        "end": [r"item\s+9\b"],
    },
}

MIN_VALID_SECTION_LENGTH = 1000  # Warning threshold, not a rejection threshold.

TRAILING_NOISE_PATTERNS = [
    r"\n+\d{1,4}\s*\n+part\s+[ivx]+\s*(item\s+\d+[a-c]?\.?)?\s*$",
    r"\n+table\s+of\s+contents\s*$",
    r"\n+part\s+[ivx]+\s*$",
]


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
    text = _clean_text(text)
    return text


def _clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("�", "'")

    # SEC HTML sometimes splits all-caps words across lines in headings.
    text = re.sub(r"\bB\s*\n\s*USINESS\b", "BUSINESS", text)
    text = re.sub(r"\bRIS\s*\n\s*K\s+FACTORS\b", "RISK FACTORS", text)
    text = re.sub(r"\bFINANCIAL\s+STATE\s*\n\s*MENTS\b", "FINANCIAL STATEMENTS", text)
    text = re.sub(r"\bINC\s*\n\s*OME\b", "INCOME", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text


def _find_next_boundary(text_lower: str, patterns: list[str], start_pos: int) -> int:
    positions = []
    for pattern in patterns:
        match = re.search(pattern, text_lower[start_pos:])
        if match:
            positions.append(start_pos + match.start())
    return min(positions) if positions else len(text_lower)


def _is_reference_match(name: str, text_lower: str, end_pos: int) -> bool:
    suffix = text_lower[end_pos:end_pos + 80].lstrip()
    if suffix.startswith(("of this", "in this")):
        return True
    if name == "risk_factors" and suffix.startswith(("and ", ";")):
        return True
    return False


def _strip_trailing_noise(content: str) -> str:
    """Remove repeated page headers/markers only when they are at section end."""
    for pattern in TRAILING_NOISE_PATTERNS:
        content = re.sub(pattern, "", content, flags=re.IGNORECASE)
    return content.rstrip()


def _find_sections(text: str, text_lower: str) -> dict[str, str]:
    sections: dict[str, str] = {}

    for name, boundary in SECTION_BOUNDARIES.items():
        for match in re.finditer(boundary["start"], text_lower):
            if _is_reference_match(name, text_lower, match.end()):
                continue

            end = _find_next_boundary(text_lower, boundary["end"], match.end())
            content = _strip_trailing_noise(text[match.start():end].strip())

            # The first match is often in the table of contents. Use the first
            # candidate long enough to contain real section body text.
            if len(content) >= MIN_VALID_SECTION_LENGTH:
                sections[name] = content
                break

    return sections

def extract_sections(text: str) -> ExtractionResult:
    text_lower = text.lower()
    sections = _find_sections(text, text_lower)
    warnings: list[str] = []

    for name, content in sections.items():
        if len(content) < MIN_VALID_SECTION_LENGTH:
            warnings.append(
                f"Section '{name}' only has {len(content)} characters — suspicious "
                f"extraction (likely includes table of contents or truncated). Please verify manually."
            )

    for name in set(SECTION_BOUNDARIES) - set(sections):
        warnings.append(f"Section '{name}' NOT found in this filing")

    return ExtractionResult(sections=sections, warnings=warnings)
