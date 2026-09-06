# Local Docker release runbook

This runbook validates a provider-free local release. It does not rebuild the
canonical corpus, embeddings, or Qdrant index, and it does not call Groq.
Generated reports and receipts belong under `data/diagnostics/`, which is
ignored by Git.

## 1. Preflight

Use a clean worktree and confirm that the existing local artifacts are
available:

```powershell
.venv\Scripts\python.exe scripts/diagnostics/release_preflight.py `
  --json data/diagnostics/local_release_preflight.json
```

`BLOCKED` is expected when Docker Desktop is stopped. `FAIL` is not. The
preflight checks the trusted index manifest, embedding/reranker pins, model
cache hints, port, disk space, and `.dockerignore` without printing secrets.

## 2. Build a provenance-bound image

Set the commit once for both the image build and Compose runtime. Compose uses
the full commit as the image tag; the explicit tag step keeps the build and
runtime references identical on a local machine.

```powershell
$releaseSha = (git rev-parse HEAD).Trim()
$env:GIT_REVISION = $releaseSha
docker compose build --build-arg GIT_REVISION=$releaseSha
docker tag edqa-api:local edqa-api:$releaseSha
docker compose up -d --no-build
```

The image must carry these labels:

- `org.opencontainers.image.revision`
- `ai.edqa.embedding-model` and `ai.edqa.embedding-revision`
- `ai.edqa.reranker-model` and `ai.edqa.reranker-revision`

The Dockerfile pre-downloads both pinned models. Runtime uses one Uvicorn
worker because local Qdrant uses a file lock.

## 3. Provider-free offline smoke

Wait until Compose reports `healthy`, then check readiness and searchable
tickers. Readiness loads the local Qdrant payloads, BM25 data, embedding model,
and reranker; it does not invoke an LLM provider.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/ready | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8000/supported-tickers | ConvertTo-Json -Depth 8
```

Do not use `/query`, `/query/stream`, or `/query/decomposed` in this smoke:
those routes can spend provider quota. A successful receipt requires
`pipeline_ready=true`, a non-empty ticker list, the health revision matching
`$releaseSha`, and all image labels present.

## 4. Write the receipt

```powershell
.venv\Scripts\python.exe scripts/diagnostics/release_receipt.py `
  --image edqa-api:$releaseSha `
  --preflight data/diagnostics/local_release_preflight.json `
  --output data/diagnostics/local_release_receipt.json
```

The receipt records only non-secret provenance and smoke responses. It records
`provider_calls: 0`, the image ID/labels, commit, preflight hash, readiness,
and ticker discovery. A receipt with `overall=FAIL` is not a release
candidate.

## 5. Cleanup

```powershell
docker compose down
```

Keep the image if it is needed for review; remove it only as a deliberate
local Docker cleanup. Never remove `data/processed/` as part of this runbook.

## Troubleshooting

- If preflight is `BLOCKED`, start Docker Desktop and rerun it.
- If readiness returns `503`, inspect `docker compose logs --tail=120 rag-api`;
  model loading can take a few minutes on CPU.
- If health reports `build.revision=unknown`, set `$env:GIT_REVISION` before
  both `docker compose build` and `docker compose up`, tag the image with the
  same full SHA, and recreate the service.
- If Qdrant reports a lock, stop any host API using the same local path before
  starting Compose.

## CI coverage

Backend CI runs the hermetic suite, marked local HTTP/SSE integration tests,
and compile checks. Frontend CI runs unit/type/build/contrast/browser gates;
its integration job builds the production frontend and runs the real HTTP/SSE
harness in Chromium and Firefox. Neither job calls a provider.
