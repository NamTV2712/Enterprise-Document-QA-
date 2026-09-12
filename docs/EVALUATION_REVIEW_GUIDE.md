# Evaluation review guide

Evaluation is a read-only review surface. It displays published reports from the backend and a clearly labelled recorded fixture; it does not start provider execution, edit datasets, or publish results.

## Review flow

1. Start in `Live published` and select a report when one is available.
2. If the live list is empty, choose `Recorded demo` or `View recorded example`. Recorded data is illustrative and is never the official benchmark.
3. Open cases to inspect the question, answer, reported evidence, scores, gates, and case status.
4. Compare only runs whose dataset, corpus, model, profile, and rubric provenance bindings match. Incompatible runs remain uncomparable.
5. Export the selected report as JSON or CSV when a review artifact is needed.

## Publishing

Use the existing `scripts/publish_evaluation_report.py` workflow and validate the complete report and provenance before publishing. Do not treat quota-skipped, checkpoint-mixed, or incomplete records as the official benchmark. The official benchmark policy remains the clean priority `<=2` N=30 evaluation unless `PROJECT_STATE.md` records a superseding clean run.

## Status interpretation

`OK`, `ERROR`, and `MISSING` are case statuses, not a universal quality verdict. Published evidence without resolvable live source identity stays report evidence and does not receive a fabricated document link.
