# SEC research workspace design system

## Product character

Calm, precise, evidence-first research workbench. The distinctive quality is
the visible connection between an answer citation and the source excerpt it
opens. It should feel like a focused financial research tool with a developer
inspection layer, not a generic AI dashboard.

## Hierarchy and copy

- Research task and source identity are primary; IDs, paths, scores, models,
  and raw status are secondary details.
- Primary action > secondary action > utility action. Use labels that describe
  the current task: a catalog action must not say “this answer” or “retrieved
  sources” without a submitted answer and retrieved evidence.
- Chat, Documents, Search, and Library are primary. Retrieval Lab, Evaluation,
  Analytics, System, and Architecture are secondary Tools surfaces.
- Prefer one coherent surface with progressive disclosure for filters and
  diagnostics. Do not turn an inspector, source list, and reader into equal
  dashboard columns unless the task and width support it.

## Layout and responsive composition

- Read current CSS/container ownership before changing dimensions. The former
  56px/216px/300px values are historical guidance, not unconditional runtime
  constants.
- Chat puts the answer first; sources and reader are contextual inspectors.
  At medium widths use tabs or a drawer; mobile uses one primary surface and a
  source/reader sheet.
- Evaluate the containing rail and its header stack, not only an inner reader
  canvas. First useful document content must not be displaced by repeated
  identity chrome.
- No accidental page-level horizontal scroll. Intentional table/code scrolling
  must be local and keyboard reachable.

## Tokens and type

Use the current semantic CSS tokens for canvas, surfaces, text, borders, focus,
and state. Validate actual foreground/background pairs in both themes; do not
copy a stale palette into components or map one alias to incompatible roles.

- UI and answers use the repository’s current sans stack; monospace is for IDs,
  code, and diagnostics. Do not prescribe a font migration.
- Keep answer and reader text comfortably readable, metadata visibly secondary,
  and desktop lines near 60–75 characters when the container permits.
- Preserve the current spacing/radius language unless the implementation and
  rendered evidence justify a change. Minimum interactive target is 44px and
  mobile input text is 16px.
- State uses text/icon plus a visual signal; color alone is insufficient.

## Evidence language

User question is quiet context, answer is a readable document block, and source
cards show identity, filing date, section, excerpt, and ranking metadata only
when present. A reader must state whether it is indexed, normalized, structured,
or unavailable. Never invent confidence, pages, exact matches, official PDFs,
or retrieved sources. Detailed provenance rules live in
`../../rag-document-provenance/references/` and are handed off when needed.
