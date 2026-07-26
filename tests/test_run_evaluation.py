import json

from scripts import run_evaluation


def test_load_checkpoint_only_returns_selected_successes(tmp_path, monkeypatch):
    checkpoint = tmp_path / "checkpoint.jsonl"
    records = [
        {"question": "selected", "status": "OK"},
        {"question": "not selected", "status": "OK"},
        {"question": "failed", "status": "SKIPPED_QUOTA"},
    ]
    checkpoint.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    monkeypatch.setattr(run_evaluation, "CHECKPOINT_PATH", checkpoint)

    assert run_evaluation.load_checkpoint({"selected", "failed"}) == {
        "selected": records[0]
    }
