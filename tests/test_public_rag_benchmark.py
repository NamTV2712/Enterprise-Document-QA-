"""The public frozen cohort must reproduce and reject input/binding drift."""
import hashlib
import json
import socket

import pytest

from scripts import reproduce_rag_public_benchmark as benchmark
from src.evaluation.native_protocol import NativeProtocolError


def test_public_frozen_report_reproduces_committed_publication():
    assert benchmark.main(["--check"]) == 0
    report, _ = benchmark.reproduce()
    assert report.digest == "sha256:e5c004215a69b5c4094a35467569d3c76f88e17803400881e728fc68c32c9d16"
    assert [(row.value, row.denominator, row.not_applicable_count, row.unavailable_count)
            for row in report.aggregates] == [
        (1.0, 30, 0, 0), (0.9917, 30, 0, 0), (0.7613, 30, 0, 0),
        (1.0, 27, 3, 0), (1.0, 24, 6, 0), (1.0, 30, 0, 0),
    ]


@pytest.mark.parametrize("change", ["cohort", "context", "answer", "judge", "dataset"])
def test_reproduction_rejects_semantic_drift_even_after_repinning(tmp_path, monkeypatch, change):
    payload = json.loads(benchmark.INPUTS.read_bytes())
    row = payload["cases"][0]
    if change == "cohort":
        payload["cases"].pop()
    elif change == "context":
        row["rendered_context"] += " altered evidence"
    elif change == "answer":
        row["answer"] += " altered final answer"
        row["answer_sha256"] = "sha256:" + hashlib.sha256(row["answer"].encode()).hexdigest()
    elif change == "judge":
        row["legacy_judge_binding"] = "sha256:" + "0" * 64
    else:
        payload["dataset"][0]["ground_truth"] += " altered label"
    encoded = json.dumps(payload).encode()
    path = tmp_path / "changed.json"
    path.write_bytes(encoded)
    # Repinning is deliberately test-only: verify the underlying binding gates too.
    monkeypatch.setattr(benchmark, "INPUT_SHA256", hashlib.sha256(encoded).hexdigest())
    with pytest.raises((ValueError, NativeProtocolError)):
        benchmark.reproduce(path)


def test_public_input_hash_rejects_unadmitted_bytes(tmp_path):
    path = tmp_path / "changed.json"
    path.write_bytes(benchmark.INPUTS.read_bytes() + b" ")
    with pytest.raises(ValueError, match="admitted version"):
        benchmark.reproduce(path)


def test_windows_crlf_checkout_preserves_the_frozen_report(tmp_path):
    path = tmp_path / "checkout.json"
    path.write_bytes(benchmark.INPUTS.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    _, reproduced = benchmark.reproduce(path)
    assert reproduced == benchmark.reproduce()[1]


def test_offline_guard_blocks_connection_before_any_network_io():
    with pytest.raises(RuntimeError, match="forbids network access"):
        with benchmark.offline():
            with socket.socket() as client:
                client.connect(("127.0.0.1", 1))
