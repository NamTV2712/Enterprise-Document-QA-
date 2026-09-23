# SEC Research Workspace Design Contract

## Product

Enterprise Document QA is a SEC 10-K research workbench. Its primary job is to
help a researcher ask a grounded question, read the answer, inspect the exact
retrieved evidence, and continue or save the work.

## Information architecture

Primary destinations are Chat, Documents, Search, and Library. Retrieval Lab,
Evaluation, Analytics, System, and Architecture are secondary Tools. Chat is a
workbench, Documents/Search are browse-and-inspect surfaces, Library is a
local content surface, and Tools are diagnostic surfaces.

## Visual direction

Use the repository-local `rag-ui-ux` skill and its references. The visual
identity comes from citation-to-source continuity, restrained blue interaction
accents, cool neutral surfaces, strong typography, and calm evidence states.
The supplied Light/Dark screenshots are directional references, not permission
to copy decorative cards, fake metrics, or unsupported controls.

## Layout

Use a 56px header, a 216px/56px navigation sidebar, and container-aware
responsive workbench modes. At eligible wide desktop sizes, Research, Sources,
and Document are simultaneous bounded surfaces; at narrower widths, Sources and
Document become an explicit dock or modal contextual surface. Keep answer and
document prose readable before reducing a pane, and use tabs or drawers when
the measured geometry cannot satisfy the research/source/document minimums.
The shared pane contract is recorded in `V5_WORKBENCH_CONTRACT.md`.

## Tokens

The authoritative colors, spacing, geometry, typography, state, and RAG visual
rules live in `.agents/skills/rag-ui-ux/references/design-system.md` and the
semantic CSS token layer. Component files must consume roles rather than raw
hex values.

## Design review

Every substantial change records its first decision, primary action, states,
mobile order, five self-review risks, and visual evidence. Build success is
necessary but not sufficient; the rendered app must be inspected and iterated.

## Current skill governance

The repository-local `rag-ui-ux` skill is the product authority and routes
retrieval, evaluation, security, performance, and document-provenance questions
to their focused project skills. The fixed dimensions above describe intended
design constraints; implementation and rendered evidence remain authoritative
when they differ. A catalog-to-reader transition must be judged by its actual
user intent and resulting surface, including whether an answer or retrieved
sources exist.

## Current V5 presentation

V5-08 is the current implementation baseline. The workbench presents Research,
Sources, and Document as sibling regions when the measured geometry supports
them: 1440×900 uses 56px navigation with 624px Research, 304px Sources, two
8px splitters, and 440px Document; 1920×1080 uses 216px navigation and 944px
Research with the same contextual tracks. 1366×768 and 1280×800 use an
accessible Sources/Document context dock, 1024px and short wide tracks use a
truthful contextual surface, and tablet/phone widths use the existing drawer
or single-surface lifecycle. The reader keeps the dominant canvas and a
bounded lower Evidence/Metadata/Notes context; source identity, exactness,
stale/unavailable states, and reader requests remain owned by the existing
domain components.

The shared workbench controller owns only presentation state: layout mode,
active contextual pane, source filter, active representation/context tab,
find text, and pane preferences. App remains authoritative for route and
document identity, while Documents, Search, Retrieval Lab, and Library retain
their fetch, retrieval, cache, reader, and persistence owners. PDF remains an
optional representation: Structured and Normalized text remain the safe
fallback, while PDF is selectable only when a current backend manifest admits
an `OFFICIAL_PDF` or `DERIVED_PDF` artifact.

## Truthful route surfaces

The route surfaces preserve the enterprise reference composition while binding
every value to an authoritative source. Research renders live SSE answers,
citations, stages, and reader handoffs; Documents renders catalog metadata,
reader coverage, and representation availability; Search and Retrieval Lab
render `/retrieval/inspect` traces without generation or confidence claims;
Library renders browser-local conversations, evidence, and storage state;
Models renders only `/system/info` retrieval fields; Pipeline renders the
API-007 public definition and, after explicit local connection, staged durable
job history/detail; and Evaluation renders only public
evaluation reports. Missing fields use an explicit unavailable state rather
than a mock value. These rules apply in both themes and at every responsive
breakpoint.

## PDF representation UX

The PDF reader uses the real PDF.js canvas/text layer and a document-bound
content URL. Its header labels generated-representation pages separately from
official PDF pages; it also exposes renderer, source/revision, page-count, and
artifact identity metadata. In the current corpus, only `DERIVED_PDF` is
admitted; `OFFICIAL_PDF` remains schema/helper support without admitted
official bytes. PDF.js is dynamically loaded only after an eligible backend
manifest is available. The download action is bound to the current document
and representation type, never to a browser-supplied path or URL.

Evidence overlays are conservative: an amber rectangle appears only after the
backend returns an exact location whose chunk hash, source document, source-set
revision, document revision, artifact hash, and mapping sidecar all match the
active document. Ambiguous, stale, unavailable, failed, and unsupported states
retain the selected evidence and show the reason without painting an
approximate page highlight. Responsive layout changes preserve the selected
representation through the shared workbench controller, including the narrow
drawer transition.
