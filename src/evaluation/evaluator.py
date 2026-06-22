"""
Module: evaluator.py
LLM-as-Judge: Use Groq (llama-3.3-70b) to evaluate each RAG response
according to 3 metrics: Faithfulness, Answer Relevancy, and Context Precision.
"""

import json
import logging
import re
from dataclasses import dataclass

from src.generation.generator import Generator
from src.retrieval.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator for RAG (Retrieval-Augmented Generation) systems.
Your job is to evaluate responses objectively and return ONLY valid JSON.
Do not add any explanation outside the JSON object."""


@dataclass
class EvalResult:
    question: str
    faithfulness: float        # 0.0 – 1.0
    answer_relevancy: float    # 0.0 – 1.0
    context_precision: float   # 0.0 – 1.0
    faithfulness_reason: str
    relevancy_reason: str
    precision_reason: str

    @property
    def average_score(self) -> float:
        return round((self.faithfulness + self.answer_relevancy + self.context_precision) / 3, 4)


class RAGEvaluator:
    def __init__(self, judge_generator: Generator):
        # Use a separate generator as a judge — distinct from the generator used for answering.
        # This allows you to use a different model as a judge if needed (to avoid self-judging bias).
        self.judge = judge_generator

    def evaluate_one(
        self,
        question: str,
        answer: str,
        chunks: list[RetrievedChunk],
        ground_truth: str,
    ) -> EvalResult:
        context_texts = [c.text for c in chunks]
        scores = self._judge_all(question, answer, context_texts, ground_truth)
        return EvalResult(question=question, **scores)

    def _judge_all(
        self,
        question: str,
        answer: str,
        context_texts: list[str],
        ground_truth: str,
    ) -> dict:
        context_str = "\n\n".join(
            f"[Chunk {i+1}]: {t[:400]}" for i, t in enumerate(context_texts)
        )
        prompt = f"""Evaluate this RAG system response on 3 metrics. Return ONLY a JSON object.

QUESTION: {question}
GROUND TRUTH: {ground_truth}
RETRIEVED CONTEXT:
{context_str}

SYSTEM ANSWER: {answer}

Evaluate and return this JSON (all scores 0.0 to 1.0):
{{
  "faithfulness": <float>,
  "faithfulness_reason": "<one sentence>",
  "answer_relevancy": <float>,
  "relevancy_reason": "<one sentence>",
  "context_precision": <float>,
  "precision_reason": "<one sentence>"
}}

Scoring guide:
- faithfulness: fraction of claims in ANSWER that are supported by CONTEXT (1.0 = all claims grounded)
- answer_relevancy: how well ANSWER addresses QUESTION compared to GROUND TRUTH (1.0 = complete match)
- context_precision: fraction of retrieved chunks that were actually useful for the answer (1.0 = all chunks relevant)"""

        raw = self._call_judge(prompt)

        # Strip markdown fences if the model returns ```json ... ```.
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        # Fall back to the first JSON object if the judge adds extra text.
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            raw = match.group(0)

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("Judge returned invalid JSON: %s\nRaw: %s", e, raw[:200])
            return {
                "faithfulness": 0.0, "faithfulness_reason": "parse error",
                "answer_relevancy": 0.0, "relevancy_reason": "parse error",
                "context_precision": 0.0, "precision_reason": "parse error",
            }

    def _call_judge(self, prompt: str) -> str:
        if self.judge.provider != "groq":
            raise ValueError("RAGEvaluator currently expects a Groq judge generator")

        response = self.judge.client.chat.completions.create(
            model=self.judge.model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0,
        )
        return response.choices[0].message.content or ""
