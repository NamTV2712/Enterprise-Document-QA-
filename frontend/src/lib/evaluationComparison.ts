import { EvaluationRun } from "../types";

export interface BootstrapDelta {
  metric: string;
  baselineMean: number;
  candidateMean: number;
  delta: number;
  lower95: number;
  upper95: number;
  sampleCount: number;
  resamples: number;
  seed: number;
}
export interface EvaluationComparison {
  compatible: boolean;
  reason: string | null;
  pairedCaseCount: number;
  metrics: BootstrapDelta[];
}

function mean(values: number[]): number {
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
}

function provenanceKey(run: EvaluationRun): string {
  return JSON.stringify(Object.entries(run.provenance).sort(([a], [b]) => a.localeCompare(b)));
}

/** Compare only paired reports with identical evaluation bindings. */
export function compareEvaluationRuns(
  baseline: EvaluationRun,
  candidate: EvaluationRun,
  resamples = 2_000,
  seed = 42,
): EvaluationComparison {
  if (provenanceKey(baseline) !== provenanceKey(candidate)) {
    return { compatible: false, reason: "Runs use different dataset, corpus, model, profile, or rubric bindings.", pairedCaseCount: 0, metrics: [] };
  }
  const baselineById = new Map(baseline.cases.map((item) => [item.case_id, item]));
  const pairs = candidate.cases.flatMap((item) => {
    const base = baselineById.get(item.case_id);
    return base?.status === "OK" && item.status === "OK" ? [{ base, item }] : [];
  });
  if (!pairs.length) {
    return { compatible: false, reason: "There are no valid paired cases to compare.", pairedCaseCount: 0, metrics: [] };
  }
  const metricNames = Array.from(new Set(pairs.flatMap(({ base, item }) => [...Object.keys(base.scores), ...Object.keys(item.scores)])))
    .filter((name) => pairs.every(({ base, item }) => typeof base.scores[name] === "number" && typeof item.scores[name] === "number"));
  const metrics = metricNames.map((metric) => {
    const deltas = pairs.map(({ base, item }) => item.scores[metric] - base.scores[metric]);
    const random = { value: seed >>> 0 };
    const samples: number[] = [];
    for (let iteration = 0; iteration < resamples; iteration += 1) {
      const selected: number[] = [];
      for (let index = 0; index < deltas.length; index += 1) {
        random.value = (1664525 * random.value + 1013904223) >>> 0;
        selected.push(deltas[random.value % deltas.length]);
      }
      samples.push(mean(selected));
    }
    samples.sort((a, b) => a - b);
    return {
      metric,
      baselineMean: mean(pairs.map(({ base }) => base.scores[metric])),
      candidateMean: mean(pairs.map(({ item }) => item.scores[metric])),
      delta: mean(deltas),
      lower95: samples[Math.floor(samples.length * 0.025)] ?? 0,
      upper95: samples[Math.ceil(samples.length * 0.975) - 1] ?? 0,
      sampleCount: deltas.length,
      resamples,
      seed,
    } satisfies BootstrapDelta;
  });
  return { compatible: true, reason: null, pairedCaseCount: pairs.length, metrics };
}
