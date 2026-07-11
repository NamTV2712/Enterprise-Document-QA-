from types import SimpleNamespace

from src.evaluation.evaluator import JUDGE_CONTEXT_CHARS_PER_CHUNK, RAGEvaluator


def test_judge_prompt_includes_evidence_beyond_old_250_character_preview() -> None:
    captured = {}
    evaluator = RAGEvaluator(SimpleNamespace(provider="fake"))

    def fake_call_judge(prompt: str) -> str:
        captured["prompt"] = prompt
        return '{"faithfulness": 1, "faithfulness_reason": "ok", "answer_relevancy": 1, "relevancy_reason": "ok", "context_precision": 1, "precision_reason": "ok"}'

    evaluator._call_judge = fake_call_judge
    context = "x" * 300 + "North America, International, and Amazon Web Services"

    evaluator._judge_all(
        question="What are Amazon's business segments?",
        answer="Amazon operates North America, International, and AWS.",
        context_texts=[context],
        ground_truth="North America, International, and Amazon Web Services.",
    )

    assert JUDGE_CONTEXT_CHARS_PER_CHUNK == 1000
    assert "North America, International" in captured["prompt"]
