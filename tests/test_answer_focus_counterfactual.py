from scripts.diagnostics.answer_focus_counterfactual import run

from tests.conftest import skip_without_data


@skip_without_data(
    "data/eval_artifacts/phase1_priority2.json",
)
def test_real_answer_focus_counterfactual_is_provider_free(tmp_path) -> None:
    report = run(output=tmp_path / "answer_focus_counterfactual.json")

    assert report["passed"] is True
    assert report["num_cases"] == 30
    assert report["changed_questions"] == [
        "What are all the major risk factors Microsoft discloses?"
    ]
    assert report["gates"]["provider_free"] is True
