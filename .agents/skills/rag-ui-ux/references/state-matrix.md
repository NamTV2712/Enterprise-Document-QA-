# State and interaction matrix

Every async or interactive surface must have an explicit state. State copy
answers what happened, why it matters, and what the user can do next.

| Surface | Loading | Empty | Error | Recovery | Long content |
|---|---|---|---|---|---|
| Chat | Searching/generating with Stop | Ask a filing question; sample fills draft | Answer unavailable/partial with Retry | Retry or new question; preserve draft | Markdown readable; source actions remain near answer |
| Documents | Stable list skeleton | No filings match scope | Filings could not load | Retry; keep stale list when safe | Wrap/truncate IDs; detail shows full values |
| Search | Search submitted | No matching passages | Search unavailable | Retry/change filters | Excerpt clamps; reader expands |
| Source reader | Loading excerpt | Source unavailable | Reader could not load | Retry or use stored preview | Scroll inside reader only; preserve selection |
| Library | Loading local records | No saved conversations | Storage unavailable | Continue in tab/export/retry | No silent truncation; preserve export |
| Tools | Loading diagnostic data | No recorded/live data | Tool unavailable | Retry or open details | Raw JSON/details are secondary |
| Architecture | Loading static artifact | Artifact absent | Artifact validation/load failed | Open standalone or inspect text outline | Viewer adapts; no clipped diagram |

Required interaction states: default, hover, pressed, focus-visible, selected,
disabled, loading, error, stale where applicable, and read-only where actions
are unavailable. Hover may enhance a citation preview but cannot be the only
way to access it.

Destructive actions such as deleting a conversation require confirmation or an
undo path. Changing view must preserve drafts, conversation content, and
relevant filter state.
