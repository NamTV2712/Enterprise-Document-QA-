# Agent Operating Guide

This file is the stable operating guide for AI coding agents working in this repository. It should stay concise and avoid duplicating `PROJECT_STATE.md`, which is the living project journal.

## Read First

- Read `PROJECT_STATE.md` before making non-trivial changes. It contains the latest evaluation state, rejected experiments, known limitations, and current milestone context.
- Read `README.md` before changing public-facing behavior or docs.
- Prefer small, evidence-backed changes. Do not redesign retrieval, evaluation, Docker, or ingestion paths without first checking the documented decisions in `PROJECT_STATE.md`.
- Keep new comments, docstrings, and docs in English.

## Repository Boundaries

- `data/` is intentionally git-ignored and contains local SEC filings, chunks, embeddings, Qdrant storage, and evaluation artifacts. Do not delete, regenerate, or move it unless explicitly requested.
- `.env` contains secrets and must never be committed. Use `.env.example` for documented configuration.
- Do not commit model caches, local virtual environments, Docker build artifacts, or generated diagnostic outputs.
- If the worktree is dirty, preserve unrelated changes. Never revert user work unless explicitly asked.

## Frontend (`frontend/`)

- `frontend/` is a separate Vite/React/TypeScript application generated through Google AI Studio. Treat it as a distinct Node/Bun stack; do not run Python tooling inside it.
- The frontend is deployed independently. The backend Docker image never bundles or serves it, and `.dockerignore` must continue to exclude `frontend/`.
- Keep dependencies, build output, platform state, and local environment files untracked. Browser-exposed `VITE_*` variables must never contain secrets.
- For Vercel, set the project root directory to `frontend` and configure `VITE_API_BASE_URL` with a reachable backend URL, not `localhost`.

## Project-Specific Traps

- Qdrant local mode uses a file lock. Run the API with one worker when `QDRANT_MODE=local`; use Qdrant server or Qdrant Cloud before enabling multi-worker serving.
- Docker intentionally installs CPU-only PyTorch before `requirements.txt`. Do not pin CUDA PyTorch in `requirements.txt`; local Legion development can use CUDA separately.
- `scripts.chunk_filings` can overwrite chunk files and remove appended `financial_table` chunks. If rechunking, rerun `scripts.add_table_chunks`, `scripts.embed_chunks`, and `scripts.index_chunks` in order.
- `scripts.embed_chunks` depends on source/output freshness. Do not assume existing embedded files reflect changed chunk files without checking timestamps or rerunning the script.
- `/supported-tickers` reports searchable embedded tickers, not the full configured ticker list.
- The official reported benchmark is the clean priority `<=2` N=30 evaluation unless `PROJECT_STATE.md` explicitly says a newer official run supersedes it. Do not publish checkpoint-merged aggregates as official results.
- Groq/Gemini quota errors can produce skipped judge records. Never treat quota-skipped or checkpoint-mixed results as final metrics.
- The Google AI Studio/Next.js UI issue from the last session was frontend env configuration, not backend readiness: the frontend must use `NEXT_PUBLIC_API_BASE_URL` pointing at the active ngrok HTTPS URL and rebuild/apply changes.
- Ngrok free-tier browser fetches may require the `ngrok-skip-browser-warning: true` header. Backend CORS is already open for demos with `allow_origins=["*"]`.

## Change Discipline

- Update `README.md` for user-facing setup, architecture, or reported status changes.
- Update `PROJECT_STATE.md` for new milestones, evaluation results, rejected experiments, operational findings, or important caveats.
- Keep `AGENTS.md` stable. Add only recurring operating rules or traps that future agents cannot reliably infer from the code.
- Before committing, inspect `git status`, `git diff`, and recent commits. Commit only intended files.
