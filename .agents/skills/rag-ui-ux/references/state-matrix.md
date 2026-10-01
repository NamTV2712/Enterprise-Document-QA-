# State and interaction matrix

Every async or interactive surface has an explicit state. Copy answers what
happened, why it matters, and what the user can do next. State belongs to the
owning conversation, request, answer variant, document, and representation.

| Surface | Loading | Empty | Error | Recovery | Long/stale content |
|---|---|---|---|---|---|
| Chat | Searching/generating with Stop | Ask a filing question; sample fills draft | Answer unavailable/partial with Retry | Retry or new question; preserve draft | Markdown readable; source actions stay near answer |
| Documents | Stable list skeleton | No filings match scope | Filings could not load | Retry; keep safe stale list | Wrap/truncate IDs; details show full values |
| Search | Search submitted | No matching passages | Search unavailable | Retry/change filters | Excerpt clamps; reader expands honestly |
| Source reader | Loading selected representation | Source or representation unavailable | Reader could not load | Retry or choose an available representation | Scroll inside reader; preserve selection and revision |
| Library | Loading local records | No saved conversations | Storage unavailable | Continue in tab/export/retry | Preserve export; do not silently truncate |
| Tools | Loading diagnostics | No recorded/live data | Tool unavailable | Retry or open details | Raw JSON is secondary |
| Architecture | Loading static artifact | Artifact absent | Validation/load failed | Open standalone or inspect outline | Viewer adapts; no clipped diagram |

Required interaction states are default, hover, pressed, focus-visible,
selected, disabled, loading, error, stale where applicable, and read-only where
actions are unavailable. Hover may enhance a citation preview but cannot be its
only access path. Destructive actions require confirmation or undo.

## Cross-context rules

- Draft scope is not submitted scope. A submitted answer keeps its original
  scope even if the draft changes during streaming.
- Switching conversation, message, variant, document, or representation
  invalidates stale success and error updates. Abort and generation checks must
  be visible in behavior, not inferred from a spinner.
- Notifications identify their owning operation and clearing condition. They do
  not survive a context switch unless intentionally persistent.
- View changes preserve drafts, conversation content, and relevant filters.
- A saved answer or historical citation resolves against its saved identity and
  revision, never the newest answer by position.

## Reader-specific states

Distinguish indexed excerpt, normalized document, structured document, PDF
availability, not-found, ambiguous, unavailable, and stale revision. “Complete”
means the checked representation has verified coverage; a successful parser
response alone is not evidence of prose or table completeness.
