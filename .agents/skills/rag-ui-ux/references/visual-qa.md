# Visual QA and performance evidence

## Browser matrix

Inspect the production build at CSS widths 390, 768, 1024, 1280, 1366, 1440,
and 1920. Check Light/Dark and EN/VI on Chat, Documents, Search, and Library;
pair tool and error states where useful. Test native browser zoom at 125%,
150%, and 200% separately from viewport emulation. If a capability is not
available, record that gate as unverified rather than substituting a guess.

## Geometry and task evidence

Verify `scrollWidth <= innerWidth` except for intentional local table/code
scrolling; no clipped primary labels, source titles, buttons, or recovery copy;
no fixed bar covers content; drawers have close and focus-return paths; tab order
follows task order; and mobile primary actions are near the top.

Capture the affected state before and after a change. A nonzero bounding box is
not proof of visibility: inspect opacity, clipping, overlap, ancestor visibility,
and screenshots. Include the task-semantics record: entry point, intent,
available evidence, label, transition, first useful content, and recovery.

Reject a result when catalog browsing is labelled as an answer/retrieval task,
repeated chrome displaces the document body, a primary recovery is below a
covered or clipped region, or a representation makes an unsupported exact,
complete, official, or unavailable claim.

## Accessibility

Use semantic buttons/links/labels, accessible names for icon buttons, sequential
headings, visible focus, Escape routes, status announcements, and reduced motion.
Normal text must meet 4.5:1; non-text controls and large text at least 3:1.
Run an actual rendered scan for changed surfaces. Do not infer full WCAG
conformance from screenshots or source markup alone.

## Performance

Measure a production build with stable browser/device, cold/warm state, data
volume, backend mode, and CPU throttling recorded. Attribute long tasks before
optimizing. Inspect streaming, Markdown rendering, persistence, view switching,
theme changes, source selection, resize, Search, Library, and Architecture
mount/unmount.

Targets retained from the project contract:

- p95 interaction input-to-next-paint <=100ms for at least 30 warm samples;
- p95 warm view switch <=200ms excluding network;
- Library search p95 <=200ms at 100 conversations × 100 messages;
- 200-message chat preserves focus, scroll, citation selection, and Markdown;
- 60-second streaming stays responsive and flushes final output;
- 20 open/close/filter cycles retain no unbounded listeners or caches.

Report failed targets with trace evidence. Do not call provider/network latency a
rendering improvement or claim all caches are bounded when the implementation
does not establish that.

## Archify evidence

Keep deterministic `deliver` receipt, run `visual-check` on exact trusted HTML,
and record automated browser evidence separately from perceptual review. A
validator pass alone does not prove readability.
