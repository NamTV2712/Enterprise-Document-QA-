# Backend contracts

Review FastAPI DTO compatibility, SSE event/request IDs, bounded queues,
cancellation, structured errors, cache ownership, acquisition admission, and
safe logging together with the owning route. A client abort does not prove that
worker execution stopped. A per-request client does not prove cross-request
single-flight. A declared timeout does not prove leader-path enforcement.

Preserve provider-free inspection, key5-only Groq policy, local-Qdrant worker
constraints, and hermetic socket guards.
