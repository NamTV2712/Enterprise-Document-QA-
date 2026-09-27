# TEST-002 — Cross-layer contract receipt

2026-09-27. COMPLETE for the implemented native-only contract surfaces.
Start: `7d178f2`, clean tracked/staged tree plus 12 unrelated untracked paths.
No TEST-003 campaign, optional Ragas integration, provider execution, codegen,
dependency change, new product capability or canonical-data regeneration.

## Strategy and contract matrix

Small test-only catalogs bind independent owners, rather than supplying a new
runtime schema. Python inspects live routes, dependency trees, selected OpenAPI
references and actual Pydantic/dataclass validation. TypeScript checks actual
compiler-resolved unions, captures real wrapper requests and renders selected
edge semantics. Existing domain/API/component suites remain complementary
authorities; passing fixture tests alone does not certify every response field.

| Surface | Authority → backend → frontend | Evidence and result |
| --- | --- | --- |
| A Access | API-001 dependencies/settings → protected routes → memory session/private transports | PASS: public/local/execution classification; bearer/anonymous reads; 401/403/public-mode 404; Host/Origin/loopback and forwarding spoof rejection; CORS is not authorization; public mode never opens private DB |
| B Documents/Search/Retrieval | Catalog/discovery/trace owners → DTOs → api/types/searchModel/reader handoffs | PASS: encoded document/chunk/snapshot identity; bounded paging reuse; unknown 404 vs expired 410; original-text code-point ranges; trace version/stage/null timing and raw score families, not confidence |
| C Collections | DATA-003 repository/domain → collection routers → api/types/collectionModel/dialog | PASS: four member kinds; body PATCH vs query DELETE revisions; stale 409; tombstone 410/no resurrection; notes/member/export semantics; list capability 404 differs from record 404 |
| D Models | Registry configured/observed owners → registry DTOs → ModelsConsole/types | PASS: roles, configured/runtime identity/revision, credentials-presence, load and availability remain independent; unknown is not offline; public registry reads do not execute a provider |
| E Datasets | Corpus manifest/built-in dataset → registry DTOs → DatasetsWorkspace/types | PASS: two dataset IDs, corpus/evaluation discrimination, coverage/provenance missing/invalid/mismatch states; unavailable count null is not measured zero |
| F Pipeline | DATA-004 + API-007 staging → definition/run/event DTOs → pipelineApi/types | PASS: five ordered stages, queued staging, canonical run/revision, current If-Match cancellation, stale 409/missing 428, cancelling/interrupted, finite numeric SSE resume; no serving promotion |
| G Native metrics | EVAL-001 native protocol → metric/case DTOs → evaluationTypes/NativeMetrics | PASS: native-evaluation/v1/six metric IDs; computed/unavailable/not_applicable; 0.0 and false retained; no invented denominator or score |
| H Evaluation analytics | EVAL-002 analysis/publication → compare/trends/failures DTOs → evaluationApi/components | PASS: backend-owned candidate_minus_baseline, compatibility/null delta/counts/coverage/groups/four failure categories and safe public projections; frontend does not recompute deltas |
| I Evaluation jobs | Frozen plan + durable SQLite coordinator → EVAL-003 routes → memory-gated evaluationApi | PASS: persisted IDs/revisions/two zero-based steps/frozen plan; provider_attempt_slot; budget_exhausted, cancellation/recovery/interruption; metric 0/false survive storage→HTTP; private text projected away before frontend state |
| J Telemetry/Logs | DATA-005 terminal facts → telemetry DTOs → operationalApi/Analytics/Logs | PASS: three ranges/two intervals/five metrics; persisted severity differs from outcome; null vs measured-zero duration; false metadata; exact API order and opaque cursor without client interpretation |
| K Settings/transfer | Configuration/system/registries + existing transfer owners → bounded APIs → Settings/session/transfer client | PASS: supported read-only facts/actions only; redaction; caller-memory bearer; actual preview/import/export paths/bodies; existing shared Python/TS digest fixtures and one-authoritative-writer/failure semantics |

Named route coverage is 53 method/path/access pairs over all 12 completed API
surface prefixes. Selected structural checks cover 26 response models/OpenAPI
references and 11 body models, plus revision/query/resume/idempotency headers.
There are still 83 registered unique API method/path pairs, not 53 total routes.
No full generated OpenAPI snapshot is committed.

The real-client request suite covers 52 operations: 49 examples validated against
live backend body/query/header/path parameters, plus three transfer operations
using the existing canonical backup fixture. GET /documents/{document_id} is
catalogued but has no current direct frontend wrapper. Transport assertions
include exact method/path encoding/query/body, public/private bearer behavior,
AbortSignal where supported, quoted If-Match, query/body revisions and no hidden
retry. Transfer has no AbortSignal parameter; none was invented.

31 independently represented literal unions are checked for exact values and
absence of string widening. Intentionally open semantic strings are not broadly
refactored. The seven shared responses preserve unknown, unavailable, null,
0/0.0, false, valid empty strings and empty arrays. Six shared snippets include
ASCII, casefold expansion, astral characters and empty text; a separate backend
test covers expansion before a truncated window.

## Reproduced defects and bounded repairs

1. CL-01 (P3, Search contract): casefold expands `ß`, but backend ranges used
   folded positions. Frontend sliced Python code-point offsets as UTF-16.
   Before repair: two Python and two TS shared regressions failed. Map folded
   matches back to original positions and slice frontend text by code point.
   Original text, identity, bounds, ranking and provider behavior are preserved.
   Regression owners: shared snippets, truncated-window test and browser marks.
2. CL-02 (P2, Collections refusal): the evidence-save dialog interpreted list
   404 as a missing individual collection and retained creation controls. New
   component test failed before repair. Reuse the existing list-unavailable
   mapping only in its list catch. Record/mutation 404 semantics and API-001
   access remain unchanged. Unit and two-browser handoff checks now pass.
3. CL-03 (test-fixture drift): evaluationJob supplied durable step ordinals 1/2,
   while actual stored/HTTP ordinals are 0/1. New frontend test failed 1/12;
   real SQLite→HTTP checks established authority. Correct only the synthetic
   fixture. No durable storage, state machine or presentation behavior changed.

Order: establish catalog/schema/transport evidence, reproduce and repair CL-01,
then isolate CL-02's surface-specific error mapping, correct CL-03's fixture,
then run focused and full gates. No speculative architecture repair was needed.
The RAG UI skill constrained repairs to original-text semantics and truthful
availability states; existing state/scroll/layout ownership was preserved.

Implementation commits:

- `7d1c937` — test: verify cross-layer contracts and repair Unicode snippet offsets
- `59c56f2` — fix(ui): distinguish unavailable Collections list in evidence save dialog

## Tests actually run

| Gate | Result |
| --- | --- |
| Shared Python plus discovery regression | 174 passed, one warning |
| Expanded selected backend contract suites | 351 passed, one warning, 12.10s |
| Focused frontend transports/shared fixtures/session/backup/error semantics | 230 passed, 12 files |
| Affected Models/Datasets/Search/Collections/Retrieval/Reranker components | 76 passed, six files |
| Collection dialog/model/workspace focused regression | 51 passed, three files |
| TypeScript (`bun run lint`, which is tsc --noEmit) | PASS |
| Full Vitest (`bun run test`) | 89 files / 788 passed, 13.69s |
| Full backend (`.venv/Scripts/python.exe -m pytest tests -q --tb=short`) | 1384 passed / 188 warnings / zero failures, 95.47s |
| Production (`bun run build`) | PASS; existing aggregate chunk >500 kB warning |
| Focused production browser (`bunx playwright test e2e/test-002-contracts.spec.ts --workers=1 --retries=0`) | 4 passed: two Chromium + two Firefox, 13.4s |
| Working/staged diff checks | PASS |

The selected backend command covers test_cross_layer_contracts,
test_api_router_contracts, test_collections_api, test_collections_transfer,
test_pipeline_staging, test_evaluation_jobs, test_terminal_telemetry_api,
test_workspace_transfer_canonical, test_workspace_transfer_api,
test_workspace_access, test_native_evaluation_analytics_api,
test_native_metric_api, test_retrieval_inspect_metadata and test_discovery_search.
All use hermetic doubles or temporary workspaces; no live provider is needed.
The full suite additionally covers migrations/atomicity/recovery/privacy and
the neighboring route/component contracts. Historical benchmark receipts were
not rerun or superseded by these engineering tests.

Baseline → final: backend 1234→1384, warnings 188→188, routes 83→83;
frontend 85 files/688 tests→89 files/788 tests. Additions account for the counts:
148 new shared Python cases + two expanded parametrized edge cases; 100 new
frontend tests in four files. The three transfer canonicalization fixtures are
reused, not replaced by a new algorithm. Native report/frozen-plan digests have
no independent TS implementation; no fictitious cross-language algorithm was
introduced.

Browser scope is 1586×992 light/EN and 390×844 dark/VI in both browsers, with
literal highlights, no root overflow, excerpt-scoped axe and the public-mode
Collection refusal. All four saved production screenshots were inspected.
This is not nine-reference validation or native zoom certification.

Exploratory whole-page axe initially failed 3/4 while measuring entry opacity;
matching the established reduced-motion gate made light pass. Settled dark still
failed 2/4 on the unchanged primary button (2.27:1) and BM25 label (4.32:1).
Those out-of-contract visual findings are retained for TEST-003, not called
flaky, fixed or certified here. The new contract test was scoped to the changed
excerpt renderer without excluding an axe rule; literal-mark/refusal assertions
remain exact. One browser run was interrupted after a test selector incorrectly
used the dialog action's label instead of the existing Save evidence accessible
name; that run is not a passing gate. The corrected run is the 4/4 result above.

## Security, artifacts, files and remaining scope

The checked access/privacy contracts pass; this is not a whole-repository
security certification. No real credentials or private research are in the new
fixtures. Bearers are synthetic test sentinels or caller-owned memory, never
public URLs or persistent session storage. Existing hidden-field projection,
configuration redaction and loopback/Host/Origin controls remain intact.

Created: three cross_layer JSON fixtures, test_cross_layer_contracts.py, three
crossLayer TS tests, CollectionTargetDialog.test.tsx, test-002-contracts.spec.ts
and this receipt. Modified: discovery.py/schemas.py, searchModel.ts/types.ts,
evaluationFixtures.ts, CollectionTargetDialog.tsx, existing Evaluation/telemetry
API tests, README, PROJECT_STATE and the current checkpoint. Deleted: none.
Only deliberate TEST-002 source/tests/docs are committed. No database, provider
output, generated schema/build, screenshot/trace/report, cache or machine path
is included. The original 12 unrelated untracked paths are preserved.

Collections/model-test bearer integration remains staged; their normal api.ts
wrappers truthfully reach refusal states rather than bypassing local access.
TEST-002 records and tests that existing limitation; it does not add the feature.
Existing warnings, bundle-size warning and dark visual findings remain. No
new failing contract or full-suite regression was found after the repairs.

The actual master-plan graph makes TEST-003 the UI-001…UI-012 visual branch and
TEST-004 depend on both TEST-002 and TEST-003. Optional EVAL-004 does not block
native-only completion. Checkpoint and PROJECT_STATE record TEST-002-A through
G complete and retain the earlier planning/reproduction evidence as history.

Exact Next Action: TEST-003 — Nine-reference visual validation. Not started.
