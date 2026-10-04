# FilingScope Documentation

Start with the [product overview, Live Demo and setup](../README.md).
The original repository is Enterprise Document QA; historical names and release
SHAs remain in engineering evidence.

## Start here

- [RAG Quality Benchmark](RAG_QUALITY_BENCHMARK.md): all 30 historical cases,
  native metric denominators, public frozen inputs and safe offline reproduction.
- [Setup and Operations](SETUP.md): current installation, index provenance,
  local Deep access and independent backend/frontend deployment.
- [Demo Guide](DEMO_SCRIPT.md) and [Recording Cheat Sheet](DEMO_RECORDING_CHEATSHEET.md):
  the published 2:28 silent tour and optional extended recording plan.
- [Portfolio shipping receipt](PORTFOLIO_SHIP_001_RECEIPT.md): preparation,
  actual video review, publication and preservation evidence.

## Portfolio

- [Case Study](PORTFOLIO_CASE_STUDY.md): problem, implementation and tradeoffs.
- [CV / Portfolio Copy](PORTFOLIO_BULLETS.md): evidence-backed application language.
- [Interview Guide](INTERVIEW_GUIDE.md): retrieval, authority, execution and testing.

## Architecture

- [Full architecture and contracts](../ARCHITECTURE.md).
- [Full pipeline guide](architecture/FULL_PIPELINE.md): technologies, commands,
  corpus lineage, Quick/Deep execution, deployment modes and diagram verification.
- New interactive views: [Full pipeline](architecture/full-pipeline.html),
  [SEC corpus preparation](architecture/corpus-pipeline.html),
  [Deployment and private access](architecture/deployment.html).
- [Earlier RAG system image](architecture/sec-research-workspace.visual-check.2048x1320.light.png):
  existing validated light system view; [visual-check evidence](architecture/sec-research-workspace.visual-check.json).
- Interactive HTML: [System Architecture](architecture/sec-research-workspace.html),
  [Query Data Flow](architecture/sec-research-query.html),
  [Research Workflow](architecture/sec-research-workflow.html).
- [Frontend contract](frontend/FRONTEND_CONTRACT.md), [design](frontend/DESIGN.md),
  [Agent UX evidence](UX_AGENT_001_FINAL_RECEIPT.md).

Download/open standalone HTML locally; GitHub file views do not execute it.
Existing detailed RAG diagrams and their authored sources remain preserved. The
earlier system image covers the RAG path; the new pipeline includes durable Agent
ownership and verified corpus preparation. The contracts remain in Full Architecture.

Historical SHOWCASE-002 presentation evidence remains available: [simplified SVG](assets/sec-research-copilot-architecture.svg),
[HTML](architecture/sec-research-copilot-showcase.html),
[source](architecture/sec-research-copilot-showcase.architecture.json) and
[receipt](SHOWCASE_002_RECEIPT.md). These retain their original names and are
secondary to the existing system visualization.

## Engineering evidence

- [Frozen final release receipt](IMPROVEMENT_FINAL_RECEIPT.md): exact code SHA,
  test counts, warnings, skips and CI provenance.
- [DB-SCALE receipt](DB_SCALE_001_FINAL_RECEIPT.md),
  [worker wake receipt](WORKER_002_FINAL_RECEIPT.md),
  [capacity receipt](CAPACITY_001_FINAL_RECEIPT.md): workload-specific measurements.
- [Showcase quality receipt](SHOWCASE_002_RECEIPT.md): diagram and public docs audit.
- [Project journal](../PROJECT_STATE.md): milestones, experiments and caveats.

These are controlled development results, not production service guarantees.
Other protocols/receipts remain in this directory for deeper inspection.

## Setup and developer tooling

- [Current local setup](SETUP.md),
  [frontend setup](../frontend/README.md), [local release runbook](LOCAL_RELEASE_RUNBOOK.md).
- [Engineering reference](ENGINEERING_REFERENCE.md): relocated setup detail,
  API tables, benchmark history and past proposals from the long README.
- [Security policy](../SECURITY.md), [MIT license](../LICENSE).
- [Agent operating guide](../AGENTS.md), [skill provenance](../.agents/skills/SOURCES.md).

Receipts, historical diagnostic evidence and `.agents/` tooling are retained;
they are not prerequisites for understanding the public overview.
