from scripts.diagnostics.evidence_contract_v3_manifest import (
    CAMPAIGN_ID,
    MAX_REQUESTS,
    NEW_OUTPUTS,
    build_manifest,
)


def test_manifest_registers_frozen_protocol_and_distinct_outputs() -> None:
    manifest = build_manifest()

    assert manifest["campaign_id"] == CAMPAIGN_ID
    assert manifest["provider_protocol"]["max_requests"] == MAX_REQUESTS == 60
    assert len(manifest["questions"]) == 6
    assert manifest["canonical_artifact"]["matches_expected_embedded_fingerprint"] is True
    assert manifest["passed"] is True
    assert len({str(path) for path in NEW_OUTPUTS}) == len(NEW_OUTPUTS)


def test_manifest_does_not_register_protected_or_legacy_output_paths() -> None:
    manifest = build_manifest()
    outputs = " ".join(manifest["registered_outputs"])

    assert "phase2_results_packed_selective_v2" not in outputs
    assert "phase2_gen.jsonl" not in outputs
    assert "phase2_judge.jsonl" not in outputs
