import json
from tests.conftest import skip_without_data

from scripts.diagnostics.evidence_contract_v3_manifest import (
    CAMPAIGN_ID,
    MAX_REQUESTS,
    NEW_OUTPUTS,
    build_manifest,
    campaign_output_paths,
    verify_manifest,
)


@skip_without_data(
    "data/eval_artifacts/phase1_priority2_financial_table_units.json",
)
def test_manifest_registers_frozen_protocol_and_distinct_outputs() -> None:
    manifest = build_manifest()

    assert manifest["campaign_id"] == CAMPAIGN_ID
    assert manifest["provider_protocol"]["max_requests"] == MAX_REQUESTS == 60
    assert len(manifest["questions"]) == 6
    assert manifest["canonical_artifact"]["matches_expected_embedded_fingerprint"] is True
    assert manifest["passed"] is True
    assert len({str(path) for path in NEW_OUTPUTS}) == len(NEW_OUTPUTS)


@skip_without_data(
    "data/eval_artifacts/phase1_priority2_financial_table_units.json",
)
def test_manifest_does_not_register_protected_or_legacy_output_paths() -> None:
    manifest = build_manifest()
    outputs = " ".join(manifest["registered_outputs"])

    assert "phase2_results_packed_selective_v2" not in outputs
    assert "phase2_gen.jsonl" not in outputs
    assert "phase2_judge.jsonl" not in outputs


@skip_without_data(
    "data/eval_artifacts/phase1_priority2_financial_table_units.json",
)
def test_custom_campaign_identity_gets_distinct_outputs_and_run_ids(tmp_path) -> None:
    campaign_id = "evidence_contract_v3_test_window"
    paths = campaign_output_paths(campaign_id)
    manifest = build_manifest(campaign_id=campaign_id, output_paths=paths)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert manifest["campaign_id"] == campaign_id
    assert manifest["provider_protocol"]["run_ids"] == [
        f"{campaign_id}-r1",
        f"{campaign_id}-r2",
    ]
    assert all(campaign_id in output for output in manifest["registered_outputs"])
    assert verify_manifest(
        manifest_path,
        campaign_id=campaign_id,
        output_paths=paths,
    ) == ()
