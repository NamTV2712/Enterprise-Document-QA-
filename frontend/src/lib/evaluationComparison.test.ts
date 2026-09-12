import { describe, expect, test } from "vitest";
import { EvaluationRun } from "../types";
import { compareEvaluationRuns } from "./evaluationComparison";

function run(id: string, value: number, corpus = "corpus-1"): EvaluationRun {
  return {
    run_id: id,
    title: id,
    status: "candidate",
    created_at: "2026-01-01T00:00:00Z",
    provenance: { dataset: "dataset-1", corpus, model: "model-1", profile: "profile-1", rubric: "rubric-1" },
    aggregate: {},
    notes: [],
    cases: [
      { case_id: "case-1", question: "Q1", language: "en", status: "OK", scores: { AR: value }, gates: {}, reasons: [], evidence: [] },
      { case_id: "case-2", question: "Q2", language: "vi", status: "OK", scores: { AR: value - 0.1 }, gates: {}, reasons: [], evidence: [] },
    ],
  };
}

describe("evaluation comparison", () => {
  test("computes deterministic paired bootstrap deltas", () => {
    const result = compareEvaluationRuns(run("base", 0.8), run("candidate", 0.9), 100, 42);
    expect(result.compatible).toBe(true);
    expect(result.pairedCaseCount).toBe(2);
    expect(result.metrics[0].metric).toBe("AR");
    expect(result.metrics[0].delta).toBeCloseTo(0.1, 12);
    expect(result.metrics[0]).toMatchObject({ resamples: 100, seed: 42 });
  });

  test("rejects incompatible provenance instead of producing a misleading delta", () => {
    const result = compareEvaluationRuns(run("base", 0.8), run("candidate", 0.9, "other-corpus"));
    expect(result.compatible).toBe(false);
    expect(result.metrics).toEqual([]);
  });
});
