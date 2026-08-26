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

ANNUAL_REPORT_ANCHOR_LABELS = {
    "business": re.compile(r"^business$", re.IGNORECASE),
    "risk_factors": re.compile(r"^risk factors$", re.IGNORECASE),
    "mdna": re.compile(r"^management.?s discussion and analysis", re.IGNORECASE),
    "financial_statements": re.compile(
        r"^financial statements(?: and (?:supplementary|supplemental) "
        r"(?:data|details)| and notes)?$",
        re.IGNORECASE,
    ),
}

MIN_VALID_SECTION_LENGTH = 1000  # Warning threshold, not a rejection threshold.
# A genuine body heading is followed by at least this much text before any
# end boundary; tighter intervals are table-of-contents page references.
MIN_GENUINE_START_INTERVAL = 200

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
    return _soup_to_text(soup)


def _soup_to_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return _clean_text(text)


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


def _iter_end_candidates(
    text_lower: str, patterns: list[str], start_pos: int
):
    """All end-boundary offsets after ``start_pos``, nearest first."""
    candidates: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text_lower[start_pos:]):
            candidates.append(start_pos + match.start())
    return sorted(set(candidates))


def _extract_valid_content(
    text: str,
    text_lower: str,
    boundary: dict,
    start_match: re.Match,
) -> str | None:
    """Slice from a start heading through the first end boundary that
    yields real section body text.

    Filings embed inline cross-references such as "...related notes in
    Item 8." inside section prose; the nearest end candidate can then cut
    the section after only its introduction. Mirroring the start-side
    rule, too-short slices are skipped and the next end candidate is
    tried while keeping the same start heading.

    A start heading whose very first end candidate sits within
    ``MIN_GENUINE_START_INTERVAL`` characters is a table-of-contents page
    reference, not a section heading, so that candidate is rejected
    outright instead of stretching a slice across unrelated sections.
    """
    first_candidates = _iter_end_candidates(
        text_lower, boundary["end"], start_match.end()
    )
    if not first_candidates:
        content = _strip_trailing_noise(text[start_match.start():].strip())
        return content if len(content) >= MIN_VALID_SECTION_LENGTH else None
    first_interval = first_candidates[0] - start_match.end()
    if first_interval < MIN_GENUINE_START_INTERVAL:
        return None

    cursor = start_match.end()
    while True:
        candidates = _iter_end_candidates(text_lower, boundary["end"], cursor)
        if not candidates:
            content = _strip_trailing_noise(text[start_match.start():].strip())
            return content if len(content) >= MIN_VALID_SECTION_LENGTH else None
        end = candidates[0]
        content = _strip_trailing_noise(text[start_match.start():end].strip())
        if len(content) >= MIN_VALID_SECTION_LENGTH:
            return content
        cursor = end + 1


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


def _strip_leading_noise(content: str) -> str:
    """Remove a repeated annual-report page header without dropping section text."""
    return re.sub(r"^\s*table of contents\s*\n+", "", content, flags=re.IGNORECASE)


def _find_sections(text: str, text_lower: str) -> dict[str, str]:
    sections: dict[str, str] = {}

    for name, boundary in SECTION_BOUNDARIES.items():
        for match in re.finditer(boundary["start"], text_lower):
            if _is_reference_match(name, text_lower, match.end()):
                continue

            content = _extract_valid_content(text, text_lower, boundary, match)
            if content is None:
                continue

            # The first match is often in the table of contents. Use the
            # first candidate long enough to contain real section body text.
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


def _anchor_sections(soup: BeautifulSoup) -> dict[str, str]:
    """Extract annual-report sections linked by same-document TOC anchors."""
    anchors: dict[str, object] = {}
    for link in soup.find_all("a", href=True):
        href = str(link.get("href", ""))
        if not href.startswith("#") or len(href) == 1:
            continue
        label = " ".join(link.get_text(" ", strip=True).split())
        for name, pattern in ANNUAL_REPORT_ANCHOR_LABELS.items():
            if name not in anchors and pattern.match(label):
                target = soup.find(id=href[1:])
                if target is not None:
                    anchors[name] = target
                break

    recovered: dict[str, str] = {}
    ordered = [name for name in ANNUAL_REPORT_ANCHOR_LABELS if name in anchors]
    for index, name in enumerate(ordered):
        start = anchors[name]
        stop = anchors[ordered[index + 1]] if index + 1 < len(ordered) else None
        fragments: list[str] = []
        for node in start.next_elements:
            if node is stop:
                break
            if isinstance(node, str):
                fragments.append(node)
        content = _strip_leading_noise(
            _strip_trailing_noise(_clean_text("\n".join(fragments)).strip())
        )
        if len(content) >= MIN_VALID_SECTION_LENGTH:
            recovered[name] = content
    return recovered


def _heading_section_name(label: str) -> str | None:
    normalized = " ".join(label.split()).casefold().rstrip(".:")
    if normalized in {
        "business",
        "our business",
        "about mcdonald's",
        "about ge aerospace",
        "about honeywell",
    }:
        return "business"
    if normalized == "risk factors":
        return "risk_factors"
    if normalized.startswith("management's discussion and analysis"):
        return "mdna"
    if normalized in {
        "financial statements and supplementary data",
        "financial statements and supplemental details",
        "consolidated financial statements",
    }:
        return "financial_statements"
    return None


def _heading_sections(soup: BeautifulSoup) -> dict[str, str]:
    """Recover non-anchor annual-report layouts from isolated body headings.

    Table-of-contents labels are naturally rejected because the next canonical
    heading follows almost immediately. The longest body interval for each
    label is selected only after it clears the normal section-length threshold.
    """
    headings = [
        (name, node)
        for node in soup.find_all(string=True)
        if (name := _heading_section_name(str(node))) is not None
    ]
    recovered: dict[str, tuple[int, str]] = {}
    for index, (name, start) in enumerate(headings):
        stop = next(
            (
                candidate
                for later_name, candidate in headings[index + 1:]
                if later_name != name
            ),
            None,
        )
        fragments: list[str] = []
        for node in start.next_elements:
            if node is stop:
                break
            if isinstance(node, str):
                fragments.append(node)
        content = _strip_leading_noise(
            _strip_trailing_noise(_clean_text("\n".join(fragments)).strip())
        )
        prefix = content[:1000].casefold()
        required_marker = {
            "business": "business",
            "risk_factors": "risk",
            "mdna": "",
            "financial_statements": "statement",
        }[name]
        if required_marker and required_marker not in prefix:
            continue
        if len(content) >= MIN_VALID_SECTION_LENGTH:
            prior = recovered.get(name)
            if prior is None or len(content) > prior[0]:
                recovered[name] = (len(content), content)
    return {name: content for name, (_, content) in recovered.items()}


def extract_sections_from_html(html_content: bytes) -> ExtractionResult:
    """Use Item boundaries first, then same-document annual-report anchors."""
    soup = BeautifulSoup(html_content, "lxml")
    text = _soup_to_text(soup)
    result = extract_sections(text)
    anchored = _anchor_sections(soup)
    heading_sections = _heading_sections(soup)
    recovered = {**heading_sections, **anchored}
    missing = {
        name: content
        for name, content in recovered.items()
        if name not in result.sections
    }
    if not missing:
        return result

    warnings = [
        warning
        for warning in result.warnings
        if not any(f"Section '{name}' NOT found" in warning for name in missing)
    ]
    warnings.extend(
        f"Section '{name}' recovered through annual-report layout adapter"
        for name in sorted(missing)
    )
    return ExtractionResult(sections={**result.sections, **missing}, warnings=warnings)
