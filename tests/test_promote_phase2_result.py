import json
from pathlib import Path

import pytest

from scripts.promote_phase2_result import _file_sha256, promote
from src.evaluation.context_packing import CONTEXT_STRATEGY_SELECTIVE_V2


BINDING = "sha256:binding"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, Path | str]:
    candidate_path = tmp_path / "candidate.json"
    official_path = tmp_path / "official.json"
    admission_path = tmp_path / "admission.json"
    metrics = {
        "faithfulness": 0.9983,
        "answer_relevancy": 0.9833,
        "context_precision": 0.7413,
        "overall_judge_average": 0.9076,
    }
    old_metrics = {
        "faithfulness": 0.9967,
        "answer_relevancy": 0.9683,
        "context_precision": 0.7347,
        "overall_judge_average": 0.8999,
    }
    cases = [
        {
            "question": f"q{index}",
            "generation_status": "OK",
            "judge_status": "OK",
        }
        for index in range(30)
    ]
    candidate = {
        "official": False,
        "provider_complete": True,
        "benchmark_eligible": True,
        "stopped_reason": None,
        "num_selected": 30,
        "num_generation_ok": 30,
        "num_judged_ok": 30,
        "binding": BINDING,
        "bound_artifact_fingerprint": "sha256:artifact",
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "metrics": {**metrics, "num_judged_ok": 30, "categories": {}},
        "cases": cases,
    }
    official = {
        "official": True,
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "metrics": {**old_metrics, "num_judged_ok": 30, "categories": {}},
    }
    _write(candidate_path, candidate)
    _write(official_path, official)
    admission = {
        "admission": True,
        "passed": True,
        "candidate_path": str(candidate_path),
        "candidate_sha256": _file_sha256(candidate_path),
        "baseline_path": str(official_path),
        "baseline_sha256": _file_sha256(official_path),
        "artifact_fingerprint": "sha256:artifact",
        "binding": BINDING,
        "context_strategy": CONTEXT_STRATEGY_SELECTIVE_V2,
        "expected_cases": 30,
        "candidate_metrics": metrics,
        "baseline_metrics": old_metrics,
        "gates": {"all": True},
    }
    _write(admission_path, admission)
    return {
        "candidate": candidate_path,
        "admission": admission_path,
        "official": official_path,
        "candidate_sha": _file_sha256(candidate_path),
        "admission_sha": _file_sha256(admission_path),
        "official_sha": _file_sha256(official_path),
    }


def _promote(paths: dict[str, Path | str], *, apply: bool) -> dict:
    return promote(
        candidate_path=paths["candidate"],
        admission_path=paths["admission"],
        official_path=paths["official"],
        archive_dir=Path(paths["official"]).parent / "archive",
        receipt_path=Path(paths["official"]).parent / "receipt.json",
        expected_candidate_sha256=str(paths["candidate_sha"]),
        expected_admission_sha256=str(paths["admission_sha"]),
        expected_official_sha256=str(paths["official_sha"]),
        expected_binding=BINDING,
        apply=apply,
    )


def test_dry_run_is_read_only(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    before = Path(paths["official"]).read_bytes()

    receipt = _promote(paths, apply=False)

    assert receipt["applied"] is False
    assert Path(paths["official"]).read_bytes() == before
    assert not (tmp_path / "archive").exists()
    assert not (tmp_path / "receipt.json").exists()


def test_apply_archives_old_bytes_and_atomically_promotes(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    before = Path(paths["official"]).read_bytes()

    receipt = _promote(paths, apply=True)

    promoted = json.loads(Path(paths["official"]).read_text(encoding="utf-8"))
    archive = Path(receipt["archive_path"])
    assert receipt["applied"] is True
    assert promoted["official"] is True
    assert promoted["benchmark_eligible"] is True
    assert promoted["promotion"]["candidate_sha256"] == paths["candidate_sha"]
    assert archive.read_bytes() == before
    assert _file_sha256(Path(paths["official"])) == receipt["promoted_official_sha256"]
    assert json.loads((tmp_path / "receipt.json").read_text(encoding="utf-8")) == receipt


def test_source_drift_is_rejected_before_any_write(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    Path(paths["candidate"]).write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="candidate drift"):
        _promote(paths, apply=True)

    assert not (tmp_path / "archive").exists()
    assert not (tmp_path / "receipt.json").exists()


def test_failed_admission_is_rejected_before_any_write(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    admission_path = Path(paths["admission"])
    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    admission["passed"] = False
    _write(admission_path, admission)
    paths["admission_sha"] = _file_sha256(admission_path)

    with pytest.raises(RuntimeError, match="not a passing decision"):
        _promote(paths, apply=True)

    assert not (tmp_path / "archive").exists()


def test_archive_collision_cannot_overwrite_official(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    archive = archive_dir / (
        f"official_{str(paths['official_sha']).removeprefix('sha256:')}.json"
    )
    archive.write_text("different", encoding="utf-8")
    before = Path(paths["official"]).read_bytes()

    with pytest.raises(RuntimeError, match="immutable archive collision"):
        _promote(paths, apply=True)

    assert Path(paths["official"]).read_bytes() == before
