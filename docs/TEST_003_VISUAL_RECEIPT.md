# TEST-003 — Nine-reference visual receipt

## A — Plan recorded before production changes

2026-09-27; starting HEAD `e2b4d49`. Tracked/staged tree clean; the original
12 untracked paths are excluded from this task. TEST-004 is out of scope.
PNG IHDR dimensions independently checked; all nine images inspected.
All native comparisons use dark/English, deterministic existing schema-shaped
Playwright fixtures, reduced motion, real completed UI state and loaded fonts.
No provider, live backend, corpus mutation or new capability is authorized.

| Surface / authoritative PNG | Native viewport | Canonical route / selected state | Reference measurements (approximate pixels) |
| --- | --- | --- | --- |
| Collections / collections-ui-reference-dark-v1.png | 1586×992 | /collections/col-risk; typed document/evidence members, favourite, Contents | nav 210; header 61; main x224; list 750; rail x987/w584; title y86; cards h163/gap10; tabs y343 |
| Documents / documents-ui-reference-dark-v1.png | 1586×992 | /documents; AAPL:fixture selected, Overview | nav204; header56; main x221/w938; rail x1174/w404; filters y138/h150; metrics y301/h92; rows h42; preview y747 |
| Evaluation / evaluation-ui-reference-dark-v1.png | 1586×992 | /evaluation/runs/baseline-native; public publication, six native metrics; empty trends | nav204; header56; main x221; metric strip y140/h153; history y307/w997; rail x1232/w336; analytics y734 |
| Models / models-ui-reference-dark-v1.png | 1586×992 | /models; generator selected, unknown availability, real registry | nav206; header59; main x224; routing w765/h308; benchmark w568; roles y470; rows h51; gaps12 |
| Pipeline / pipeline-ui-reference-dark-v1.png | 1586×992 | /pipeline/runs/run-reference-1; explicit memory-only connection; queued with five pending steps | nav206; header59; main x223/w985; rail x1228/w347; metrics y148/h95; flow y259/h298; history y574; rows h32 |
| Chat / rag-workbench-master-reference-dark.png | 1254×856 | /chat; completed grounded answer, source 1, document open | image includes black margin; nav158; header~65; answer x171/w466; sources x659/w246; reader x931/w277; composer y747/h82; gaps8–14 |
| Research / research-ui-reference-dark-v1.png | 1586×992 | /research?mode=conversation; completed answer, source 1, document open | nav199; header55; answer x210/w603; sources x832/w322; reader x1185/w378; composer y912/h72; sources h119; gaps8–18 |
| Retrieval / retrieval-ui-reference-dark-v1.png | 1586×992 | /retrieval; hybrid trace completed, first candidate selected | nav206; header59; main x223/w958; rail x1201/w377; query y144/h177; metrics y336/h100; results y451; rows h60 |
| Search / search-ui-reference-dark-v1.png | 1586×992 | /search; submitted revenue query, snapshot results, highlights/facets | nav204; header56; main x220/w963; rail x1198/w377; query y136/h196; results y383/h126; gaps5–12; overview four metrics |

The screenshots use navy canvas/sidebar/panel/raised/selection near
#06182A/#061525/#081D32/#0A223B/#0B315B, blue primary and cyan selection,
1px borders, 6px controls/8px cards. Titles approximately 24px/700 (Chat
18–20px), panel titles16px/600, prose13–15px/400, metadata11–13px, paper
serif14–16px. Existing readability floors and contrast 4.5:1 override smaller
reference text. Selected navigation, tab underline, row outline and text labels
must accompany colour. Do not reproduce fake quota, owners, health, progress,
probabilities, filing forms/pages or trend lines.

### Comparison and gate policy

Capture all nine native baselines before any production style repair; inspect
each paired with its PNG at native dimensions. Record DOM bounding boxes,
computed font/surface/control colours and whole-page axe A/AA violations.
Structural differences are reviewed before micro-alignment. The master sets no
numeric pixel threshold: use bounded deliberate closeness, roughly ±8px shared
chrome/padding and ±10% column allocation as review flags, not automatic waiver
or invented acceptance limits. Contract-driven density/geometry deviations must
be explicit. Rasterization/subpixel/scrollbar variance is acceptable; lost panes,
clipped actions and false facts are not. A regression, B truthful difference,
C responsive adaptation, D accessibility repair, E ambiguity classify findings.

Final production Chromium and Firefox native gates cover all nine. Responsive
coverage: native,1600×1000,1440×900,1280×856,1024×768,768×900,390×844,
1440×700 plus1366×768/1920×1080; dark/light × EN/VI populated; applicable
empty/loading/error/stale states use existing focused specs and bounded probes.
Require exact zero body/root overflow; actions/details/lower content accessible,
compact cards rather than squeezed tables. Whole-page axe, keyboard focus,
dialogs, labelled states, reduced motion and phone target review supplement
images. Native zoom125/150/200 is separate: current contract requires external
manual verification if automation cannot faithfully observe native chrome zoom;
never present viewport resizing as zoom proof.

### Semantics, hierarchy and ownership gate

Entry intent: Chat/Research question→answer→citation→source→reader; Documents
catalog→selected document→reader; Search submit→snapshot hits→open/save;
Retrieval submit→trace→candidate excerpt; Collections list→typed members/tabs;
Models browse configured/runtime facts; Pipeline definition→connected queued
run; Evaluation published report→definitions/analytics. Success is the actual
selected identity and truthful evidence, not a screenshot-shaped demo. Recovery
retains safe data and distinguishes refusal, missing record, stale and empty.

Tree: App route/session/connection → shared sidebar/topbar → domain workspace →
primary list/answer plus selected source/detail → shared reader/overlay.
App owns route/document and memory-only connection; domain controllers own
request epochs, filters, revisions and selected IDs. Conversations/preferences
retain existing browser storage; Collections/jobs stay server-owned with no
fallback. Identity is document/chunk/answer-variant/collection/run ID, never
row index. Notifications clear with their owning operation; independent pane,
workspace/list, reader and overlay scroll owners remain unchanged.

Five risks: shared colour repair harming other routes/light mode; long VI labels
clipping; pane minimums hiding evidence; private fixture access being mistaken for
real auth integration; unsupported reference facts leaking into production.
Mitigate through all-nine recapture, four theme/locale combinations, small/short
viewports, explicit fixture-only disclaimer and source/test diff review.

Known investigation targets: TEST-002 dark Search white-on-cyan button2.27:1 and
BM25 muted label4.32:1; reproduce before fixing. No Reranker reference exists;
shared-style impact requires smoke only, excluded from the nine.

## B–D — Baseline captured before repairs

All nine Chromium native captures and computed-geometry/axe JSON are in ignored
`frontend/test-results/test-003/baseline/chromium/`. Each PNG inspected beside
its authoritative image. First harness run6/9; three detail route IDs corrected
to collection-detail/evaluation-run/pipeline-run, then2/3 (Collections heading
contains its favourite button), finally2/2. These were test assumptions, not
product defects. Documents' first capture caught an entrance animation; replaced
with a capture awaiting finite animation completion, not a fixed sleep.

Shared baseline: nav184 vs reference199–210 (−15 to−26), native Chat158 exact;
header56 vs55–61 (−5 to+1); primary content x208 vs220–239 (−12 to−31).
These are the established responsive shell, not lost navigation. Shared surfaces
retain navy/blue borders, paper white and selected outline/text; font normal
metadata12–13 vs11–13, page title24/700 vs24/600–700. Inter/system rasterization
and compact route icons differ (E); no decorative branding redesign warranted.

| Surface | Baseline measured composition / largest differences | Classification / decision |
| --- | --- | --- |
| Collections | list x208/w758, detail x980/w582 vs224/w750 and987/w584; cards160/160/160 vs163, gap13 vs10; detail y206 vs145; radius16 vs8 | B: header/library tabs span width, typed member filters/tabs, no unsupported share/owner,3 collections/2 actual members rather than4/12; four real detail tabs retained. Established Collections readability/selection repairs remain intact. |
| Documents | filters x208/y134/w954/h149 vs221/138/938/150; metrics y299/h100 vs301/92; detail x1178/w384 vs1174/404; row58 vs42; sparse one filing | B/D: no unsupported form/year metadata or management controls; factual summary and one excerpt preview rather than invented full paper. Selected secondary text contrast4.16:1 requires repair. |
| Evaluation | six metrics y203/h186 vsfive y140/h153; history y402/w942 vs307/w997; detail x1162/w400 vs1232/w336 | B: six native metric definitions/denominators plus five domain tabs need more space; public publications rather than demo jobs. Trends/failures live in actual tabs, no fake interpolated chart. Zero/false/unavailable/N/A remain visible. |
| Models | summary y141/h65, roles y220; registry y282/w881 and detail x1103/w459; row61 vs51 | B: no mutable routing policy or fake benchmark; actual three configured roles and selected independent runtime facts replace unsupported upper panels. Unknown availability is retained. |
| Pipeline | metrics y142/h96 vs148/95; flow y252/h324 vs259/298; history y590 vs574; rail x1210/w352 vs1228/w347 | B: five actual ingestion steps vsunsupported sixth stage; queued/pending/null progress and no timings replace successful sample. Main/rail proportion preserved. |
| Chat | nav158; answer x174/w414 vs171/w466; sources x596/w332 vs659/w246; reader x936/w318 vs931/w277; composer bottom836 vs829 | B/D/E: source controller deliberately requires300px minimum and430px research track;332 requested source width is not screenshot250. All panes simultaneous; current provenance header and accessible composer wrap take more height. No forced smaller text or pretend full filing/page is justified. |
| Research | answer x200/w638 vs210/w603; sources x846/w332 vs832/w322; reader x1186/w400 vs1185/w378; composer y862/h110 vs912/72 | B/D: safe identity/representation controls and actual two-source answer, not five source demo. Three panes remain legible; longer truthful controls move composer upward. |
| Retrieval | query y147/h277 vs144/177; metrics y597/h137 vs336/100; results y749 vs451; rail x1202/w360 vs1201/w377; rows66 vs60 | B: explicit submitted trace configuration/export/raw families and candidate-pool parameters are API-005 controls, not a removed geometry region. No invented whole-document excerpt/probability. D: primary button resting/hover contrast needs repair. |
| Search | query y147/h210 vs136/196; results y371 header then cards y499/h156+ vs383/h126; rail x1202/w360 vs1198/w377 | B/D: bound-count disclaimer/grouped filing identity add height; raw11.473 BM25 rather than fake0.892 probability. Primary hover2.27:1, BM25 label4.32:1 require repair. |

### E — Verified bounded repair plan

V01 D/P2: console primary text hardcoded white on bright blue/cyan (hover2.27),
affects Search/Retrieval/Documents/Collections and other console consumers.
Reuse existing accent-button background/text roles, no global accent palette
change; check rest/hover/keyboard-focus in both themes and recapture all nine plus
Reranker. An intermediate inverse-text experiment failed Collections4.01:1
(its existing button already used a darker background); rejected, never committed.

V02 D/P2: Search BM25 label muted on tinted pill4.32; use secondary text only
in that label. Documents selected row's secondary metadata4.16; use secondary
text only in selected console rows. All consumer tables recertified.

V03 D/P2: shared connection subtitle mixes green with surface (4.46); inherit
already-accessible state foreground. All nine headers/theme/locale checks.

V04 D/P2: Chat/Research splitter's focusable separator contains a details menu
and buttons (two nested-interactive nodes on each page); move separator semantics
and pointer/keyboard handlers onto a sibling handle inside the same geometry
wrapper. Preserve widths/storage and menu actions. Add unit regression for no
focusable descendants, arrow resize, independent menu and collapse; browser axe
and existing workbench/reader/route tests. No state redesign.
The existing V5-06 pointer/keyboard/reset/collapse browser test now targets the
semantic separator handle instead of the noninteractive geometry wrapper;
all width/storage/gesture assertions are preserved.

V05 D/P2: light subtle text #64748B on sidebar #F1F5F9 fails4.34:1;
card metadata on #F4F7FA4.42 and raised #EDF2F74.22. Same semantic role owns
sidebar group labels, card hints and chips; minimally darken the light-only
--text-subtle to #5B6B81. Dark unchanged. All nine × four combinations plus
Reranker/route/shared-shell and operational consumers require revalidation.

One light token value is changed; other changes are role-consumer corrections. Backend,
API count, persistence, capability/auth owners and provider boundaries unchanged.

### E continued — Findings from progressive responsive validation

V08 D/P2: selected Chat/Research source cards use hardcoded dark translucent
blue in light mode: #526174 on #C7CEE2 is4.02:1 for citation/excerpt/metadata.
Use the existing selected-surface role for that card, keeping selection and focus.
The selected surface also requires secondary (not muted) excerpt/state text:
dark muted #7894B2 on #0B315B is4.16. After closing the mobile inspector, the
light Chat/Research answer badge1.61 and footer citation buttons2.63 are exposed;
replace their hardcoded Tailwind foregrounds with existing success/accent roles.
Footer citation buttons receive44px mobile targets; desktop density unchanged.
The existing conversation pipeline-details button shares the same light blue
foreground2.63:1; use accent-text there too (no pipeline execution change).
V10 A/P2 source-card facts: the low-contrast page label is also fabricated by
card index (12/28/45/67/88); missing section defaults to Risk Factors. Source DTO
does not provide those page labels. Remove fabricated pages and explicitly show
section unavailable when absent; protect with SourceCard unit assertion. This is
bounded truthful rendering, not new provenance capability or a backend change.
V06 also includes Evaluation's native/computed/complete state labels: decorative
green on #F4F7FA is3.50:1; use the same existing success-text role.
V09 D: shared console buttons are36px, inputs40px/14px, select triggers40.8px.
At mobile widths only, increase these existing controls to44px and input text
to16px; preserve desktop/native geometry and action semantics.
DOM review additionally measures Collections icons24–30px, tabs37px, member
filters26px, document paging32px, Evaluation disclosures17–24px, model filters
38px and reader/source actions25–33px. Apply a mobile-only workspace/evidence
dialog control floor44px, with16px text-entry fields and composite wrapper hit
areas. Revalidate all nine and operational/shared reader consumers. Desktop
density remains unchanged; no control, request or persistence action is added.
V11 D/A: phone screenshot after the touch floor shows no useful reader canvas:
the stacked source pane plus wrapping reader controls consume the drawer height.
On phones only, show the active document alone in the existing evidence drawer;
the existing Back to inspector action restores sources. Keep reader header
actions in a wrapping row. Verify visible reader content plus source/back/reader
recovery; no new tab/control or state owner is introduced.

Validation incident: the first responsive sweep was interrupted after a separate
`bun run build` overwrote the preview bundle with developer environment settings.
Later routes reported API offline; those interrupted outcomes are UNKNOWN, not
product regressions or acceptance evidence. Do not rebuild a preview's shared
dist while it is serving. Final harness blocks every external origin (including
remote fonts) and rejects any unmocked fixture-origin request; use deterministic
system fonts. All final evidence is rerun against the controlled production
build. No live provider outcome is asserted from the invalidated sweep.

Further responsive reproduction (before repair): V06 D/P2 Evaluation native chip
uses decorative success colour #059669 on #EBF7F3,3.43:1; connected Pipeline
chip #059669/#E6F5F0,3.35:1. Reuse state-success-text on those chips only.
V07 D/P2 Pipeline's five-stage strip overflows locally at390 but has no keyboard
focus target; add tabindex/region semantics to the existing labelled strip, no
new control or step. Check keyboard access and all five cards' reachability.

Harness correction: a narrow Chat/Research inspector deliberately makes the
background main inert (C), so assert its dialog and close/recovery rather than
requiring the hidden main landmark. Finite-animation waits must ignore invisible
details/resize artifacts: diagnostics showed reduced-motion0.01ms animations on
hidden elements never resolve finished. The final capture policy finishes finite
animations (equivalent to Playwright's animations-disabled capture), waits for
loaded fonts and two animation frames; no timeout inflation or fixed sleep.
Whole-page assertions remain.

## F — Final visual, responsive and accessibility disposition

All nine are accounted for. Native dark/EN production captures were inspected
individually in Chromium and Firefox, then Chromium/reference side-by-side
comparisons reviewed at the original image dimensions. The image viewer can
downscale a combined comparison; original native images were also inspected.
This is a measured visual review, not an invented pixel-difference threshold.
The B/D/E geometry rationale above remains the final disposition, not a claim
of pixel identity. Shared navigation184 (Chat158), header56, page titles24 and
12–13px metadata remain unchanged; no shell redesign was warranted.

Final captures are local ignored artifacts under
`frontend/test-results/test-003/final/{chromium,firefox}/<surface>.png` with
matching geometry/contrast/axe JSON. Authoritative tracked PNG filenames,
dimensions, routes and selected states are in A. Baselines remain separate.

| Surface / capture stem | Final native disposition in both browsers | Verified repair / preserved truth |
| --- | --- | --- |
| Collections / collections | Reviewed; list758/detail582, cards160; B/D/E deviations recorded | Primary colour/phone targets; typed two-member detail, four tabs, revisions/delete/refusal unchanged |
| Documents / documents | Reviewed; filters954/detail384, rows58; B/D | Selected-row secondary contrast/phone targets; actual metadata and canonical reader. Supplemental 12-filing, ten-row paged catalog inspected, not a fabricated native reference count |
| Evaluation / evaluation | Reviewed; six metrics186 high, history942/detail400; B/D | Accessible native/state chips and phone disclosures; zero/false/unavailable/N/A, real tabs/trends/jobs remain distinct |
| Models / models | Reviewed; registry881/detail459, rows61; B/D/E | Shared subtle colour/phone filters; configured/loading/availability remain independent, unknown stays unknown |
| Pipeline / pipeline | Reviewed; metrics96/flow324, detail352; B/D | Connected chip contrast and keyboard-scrollable five-stage region; queued/pending/null, no sixth stage |
| Chat / chat | Reviewed; answer414/sources332/reader318; B/D/E | Independent splitter handle/menu, selected source and answer/citation contrast; fabricated page numbers removed. Phone reader visible with existing Back recovery |
| Research / research | Reviewed; answer638/sources332/reader400; B/D | Same evidence/splitter repairs, actual sources/session and responsive inspector; no invented document or page |
| Retrieval / retrieval | Reviewed; query277, metrics137, detail360; B/D | Primary contrast/phone inputs; submitted configuration, raw score families/candidate pool and export remain real |
| Search / search | Reviewed; query210, results156+, detail360; B/D | Primary and BM25 contrast/phone inputs; one submitted snapshot, grouped identity and original Unicode ranges retained |

Browser differences are minor font rasterization/weight, native numeric-input
spinners and Pipeline Recent events heading wrapping (E), not missing content or
material column drift. No Reranker tenth reference was created; UI-007 supplied
its existing functional/visual/accessibility smoke only.

Final actual dark Search computed contrast: primary white/#0874D4 =4.71:1 in
rest, hover and keyboard-focus states (reproduced baseline hover2.27).
BM25 #B8CBE4 on computed tinted background =8.25:1 (baseline4.32).
Shared connection subtitle =7.60:1 (baseline4.46). Primary focus outline remains
at least2px. Existing light primary pair is6.70:1. All nine recaptured after
the light-only subtle-token and shared primitive changes; UI-007 Reranker and
UI-012 Analytics/Logs/Settings were revalidated as affected consumers.

Responsive campaign: 9 surfaces ×4 theme/locale pairs ×2 browsers ×9 viewport
sizes =648 measured populated viewport combinations, each exact body/root
horizontal overflow0. Sizes1600×1000,1440×900,1280×856,1024×768,768×900,
390×844,1440×700,1366×768,1920×1080 supplement18 native captures.
Dark/light and EN/VI long labels passed. Existing compact cards/drawers, table
local scrolling and selected detail ownership remain coherent; short-height
lower actions are scroll-reachable. Phone visible button/summary/text-entry
targets measure at least44×44 and text-entry fonts at least16px (composite
fields use their actual wrapper hit area). Reader clipping is checked against
every scroll/clipping ancestor: at least160px useful visible canvas and the
selected mark are in view, with source→reader→Back→reader→close recovery.
Pipeline ArrowRight actually increases the focused region's scrollLeft and its
fifth stage remains reachable. Selected outlines/labels, statuses, form labels,
dialogs and keyboard focus supplement colour; reduced motion is exercised.

Whole-page axe WCAG2/2.1 A/AA:18 native +144 phone/short-height analyses =162,
zero reported violations in the final nine-reference campaign. Incomplete
native axe checks remain in ignored JSON for manual follow-up; this is not a
blanket WCAG certification. Manual screenshots found the clipped phone reader
that an earlier bounding-box-only assertion missed; the strengthened clipping
test now protects it. Native browser zoom125%,150%,200% remains EXTERNAL MANUAL /
UNVERIFIED: native application UI automation is unavailable here. No CSS zoom,
device-scale or viewport resizing is offered as native zoom evidence.

## G — Actual final validation

Commands run in `frontend/`, production fixtures only; no live backend/provider:

| Gate | Actual final result |
| --- | --- |
| `bunx tsc --noEmit` | PASS |
| `bun run test --run` |90 files /790 passed /0 failed,15.51s |
| controlled-origin `bun run build` | PASS;2074 modules;3.15s; aggregate index506.91kB, existing >500kB warning |
| `bunx playwright test e2e/test-003-visual.spec.ts --workers=2` |90 passed /0 failed,2.6m;45 per engine =9 native +36 responsive tests per engine |
| focused domain/route/shell/contracts command below |204 passed /0 failed,2.7m;102 per engine |
| `bunx playwright test e2e/v5-06-layout.spec.ts --workers=2` |6 passed /0 failed,17.9s;3 per engine |
| Working and staged `git diff --check` | PASS; line-ending advisories are not failures |

The204-test command ran existing `ui-003-conversation-modes`,
`ui-004-source-document`, `ui-005-documents`, `ui-006-search`,
`ui-007-retrieval`, `ui-008-collections`, `ui-009-registries`,
`ui-010-pipeline`, `ui-011-evaluation`, `ui-012-operations`, `ui-routing`,
`v5-02-shell`, and `test-002-contracts` specs together, workers2. It covers
applicable empty/loading/error/stale/race recovery, original Search Unicode,
snapshot paging, Collections conflict/refusal/delete, reader identity,
Pipeline SSE/job states, Evaluation budget/analytics and operational consumers.
The6-test layout suite preserves pointer live-width/commit/storage, keyboard,
Home/End/collapse, double-click/reset and responsive geometry assertions.
Total final production browser gates300 passed,150 Chromium/150 Firefox.
These scoped regressions do not begin or certify TEST-004 integration.

Progressive evidence, not added to final totals: new separator regression first
failed nested-interactive semantics, then11 focused files/78 passed; source-fact
regression exposed the General Document fallback, then4 affected files/28 passed.
Focused phone Documents/Retrieval/Search24, all-nine dark phone9 and
Chat/Research16 passed before the final all-nine rerun. Completed pre-final
contrast failures were reproduced and repaired. Interrupted preview/hidden-
animation/reader-investigation sweeps are UNKNOWN and excluded from acceptance;
an earlier90-pass sweep was superseded after manual reader inspection.

Backend is untouched:1384 passed /188 warnings /83 routes are the historical
TEST-002 baseline, NOT rerun or newly certified here. Frontend baseline89/788
becomes90/790 through two bounded regression tests, not relaxed assertions.
No package/dependency/DTO/API/auth/request identity/persistence/provider changes.

## H — Closure and scope audit

TEST-003-A through H COMPLETE. Nine/reference state/viewport mapping, baseline
before repairs, final per-browser review, measured deviations and final gates
are recorded above. Implementation and textual closure are separate selective
commits. Implementation: `acd9487` — `fix(ui): repair verified visual accessibility
and evidence rendering`; closure documentation is committed separately.

Only task-owned source/tests and four textual records enter Git. Generated PNGs,
JSON geometry/axe receipts, comparisons, traces/reports and dist remain ignored;
no secret, runtime DB, canonical data, model/cache artifact or debug dump is
staged. Original12 unrelated untracked paths are preserved unchanged. No file
was deleted. Remaining limits: external native zoom, existing bundle warning,
historical backend warnings and staged real Collections/model-test bearer
integration (fixture success is not integration proof). No deterministic
regression remains in the final gates; no security/provider/evaluation promotion
or mathematically exact screenshot parity is claimed.

Actual dependency graph: `UI_REBUILD_MASTER_PLAN.md` TEST-004 depends on TEST-002
and TEST-003; UI-013 follows TEST-004. Exact Next Action = TEST-004 — Full product
validation. STOP: TEST-004 has not been started.
