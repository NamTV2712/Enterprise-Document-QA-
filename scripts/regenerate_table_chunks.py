"""
Remove existing financial_table chunks before regenerating them.

Run from the project root before `python -m scripts.add_table_chunks` when the
table extraction logic changes. This avoids keeping stale table labels in the
JSONL chunk files.
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    total_removed = 0
    for chunks_file in sorted(Path("data/processed").glob("*/*_chunks.jsonl")):
        lines = [line for line in chunks_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        kept = []
        removed = 0

        for line in lines:
            record = json.loads(line)
            if record.get("section") == "financial_table":
                removed += 1
                continue
            kept.append(line)

        if removed:
            chunks_file.write_text("\n".join(kept) + "\n", encoding="utf-8")
            print(f"{chunks_file}: removed {removed} financial_table chunks")
            total_removed += removed

    print(f"Total removed financial_table chunks: {total_removed}")


if __name__ == "__main__":
    main()
