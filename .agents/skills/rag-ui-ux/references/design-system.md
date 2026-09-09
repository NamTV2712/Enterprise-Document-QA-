# SEC Research Workspace Design System

## Product character

Calm, precise, evidence-first research workbench. The distinctive element is
the visible connection between an answer citation and the source excerpt it
opens. The product should feel like a focused financial research tool with a
developer inspection layer, not a generic AI dashboard.

## Layout contract

- Global header: 56px; context, search/commands, connection, settings.
- Primary navigation: 216px expanded, 56px collapsed; Chat, Documents,
  Search, Library. Tools is secondary and collapsed by default.
- Chat desktop: answer first; Sources/Reader are an inspector, not equal
  dashboard columns. Use 480px answer, 240px source, 300px reader minimums
  only when the available width supports them.
- Medium widths use Sources/Reader tabs or a drawer. Mobile uses one primary
  surface and a source/reader sheet. No accidental page-level horizontal scroll.
- Composer stays with Chat. Documents, Search, Library, and Tools own their
  own content width.

## Palette

| Role | Light | Dark |
|---|---|---|
| Canvas | `#F6F8FB` | `#08111E` |
| Surface | `#FFFFFF` | `#0D1828` |
| Nested surface | `#F4F7FA` | `#111F32` |
| Primary text | `#172033` | `#EDF3FB` |
| Secondary text | `#526174` | `#A8B6C9` |
| Primary action | `#2563EB` | `#3B82F6` |
| Retrieval accent | `#0891B2` | `#22D3EE` |
| Embedding accent | `#0D9488` | `#2DD4BF` |
| Reranking accent | `#7C3AED` | `#A78BFA` |
| Success | `#059669` | `#34D399` |
| Warning | `#D97706` | `#FBBF24` |
| Danger | `#DC2626` | `#F87171` |

Use accents on icons, selected states, links, small indicators, and progress.
Neutral surfaces and typography carry most of the interface. Validate actual
foreground/background pairs in the rendered UI.

## Type and geometry

- Inter/system sans for UI and answers; monospace only for IDs, code, and
  tabular diagnostics.
- 14px UI, 15–16px answer/reader, 12–13px metadata, 20–24px page headings.
- Line-height 1.5–1.7; keep answer lines around 60–75 characters on desktop.
- Spacing scale 4/8/12/16/24px; 6–10px radius for controls and panels.
- 1px borders and restrained shadow; reserve shadow for overlays.
- Minimum touch target 44px; mobile input text 16px.

## Hierarchy

Primary action > secondary action > utility action. Human labels are primary;
document IDs, URLs, scores, and raw technical status are secondary. Selected
state uses at least two signals, such as border + surface or icon + label.

## RAG visual language

- User question: quiet context block, not a chat-app bubble wall.
- Answer: readable document block with inline citations.
- Source: document identity, filing date, section, excerpt, retrieval score.
- Reader: one selected excerpt with honest preview/full-content boundaries.
- Pipeline: compact stage/timing list using semantic small accents, never neon
  circles or a decorative graph.
- Evidence: say “N sources retrieved” and explain limitations; do not display
  made-up confidence percentages.
