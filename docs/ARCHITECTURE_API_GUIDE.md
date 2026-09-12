# Architecture and API guide

This guide describes the provider-free inspection surfaces used by the
personal/demo research workspace. It is intentionally operational: the
Retrieval Lab observes the loaded local index and never rebuilds data or calls
an LLM.

## Request path

```text
React workspace
  -> FastAPI query/retrieval API
     -> conservative query normalization and ticker detection
     -> BM25 + dense candidate retrieval
     -> optional RRF fusion and cross-encoder reranking
     -> V7 context rendering with source identity preserved
     -> generator (query routes only)
```

`POST /retrieval/inspect` stops before generation. The returned interpretation,
stage timings, candidate list, and selected chunk IDs are the same trace used
by the UI. The default preset remains `hybrid_rerank`; comparison is an
explicit second inspection with the selected preset and is labelled as a
diagnostic, not a production setting change.

## Read-only workspace endpoints

| Endpoint | Purpose | Provider call |
|---|---|---:|
| `GET /documents` | Paginated loaded-filing catalog | 0 |
| `GET /documents/{id}` | One safe filing metadata record | 0 |
| `GET /documents/{id}/chunks` | Source previews for one filing | 0 |
| `POST /retrieval/inspect` | Normalization and retrieval trace | 0 |
| `GET /system/info` | Allowlisted corpus, models, presets, build metadata | 0 |
| `GET /evaluation/runs` | Published report summaries after schema validation | 0 |
| `GET /evaluation/runs/{run_id}` | One published report after schema validation | 0 |

Document and evaluation paths are allowlisted. The public evaluation API does
not browse `data/diagnostics`, checkpoints, prompts, or arbitrary user paths.
Reports must be published through `scripts/publish_evaluation_report.py` and
bind dataset/corpus/model/profile/rubric/source-artifact provenance.

## Frontend state boundaries

- Conversation records, notes, bookmarks, feedback, and collections are local
  browser state. They never enter provider prompts unless the user submits a
  new question through the normal query flow.
- Analytics is metadata-only and capped locally. Export excludes questions,
  answers, excerpts, session IDs, and secrets.
- Evaluation Recorded mode uses a clearly labelled fixture. Live mode reads
  only the validated public API.
- `?view=` preserves the selected workspace surface for reload/shareable local
  navigation. English/Vietnamese UI preference and answer language remain
  separate settings.

## Local verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py tests/test_public_report.py
Set-Location frontend
bun run test
bun run lint
bun run build
```

The provider campaign is separate from these checks. Its manifest and
append-only request ledger must be created before execution; quota failure is
reported as `INCOMPLETE`, never silently treated as a benchmark result.
