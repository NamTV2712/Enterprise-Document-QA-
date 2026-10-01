# SEC RAG skill source registry

Review date: 2026-09-12. Core skills are project-authored and have no runtime
dependency on remote content. External sources below are reference-only; no
third-party scripts, installers, hooks, or executable code were copied or run.
“Maintained” means only the dated repository metadata observed during PASS 1.

| ID | Local consumer | Upstream artifact | Reviewed pin | License evidence | Trust / executable review | Disposition |
|---|---|---|---|---|---|---|
| QDRANT-QUALITY | `rag-retrieval-quality/references/qdrant-quality.md` | https://github.com/qdrant/skills — `skills/qdrant-search-quality/diagnosis/SKILL.md`; `skills/qdrant-search-quality/search-strategies/hybrid-search/SKILL.md`; search-speed and memory-optimization skills | `a43c06af70fecae383f36f0f94c31f9641609b6c` | Apache-2.0 license inspected | Vendor guidance; advisor/live-fetch and operational scope excluded; no scripts run | REFERENCE ONLY |
| NVIDIA-RAG | `rag-evaluation/references/metrics-and-ground-truth.md` | https://github.com/NVIDIA/skills — `skills/rag-eval/SKILL.md`; result-analysis and evaluate-rag-cli references | `9ca28078c7e9acef40347c7bb15449a281f3fb8d` | Skill frontmatter Apache-2.0; repo distinguishes CC-BY-4.0 docs and Apache-2.0 code | Blueprint endpoints, credentials, uv/pip and scripts incompatible; no execution | REFERENCE ONLY |
| NVIDIA-PERF | `rag-performance/references/measurement-and-attribution.md` | https://github.com/NVIDIA/skills — `skills/rag-perf/SKILL.md` | `9ca28078c7e9acef40347c7bb15449a281f3fb8d` | Same repository license split | aiperf/plugin/scripts excluded; no execution | REFERENCE ONLY |
| VERCEL-REACT | `rag-ui-ux/references/frontend-architecture.md` | https://github.com/vercel-labs/agent-skills — `skills/react-best-practices/SKILL.md` | `063bee94c3f4df8453406c830b0a7df0f2860278` | MIT declared for skill; repository-wide status incomplete | Principle reference only; no Next/RSC assumptions | REFERENCE ONLY |
| VERCEL-WEB | `rag-ui-ux/references/visual-qa.md` | https://github.com/vercel-labs/web-interface-guidelines — `command.md` | `e3d624baaf29dc1fc645aff3e38f03e564d2d6b1` | MIT license inspected | Mutable-fetch command excluded; no scripts run | REFERENCE ONLY |
| ANTHROPIC-FRONTEND | `rag-ui-ux/references/design-system.md` | https://github.com/anthropics/skills — `skills/frontend-design/SKILL.md` | `34040c9c568585f6929bedeaad110ad08f079624` | Apache-2.0 text inspected | Advisory composition only; no asset/template copy | REFERENCE ONLY |
| CODEX-UIUX | `rag-ui-ux/SKILL.md`, `evals/skill-cases.md` | https://github.com/atuizz/codex-ui-ux-skill — `ui-ux/SKILL.md`, `docs/EVALUATION.md` | `3c311f71f5aab40af3a10dadb2306578783979d0` | MIT license inspected | Community methodology; generator scripts excluded | REFERENCE ONLY |
| PRO-MAX | `rag-ui-ux/references/visual-qa.md` | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill — `.claude/skills/ui-ux-pro-max/SKILL.md` | `7f69fed6a2717900085f1bc3b263721f8ba025e2` | MIT license inspected | Design-system generator/search excluded | REFERENCE ONLY |
| COMMUNITY-FE | `rag-ui-ux/references/frontend-architecture.md` | https://github.com/winklerbremen/codex-skills — `skills/frontend-skill/SKILL.md` | `af28efd6d134888d7d7fe30e791285e8a0eefd6d` | License not established | Community source; no code copied | REFERENCE ONLY |
| OPENAI-CATALOG | `ROUTING.md` and discovery notes | https://github.com/openai/skills | `49f948faa9258a0c61caceaf225e179651397431` | Per-artifact review required | Catalog evidence only; no general UI skill adopted | REFERENCE ONLY |
| CISCO-SCANNER | `rag-security/references/threat-model-and-review.md` | https://github.com/cisco-ai-defense/skill-scanner | `431cb58a5ac333bc0bb9aaa23f7c30ac628f59f8` | Apache-2.0 inspected | Scanner is best-effort and executable; not installed or run | REFERENCE ONLY |
| OWASP-RAG | `rag-security/references/threat-model-and-review.md` | https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html | Repo observed `be333201dc8bbf9380327dd755c1deff1525f9b3`; page binding unverified | CC-BY-SA-4.0 metadata; exact page pin unverified | Published guidance only; no text copied wholesale | REFERENCE ONLY — UNPINNED |
| RAGAS | `rag-evaluation/references/metrics-and-ground-truth.md` | https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ | Repo observed `298b68274234c060deacab3cf5fb52aa3a20e885`; page binding unverified | Apache-2.0 repository metadata | Methodology only; no framework install | REFERENCE ONLY — UNPINNED |
| REACT-OFFICIAL | `rag-ui-ux/references/frontend-architecture.md` | https://react.dev/learn/you-might-not-need-an-effect | Documentation URL; no executable pin | Official documentation | State/effect principle only | REFERENCE ONLY |
| WCAG22 | `rag-ui-ux/references/visual-qa.md` | https://www.w3.org/TR/WCAG22/ | Current recommendation URL; no vendored copy | W3C publication terms | Normative reference only | REFERENCE ONLY |
| OPENAI-SKILLS-DOCS | `ROUTING.md` | https://learn.chatgpt.com/docs/build-skills | Current documentation URL | Official documentation | Discovery contract only | REFERENCE ONLY |

## Local baseline records

The preserved UI baseline before PASS 2 was:

```text
rag-ui-ux/SKILL.md                       a82a7a6c088b9d0d60200941a38343b08717927586e959e6c3b5d7f2585f3a12
rag-ui-ux/references/design-system.md    4ba18ce050b341a67b5d14bc4a9caae92736a7fb466556f89155607bfc2a38d2
rag-ui-ux/references/state-matrix.md     536a998ba1986991814f0956b0fa2e75c688d37c69ee0fdc9d38bc28d01f3132
rag-ui-ux/references/visual-qa.md        7413b6e9885b66693176d2c45dd820a11c0474ca3b66305923b51f5235592d8c
```

PASS 2 adaptations are original project-specific text. Version refresh is an
explicit maintenance task; skills never fetch mutable `main`, `HEAD`, or live
advisor content at activation time.
