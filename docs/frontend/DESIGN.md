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
responsive panels. Keep answer readable before opening an inspector. Use tabs
or drawers when Sources and Reader cannot fit without squeezing the answer.

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
