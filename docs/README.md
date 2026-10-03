# SEC Research Copilot Documentation

Start with the [product overview, Live Demo and setup](../README.md).
The original repository is Enterprise Document QA; historical names and release
SHAs remain in engineering evidence.

## Portfolio

- [Case Study](PORTFOLIO_CASE_STUDY.md): problem, implementation and tradeoffs.
- [Demo Guide](DEMO_SCRIPT.md): actual 5–7 minute recording plan, fixture boundaries.
- [CV / Portfolio Copy](PORTFOLIO_BULLETS.md): evidence-backed application language.
- [Interview Guide](INTERVIEW_GUIDE.md): retrieval, authority, execution and testing.

## Architecture

- [Full architecture and contracts](../ARCHITECTURE.md).
- [Hero SVG](assets/sec-research-copilot-architecture.svg),
  [showcase HTML](architecture/sec-research-copilot-showcase.html),
  [reproducible source](architecture/sec-research-copilot-showcase.architecture.json).
- Detailed interactive HTML: [System Architecture](architecture/sec-research-workspace.html),
  [Query Data Flow](architecture/sec-research-query.html),
  [Research Workflow](architecture/sec-research-workflow.html).
- [Frontend contract](frontend/FRONTEND_CONTRACT.md), [design](frontend/DESIGN.md),
  [Agent UX evidence](UX_AGENT_001_FINAL_RECEIPT.md).

Download/open standalone HTML locally; GitHub file views do not execute it.
Existing detailed RAG diagrams and their authored sources remain preserved.

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

- [Current local setup](../README.md#local-setup),
  [frontend setup](../frontend/README.md), [local release runbook](LOCAL_RELEASE_RUNBOOK.md).
- [Engineering reference](ENGINEERING_REFERENCE.md): relocated setup detail,
  API tables, benchmark history and past proposals from the long README.
- [Security policy](../SECURITY.md), [MIT license](../LICENSE).
- [Agent operating guide](../AGENTS.md), [skill provenance](../.agents/skills/SOURCES.md).

Receipts, historical diagnostic evidence and `.agents/` tooling are retained;
they are not prerequisites for understanding the public overview.
