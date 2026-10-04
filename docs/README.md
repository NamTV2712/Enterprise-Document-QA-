# FilingScope Documentation

Start with the [product overview and published demo](../README.md).

## Setup and product contracts

- [Setup and Operations](SETUP.md): installation, corpus/index preparation,
  local Deep access and independent backend/frontend deployment.
- [Frontend setup](../frontend/README.md) and
  [local release runbook](LOCAL_RELEASE_RUNBOOK.md).
- [Architecture and contracts](../ARCHITECTURE.md),
  [frontend contract](frontend/FRONTEND_CONTRACT.md) and [design](frontend/DESIGN.md).
- [Security policy](../SECURITY.md), [MIT license](../LICENSE) and
  [diagram viewer notices](licenses/DIAGRAM_NOTICES.md).

## Pipeline and demo

- [Full pipeline guide](architecture/FULL_PIPELINE.md): technologies, models,
  commands, corpus lineage, Quick/Deep execution and deployment modes.
- Interactive diagrams: [Full pipeline](architecture/full-pipeline.html),
  [SEC corpus preparation](architecture/corpus-pipeline.html),
  [Hybrid Search](architecture/hybrid-search.html) and
  [deployment/access](architecture/deployment.html).
- [Demo Guide](DEMO_SCRIPT.md): published 2:28 silent tour and repeatable
  provider-free fixture instructions.
- [Case Study](PORTFOLIO_CASE_STUDY.md) and [Interview Guide](INTERVIEW_GUIDE.md):
  implementation decisions, measured tradeoffs and limitations.

Download/open standalone diagram HTML locally; GitHub file views do not execute it.

## Reproducibility and engineering evidence

- [RAG Quality Benchmark](RAG_QUALITY_BENCHMARK.md): frozen 30-case inputs,
  native metric denominators, provenance and safe offline reproduction.
- [Frozen release receipt](IMPROVEMENT_FINAL_RECEIPT.md): exact code SHA,
  test counts, warnings, skips and CI provenance.
- [DB-SCALE](DB_SCALE_001_FINAL_RECEIPT.md),
  [worker wake](WORKER_002_FINAL_RECEIPT.md) and
  [capacity](CAPACITY_001_FINAL_RECEIPT.md): workload-specific measurements.
- [Engineering reference](ENGINEERING_REFERENCE.md): technical detail and
  historical experiments. Historical links may point to the corresponding
  earlier Git revision rather than the current file tree.

Protocols and final receipts supporting reproducibility remain available.
Controlled development results do not establish production service guarantees.
