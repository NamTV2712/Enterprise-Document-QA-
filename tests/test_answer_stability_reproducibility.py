from scripts.diagnostics.answer_stability_reproducibility import build_report


def _report(binding: str, replicate_id: str) -> dict:
    questions = [f"q-{index}" for index in range(7)]
    rows = {
        question: {
            "v5_context_sha256": f"v5-{question}",
            "v6_context_sha256": f"v6-{question}",
            "selected_chunk_ids": [question],
            "selector_tier": "structured_exact",
            "selector_safe": True,
            "selector_one_source": True,
        }
        for question in questions
    }
    return {
        "passed": True,
        "sentinel_questions": questions,
        "answer_stability_fingerprint": "sha256:2a39e719d04584631b3c3e871c2af7c9a5734cf36412d2f129652ec28e36d7fd",
        "selector_fingerprint": "sha256:a068e14bf0dfaec29be37af653e2ae01b0101fcd91dba51ecbf1918f4489a882",
        "binding": binding,
        "provider_complete": True,
        "replicate_id": replicate_id,
        "replicate_provenance": {
            "one_generation_binding": True,
            "one_judge_binding": True,
        },
        "selector_rows": rows,
    }


def test_reproducibility_requires_same_binding_and_selector_outputs() -> None:
    report = build_report(_report("sha256:b", "r1"), _report("sha256:b", "r2"))

    assert report["passed"] is True
    assert report["gates"]["same_generation_binding"] is True
    assert report["gates"]["same_selector_outputs"] is True
