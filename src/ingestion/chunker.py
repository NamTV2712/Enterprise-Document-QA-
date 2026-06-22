"""
Module: chunker.py
Purpose: Split extracted filing sections into embedding-ready chunks with metadata.
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import tiktoken

logger = logging.getLogger(__name__)
ENCODING = tiktoken.get_encoding("cl100k_base")

CHUNK_CONFIG = {
    "business": {"chunk_size": 500, "overlap": 75},
    "risk_factors": {"chunk_size": 500, "overlap": 75},
    "mdna": {"chunk_size": 500, "overlap": 75},
    "financial_statements": {"chunk_size": 900, "overlap": 100},
}
SEPARATORS = ["\n\n", "\n", ". ", " "]
CHUNK_JOIN_SEPARATOR = "\n\n"


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def _split_by_separator(text: str, separator: str) -> list[str]:
    return [part.strip() for part in text.split(separator) if part.strip()]


def _recursive_split(text: str, max_tokens: int, separators: list[str]) -> list[str]:
    """Split text under max_tokens, preferring paragraph > line > sentence > word."""
    if count_tokens(text) <= max_tokens:
        return [text.strip()]

    if not separators:
        tokens = ENCODING.encode(text)
        return [
            ENCODING.decode(tokens[i:i + max_tokens]).strip()
            for i in range(0, len(tokens), max_tokens)
        ]

    separator, *rest = separators
    parts = _split_by_separator(text, separator)

    if len(parts) == 1:
        return _recursive_split(text, max_tokens, rest)

    result: list[str] = []
    for part in parts:
        result.extend(_recursive_split(part, max_tokens, rest))
    return result


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Build chunks up to chunk_size tokens with overlap between adjacent chunks."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    units = _recursive_split(text, chunk_size, SEPARATORS)
    chunks: list[str] = []
    current: list[str] = []

    for unit in units:
        if current and count_tokens(CHUNK_JOIN_SEPARATOR.join([*current, unit])) > chunk_size:
            chunks.append(CHUNK_JOIN_SEPARATOR.join(current))

            kept: list[str] = []
            for previous_unit in reversed(current):
                candidate = [previous_unit, *kept]
                if count_tokens(CHUNK_JOIN_SEPARATOR.join(candidate)) > overlap:
                    break
                kept = candidate

            if kept and count_tokens(CHUNK_JOIN_SEPARATOR.join([*kept, unit])) > chunk_size:
                kept = []
            current = kept

        current.append(unit)

    if current:
        chunks.append(CHUNK_JOIN_SEPARATOR.join(current))
    return chunks


@dataclass
class Chunk:
    chunk_id: str
    ticker: str
    section: str
    accession_number: str
    filing_date: str
    report_date: str
    chunk_index: int
    token_count: int
    text: str


def build_chunks_for_filing(filing_data: dict) -> list[Chunk]:
    chunks: list[Chunk] = []
    accession_nodash = filing_data["accession_number"].replace("-", "")

    for section_name, section_text in filing_data["sections"].items():
        config = CHUNK_CONFIG[section_name]
        pieces = chunk_text(section_text, config["chunk_size"], config["overlap"])

        for index, piece in enumerate(pieces):
            chunks.append(Chunk(
                chunk_id=f"{filing_data['ticker']}_{accession_nodash}_{section_name}_{index:04d}",
                ticker=filing_data["ticker"],
                section=section_name,
                accession_number=filing_data["accession_number"],
                filing_date=filing_data["filing_date"],
                report_date=filing_data["report_date"],
                chunk_index=index,
                token_count=count_tokens(piece),
                text=piece,
            ))

        logger.info("%s/%s -> %d chunk(s)", filing_data["ticker"], section_name, len(pieces))

    return chunks


def save_chunks(chunks: list[Chunk], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
