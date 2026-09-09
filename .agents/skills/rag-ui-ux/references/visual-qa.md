# Visual QA and performance evidence

## Browser matrix

Inspect the production build at CSS widths 390, 768, 1024, 1280, 1366, 1440,
and 1920. Check Light/Dark and EN/VI on Chat, Documents, Search, and Library;
pair tool/error states where useful. Test real browser zoom at 125%, 150%, and
200% separately from viewport emulation.

## Geometry checks

Verify:

- document `scrollWidth <= innerWidth` except for intentional local table/code
  scrolling;
- no clipped primary labels, source titles, buttons, or error copy;
- answer and composer are not covered by fixed/sticky elements;
- inspector/drawer has a close and focus-return path;
- tab order follows the visual/task order;
- selected state remains visible without color alone;
- mobile primary action is reachable near the top.

Do not accept a nonzero bounding box as proof that content is visible. Inspect
opacity/visibility ancestors, clipping, overlap, and screenshots.

## Accessibility

Use semantic buttons/links/labels, accessible names for icon buttons, sequential
headings, visible focus, Escape routes, screen-reader status updates, and
reduced motion. Normal text must meet 4.5:1; non-text controls and large text
must meet at least 3:1. Run an actual rendered scan for changed surfaces.

## Performance

Measure production build with a stable browser/device and record cold/warm
state, data volume, backend mode, and CPU throttling. Attribute long tasks
before optimizing. Inspect streaming, Markdown re-rendering, persistence,
view switching, theme changes, source selection, resize, Search, Library, and
Architecture mount/unmount.

Targets for this project:

- p95 interaction input-to-next-paint <=100ms for at least 30 warm samples;
- p95 warm view switch <=200ms excluding network;
- Library search p95 <=200ms using 100 conversations × 100 messages;
- 200-message chat keeps focus, scroll, citation selection, and Markdown;
- 60-second streaming keeps input responsive and flushes final output;
- 20 open/close/filter cycles do not retain unbounded listeners or caches.

Report failed targets with trace evidence. Do not lower a threshold to claim a
pass, and do not call provider/network latency a rendering improvement.

## Archify evidence

For each delivered diagram keep deterministic `deliver` receipt, then run
`visual-check` on the exact trusted HTML. Record automated browser evidence and
perceptual visual review separately. A validator pass alone does not prove the
diagram is readable.
