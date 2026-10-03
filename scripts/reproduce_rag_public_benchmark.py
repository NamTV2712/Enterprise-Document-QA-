"""Recompute the fixed public RAG benchmark offline; never generate or judge."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import socket
from tempfile import TemporaryDirectory

BENCHMARK_ID = "filingscope-rag-public-v1"
ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "docs/evaluation"
INPUTS = DIRECTORY / f"{BENCHMARK_ID}.inputs.json"
INPUT_SHA256 = "ccdba7451775a413fc751109fbefdc2af0338a8295284199e3b26055168b7eea"


@contextmanager
def offline():
    """Fail closed before imports as well as during scoring."""
    targets = [(socket.socket, "connect"), (socket.socket, "connect_ex"),
               (socket, "create_connection"), (socket, "getaddrinfo")]
    originals = [(owner, name, getattr(owner, name)) for owner, name in targets]
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(True)
        raise RuntimeError("Public benchmark reproduction forbids network access")

    try:
        for owner, name in targets:
            setattr(owner, name, deny)
        yield
        if attempts:
            raise RuntimeError("A network attempt occurred during offline reproduction")
    finally:
        for owner, name, original in originals:
            setattr(owner, name, original)


def reproduce(inputs: Path = INPUTS):
    """Validate curated provenance, then delegate all metrics to native v1."""
    inputs = inputs.resolve()
    with offline():
        # Transitive canonical imports initialize Settings. An empty import cwd
        # prevents reading a caller's .env without changing the product modules.
        previous = Path.cwd()
        with TemporaryDirectory(prefix="filingscope-rag-import-") as directory:
            try:
                os.chdir(directory)
                from src.evaluation.dataset_binding import evaluation_dataset_revision
                from src.evaluation.judge_checkpoint import compute_judge_binding
                from src.evaluation.generation_checkpoint import sha256_text
                from src.evaluation.native_protocol import (
                    NativeCaseInput, NativeReportBinding, build_native_report,
                    canonical_report_bytes, parse_native_report, preflight_native_cases,
                )
                from src.evaluation.test_set import TestCase
                from src.retrieval.canonical_json import canonical_json_bytes
            finally:
                os.chdir(previous)

        # Git's Windows checkout may use CRLF; the admitted JSON is UTF-8/LF.
        encoded = inputs.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(encoded).hexdigest() != INPUT_SHA256:
            raise ValueError("Frozen public inputs differ from the admitted version")
        payload = json.loads(encoded)
        if payload["schema_version"] != 1 or payload["benchmark_id"] != BENCHMARK_ID:
            raise ValueError("Unsupported public benchmark identity/version")
        binding = NativeReportBinding(**payload["binding"])
        provenance = payload["provenance"]
        dataset = [TestCase(**row) for row in payload["dataset"]]
        if evaluation_dataset_revision(dataset) != binding.dataset_revision:
            raise ValueError("Frozen dataset revision differs from its binding")
        selected = {
            hashlib.sha256(canonical_json_bytes(asdict(case))).hexdigest(): asdict(case)
            for case in dataset if case.priority <= 2
        }
        rows = payload["cases"]
        if len(rows) != 30 or {row["case_id"] for row in rows} != set(selected):
            raise ValueError("Public benchmark must retain the entire 30-case cohort")
        context_set = {
            "renderer": provenance["generation_context_builder_fingerprint"],
            "cases": [{key: row[key] for key in ("case_id", "context_sha256")}
                      for row in sorted(rows, key=lambda item: item["case_id"])],
        }
        context_binding = "sha256:" + hashlib.sha256(canonical_json_bytes(context_set)).hexdigest()
        if context_binding != binding.context_binding:
            raise ValueError("Frozen evidence-set binding differs")
        judge_set = []
        cases = []
        for row in sorted(rows, key=lambda item: item["case_id"]):
            if row["test_case"] != selected[row["case_id"]]:
                raise ValueError("Case labels differ from the frozen full dataset")
            answer_hash = sha256_text(row["answer"])
            if answer_hash != row["answer_sha256"]:
                raise ValueError("Frozen final answer hash differs")
            expected = compute_judge_binding(
                binding.generation_binding,
                sha256_text(json.dumps([answer_hash], separators=(",", ":"))),
                binding.judge_model_id, binding.judge_prompt_sha256,
                provenance["judge_max_tokens"],
                provenance["judge_context_builder_fingerprint"],
            )
            if expected != row["legacy_judge_binding"]:
                raise ValueError("Original per-call judge binding differs")
            judge_set.append({key: row[key] for key in (
                "case_id", "context_sha256", "answer_sha256",
                "legacy_judge_binding", "judge_scores",
            )})
            labels = row["test_case"]
            cases.append(NativeCaseInput(
                case_id=row["case_id"], answer=row["answer"],
                rendered_context=row["rendered_context"],
                ground_truth=labels["ground_truth"],
                required_keywords=tuple(labels["required_keywords"]),
                expects_fallback=labels["expects_fallback"],
                judge_scores=row["judge_scores"],
                generation_context_sha256=row["context_sha256"],
                judge_context_sha256=row["context_sha256"],
                generation_binding=binding.generation_binding,
                judge_binding=binding.judge_binding,
            ))
        batch_hash = "sha256:" + hashlib.sha256(canonical_json_bytes(judge_set)).hexdigest()
        if batch_hash != binding.judge_binding:
            raise ValueError("Publication adapter's frozen judge-set binding differs")
        preflight = preflight_native_cases(cases, binding)
        if preflight.bound_judge_cases != 30 or preflight.cases_requiring_external_judging:
            raise ValueError("Frozen benchmark prerequisites are incomplete")
        report = build_native_report(BENCHMARK_ID, cases, binding)
        encoded_report = canonical_report_bytes(report)
        if report.status != "complete" or canonical_report_bytes(parse_native_report(encoded_report)) != encoded_report:
            raise ValueError("Canonical native report validation failed")
        return report, encoded_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare with the committed native publication")
    parser.add_argument("--output", type=Path, help="Write recomputed native JSON to an explicit local path")
    args = parser.parse_args(argv)
    report, encoded = reproduce()
    if args.check:
        with offline():
            from src.evaluation.native_publication import get_published_native_report
            from src.evaluation.native_protocol import canonical_report_bytes
            published = get_published_native_report(BENCHMARK_ID, root=DIRECTORY)
            if published is None or canonical_report_bytes(published.report) != encoded:
                raise ValueError("Committed publication differs from the reproduced report")
    if args.output:
        args.output.write_bytes(encoded + b"\n")
    print(json.dumps({"benchmark_id": BENCHMARK_ID, "status": report.status,
                      "digest": report.digest, "live_provider_calls": 0,
                      "metrics": [asdict(row) for row in report.aggregates]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
