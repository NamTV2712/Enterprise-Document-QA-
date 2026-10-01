# Document workspace journeys

## Catalog to reader

Catalog browsing starts with a document identity and available representations.
“Open document workspace” must open a document workspace or clearly name the
intermediate selection step. It must not construct an answer-scoped inspector
labelled “Retrieved sources” or “this answer” when no question and answer exist.
The next action must expose the normalized/structured source only when that
representation is available and its identity is preserved.

## Answer to evidence

Answer citations open the source and reader belonging to the citation’s answer
variant. The source card, excerpt, document, filing role, revision, and reader
representation stay synchronized. Switching variants or conversations rejects
stale reader replies and restores focus predictably.

## Reader quality

Inspect the containing rail, stacked headers, inspector, toolbar, and document
body together. First useful content must not be displaced by repeated identity
chrome. Search, outline, tables, and code scroll locally and remain keyboard
reachable. “Widen” changes a real available reading area; it must not merely
resize an inner canvas inside a constrained rail.

## Representation honesty

Normalized and structured search can differ. A structured result reporting
complete coverage while losing supported `div`/`span` prose is a product and
provenance defect, not a valid empty state. The UI must expose representation
availability and limitations rather than silently claiming “not found.”

Acquisition success is not reader admission or search readiness. Source identity,
revision, coverage, and availability are handed to
`rag-document-provenance`.

## Regression journeys

- Documents → open workspace with no question: no answer/retrieval labels.
- Documents → normalized original: direct structured/normalized transition.
- Indexed excerpt → reader: exact source/chunk identity is retained.
- Search a phrase visible in normalized text: structured no-match reports its
  representation limitation when coverage is incomplete.
- Switch answer variant while reader request is pending: stale result is ignored.
