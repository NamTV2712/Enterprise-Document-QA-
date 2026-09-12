# Frontend architecture reference

Use this map to locate ownership before changing a surface. Confirm symbols in
the current implementation because this reference describes boundaries, not a
second API contract.

## Owners

- `useResearchDraft` owns editable scope and per-conversation draft hydration.
- `useResearchSession` owns submit, streaming, abort, flush, and session epochs.
- `useReaderSession` owns reader generation, abort signals, and the target tuple:
  conversation, message, variant, document, source, and representation.
- Evidence selection is cleared or revalidated on conversation/answer changes.
- Transient answer actions carry IDs and resolve against the current version at
  invocation; they do not fall through to the newest answer.
- Conversation persistence is schema-versioned and coordinated through the
  IndexedDB/localStorage mirror. BroadcastChannel notifies; it is not the writer.
- Reader chunk details have TTL/in-flight deduplication. Document-list caches
  are not automatically bounded; profile their actual retention.

## React discipline

Derive display values during render when possible. Use effects for external
systems, subscriptions, persistence, or abort cleanup, with complete
dependencies and cleanup. Do not add memoization, global stores, event
listeners, or data-fetching libraries without an evidence-backed ownership need.
Keep request identity and stale-response checks explicit.

## Review questions

1. Which hook/component owns the state?
2. What identity and revision does the result carry?
3. What happens when scope, conversation, variant, or representation changes?
4. Who owns cancellation and who owns the visible error?
5. Which element scrolls, and where does focus return?
6. Does the rendered label describe the current user task?

Route source identity, revision, acquisition, and coverage questions to
`rag-document-provenance`; route request/SSE contract changes to `rag-core`.
