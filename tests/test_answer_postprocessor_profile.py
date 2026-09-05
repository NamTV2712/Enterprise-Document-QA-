from src.evaluation.answer_postprocessor_profile import (
    ANSWER_POSTPROCESSOR_PROFILE_PROVIDER_DRAFT,
    build_answer_postprocessor_profile,
)


def test_provider_draft_profile_is_stable_and_nonempty() -> None:
    assert ANSWER_POSTPROCESSOR_PROFILE_PROVIDER_DRAFT.startswith("sha256:")
    assert len(ANSWER_POSTPROCESSOR_PROFILE_PROVIDER_DRAFT) == 71


def test_renderer_toggle_changes_postprocessor_profile() -> None:
    provider_only = build_answer_postprocessor_profile()
    fact_renderer = build_answer_postprocessor_profile(
        deterministic_fact_renderer=True,
    )
    risk_renderer = build_answer_postprocessor_profile(
        deterministic_risk_renderer=True,
    )
    comparative_renderer = build_answer_postprocessor_profile(
        deterministic_comparative_renderer=True,
    )

    assert provider_only != fact_renderer
    assert provider_only != risk_renderer
    assert provider_only != comparative_renderer
    assert fact_renderer != risk_renderer
    assert risk_renderer != comparative_renderer
