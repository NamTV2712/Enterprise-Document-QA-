# SEC Research Workspace Design Contract

## Unified conversation controls (UX-AGENT-001)

Research is the primary entry; legacy Chat routes use the same composer and
message stream. Quick/Deep buttons are explicit keyboard-accessible controls,
with Quick as the initial mode. Quick scope/comparison controls appear only in
Quick. Deep explains the goal-only boundary and shows connection/consent before
submission. Consent clears on mode, conversation or private-session changes.

The compact Agent card gives status/activity and current-revision cancellation
while active; the terminal answer and evidence lead after completion. A single
collapsed disclosure contains safe trace, optional research ledger and native
evaluation, with an advanced inspector link. Loading, disconnected, unavailable,
error and cancellation states remain source-honest. Controls wrap at narrow
widths; the existing conversation scroller and source reader keep ownership.
No raw observations, provider bodies or hidden reasoning are presented.

## Product

Enterprise Document QA is a SEC 10-K research workbench. Its primary job is to
help a researcher ask a grounded question, read the answer, inspect the exact
retrieved evidence, and continue or save the work.

## Information architecture

The implemented Workspace navigation leads with Chat, Research, Documents,
Search, and Collections. The on-device conversation Library is the Conversations
tab within Collections, not a separate primary URL. Build groups Retrieval,
Models, Pipeline, and Reranker; Evaluate groups Evaluation, Analytics, and
Datasets; Manage groups Settings and Logs. Architecture/help lives under
`/settings?panel=architecture`. Chat/Research are answer workbenches;
Documents/Search browse and inspect without implying that an answer exists.

## Visual direction

Use the repository-local `rag-ui-ux` skill and its references. The visual
identity comes from citation-to-source continuity, restrained blue interaction
accents, cool neutral surfaces, strong typography, and calm evidence states.
The supplied Light/Dark screenshots are directional references, not permission
to copy decorative cards, fake metrics, or unsupported controls.

## Layout

Use a 56px header, a 216px/56px navigation sidebar, and container-aware
responsive workbench modes. At eligible wide desktop sizes, Research, Sources,
and Document are simultaneous bounded surfaces; at narrower widths, Sources and
Document become an explicit dock or modal contextual surface. Keep answer and
document prose readable before reducing a pane, and use tabs or drawers when
the measured geometry cannot satisfy the research/source/document minimums.
The shared pane contract is recorded in `V5_WORKBENCH_CONTRACT.md`.

## Tokens

The authoritative colors, spacing, geometry, typography, state, and RAG visual
rules live in `.agents/skills/rag-ui-ux/references/design-system.md` and the
semantic CSS token layer. Component files must consume roles rather than raw
hex values.

## Design review

Every substantial change records its first decision, primary action, states,
mobile order, five self-review risks, and visual evidence. Build success is
necessary but not sufficient; the rendered app must be inspected and iterated.

## Final visual validation boundary

TEST-003 reviewed the nine tracked references: Chat, Research, Documents,
Search, Collections, Retrieval, Models, Pipeline and Evaluation. Native
Chromium/Firefox screenshots, selected-state geometry and responsive
light/dark × English/Vietnamese checks are recorded in
[`TEST_003_VISUAL_RECEIPT.md`](../TEST_003_VISUAL_RECEIPT.md). The shared shell
uses semantic surface/text/focus/status roles rather than copying every
reference pixel. Verified repairs covered contrast in both themes, non-color
selection cues, independent splitter focus/menus, and a useful phone reader
with Back recovery. At phone widths the contract uses at least 44px interactive
targets and 16px text-entry fonts; document, source, table and overlay scrolling
retain their own owners. TEST-003's reported 300 production browser passes,
648 populated responsive combinations and 162 A/AA axe analyses are bounded
evidence, not exact pixel identity or blanket WCAG certification. Native browser
zoom at 125%, 150% and 200% remains manual and unverified.

## Current skill governance

The repository-local `rag-ui-ux` skill is the product authority and routes
retrieval, evaluation, security, performance, and document-provenance questions
to their focused project skills. The fixed dimensions above describe intended
design constraints; implementation and rendered evidence remain authoritative
when they differ. A catalog-to-reader transition must be judged by its actual
user intent and resulting surface, including whether an answer or retrieved
sources exist.

## Current V5 presentation

V5-08 is the current implementation baseline. The workbench presents Research,
Sources, and Document as sibling regions when the measured geometry supports
them: 1440×900 uses 56px navigation with 624px Research, 304px Sources, two
8px splitters, and 440px Document; 1920×1080 uses 216px navigation and 944px
Research with the same contextual tracks. 1366×768 and 1280×800 use an
accessible Sources/Document context dock, 1024px and short wide tracks use a
truthful contextual surface, and tablet/phone widths use the existing drawer
or single-surface lifecycle. The reader keeps the dominant canvas and a
bounded lower Evidence/Metadata/Notes context; source identity, exactness,
stale/unavailable states, and reader requests remain owned by the existing
domain components.

The shared workbench controller owns only presentation state: layout mode,
active contextual pane, source filter, active representation/context tab,
find text, and pane preferences. App remains authoritative for route and
document identity, while Documents, Search, Retrieval Lab, and Library retain
their fetch, retrieval, cache, reader, and persistence owners. PDF remains an
optional representation: Structured and Normalized text remain the safe
fallback, while PDF is selectable only when a current backend manifest admits
an `OFFICIAL_PDF` or `DERIVED_PDF` artifact.

## Truthful route surfaces

UI-012 extends the same language to Analytics, Logs, and Settings without a
dedicated reference screenshot. Analytics uses a compact population strip,
outcome/job groups and UTC observations with a table equivalent. Logs uses
readable record cards and native detail disclosures, with independent severity
and outcome. Settings groups editable browser presentation/recovery controls
separately from read-only retention, provider, deployment and system facts.
All share the app's connection owner and explicit refresh; private-unavailable
is never an empty dashboard. Compact layouts stack cards instead of compressing
data, and phone chart interval/unit labels live outside the scaled SVG.

The route surfaces preserve the enterprise reference composition while binding
every value to an authoritative source. Research renders live SSE answers,
citations, stages, and reader handoffs; Documents renders catalog metadata,
reader coverage, and representation availability; Search reads provider-free
`POST /search` snapshots (paged by `GET /search/{search_id}`), while Retrieval
Lab renders `/retrieval/inspect` traces without generation or confidence claims;
Library renders browser-local conversations, evidence, and storage state;
Models separates configured and observed identity via `/models`; Pipeline renders the
API-007 public definition and, after explicit local connection, staged durable
job history/detail; and Evaluation renders EVAL-001 definitions, EVAL-002
public publications/analytics, and EVAL-003 frozen job controls after the same
explicit memory-only local connection. Missing fields use an explicit
unavailable state rather than a mock value. These rules apply in both themes
and at every responsive breakpoint.

## Agent operational workspace (UI-014)

Agent follows the shared shell and card tokens. Its hierarchy is connection
and execution availability, durable run history, selected frozen policy and
state, safe operational trace, research objectives/gaps/source identities,
final result and individual native metrics. Desktop uses a bounded history
column with a flexible detail column. Tablet stacks them; a selected phone run
shows a Back control and the detail instead of compressing both columns.
Long IDs wrap, the event list is keyboard scrollable, and status is expressed
in text as well as color. The existing composer remains part of the shell.
Both themes and EN/VI use the same authority and responsive rules.

## PDF representation UX

The PDF reader uses the real PDF.js canvas/text layer and a document-bound
content URL. Its header labels generated-representation pages separately from
official PDF pages; it also exposes renderer, source/revision, page-count, and
artifact identity metadata. In the current corpus, only `DERIVED_PDF` is
admitted; `OFFICIAL_PDF` remains schema/helper support without admitted
official bytes. PDF.js is dynamically loaded only after an eligible backend
manifest is available. The download action is bound to the current document
and representation type, never to a browser-supplied path or URL.

Evidence overlays are conservative: an amber rectangle appears only after the
backend returns an exact location whose chunk hash, source document, source-set
revision, document revision, artifact hash, and mapping sidecar all match the
active document. Ambiguous, stale, unavailable, failed, and unsupported states
retain the selected evidence and show the reason without painting an
approximate page highlight. Responsive layout changes preserve the selected
representation through the shared workbench controller, including the narrow
drawer transition.
