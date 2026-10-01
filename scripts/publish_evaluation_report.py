"""Validate and publish an allowlisted evaluation report for the read-only API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from configs.settings import settings
from src.evaluation.public_report import (
    PublicReportError,
    publish_public_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON report in the public schema")
    parser.add_argument("--output-dir", type=Path, default=settings.data_public_evaluations_dir)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        path = publish_public_report(payload, root=args.output_dir, overwrite=args.overwrite)
    except (OSError, json.JSONDecodeError, PublicReportError) as error:
        parser.error(str(error))
        return 2
    print(json.dumps({"path": str(path), "run_id": path.stem, "published": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
