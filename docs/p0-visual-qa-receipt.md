# P0 visual QA receipt

Date: 2026-09-09

This receipt covers the first Plan V2 visual pass after P0.2–P0.5. It uses the
production Vite preview at `http://127.0.0.1:4173/`, not the development
server. The latest build emitted `index-CsGOjmko.js` and `index-CfT-Fge0.css`.

## Commands

- `bun run lint` — passed.
- Targeted component tests — passed: ChatInput, Tooltip, Documents (7 tests in
  the final focus/status pass); earlier P0.3 and P0.4 receipts record their
  targeted suites separately.
- `bun run build` — passed with Vite 6.4.3.
- Browser verification — passed through the Codex browser accessibility tree,
  keyboard actions, computed styles, and production screenshots.

## N1–N8 receipt

| ID | Result | Evidence |
|---|---|---|
| N1 | Fixed | Tooltip uses semantic surface/foreground/border tokens and a matching arrow. Focused-tooltip test verifies `aria-describedby`; Light/Dark computed-style smoke checks found no unresolved tooltip variables. |
| N2 | Fixed | `.chat-input-island` owns the focus ring; scoped textarea `:focus-visible` no longer adds a second outline. The rebuilt Light/VI focus screenshot shows one outer ring. |
| N3 | Fixed | One stable template ID now resolves localized copy for the active locale. EN and VI palette searches showed only the active locale, and selecting a template did not change the locale. |
| N4 | Fixed | Palette rows are a `listbox`/`option` model with `aria-selected`, active-row styling, Arrow/Home/End/Enter/Escape handling, scroll-into-view, and focus restoration. Dark selected-row screenshot and AX tree confirm the active state. |
| N5 | Fixed | Documents search now has a visible label aligned with Company/Section. Loading, unavailable, empty catalog, and filtered-empty states are distinct; the rebuilt VI error screenshot shows Retry plus `Không khả dụng`, without a contradictory empty message. |
| N6 | Addressed for P0 | Template selection applies the complete scope snapshot; free text retains and displays the current scope. Browser verification showed the Risk groups template question paired with `Risk Factors · Top 5` and no stale comparison flag. Start-card density remains a P1.3/O10 concern. |
| N7 | Fixed | Retry/status actions use semantic warning/error hover roles rather than blanket white opacity. Light and Dark offline screenshots keep the action readable. |
| N8 | Fixed | ConnectionStatus/offline copy uses explicit semantic foreground/icon/surface roles. Light/VI, Dark/VI, and Dark/EN screenshots show readable offline status and recovery action. |

## Classified non-bugs

- O2: OS/browser-native language popup behavior is not cloned; the segmented
  control has a visible label group, selected state, and keyboard focus.
- O5: native Top-K/select behavior is preserved where semantics are stronger
  than a visual clone; shared select focus and portal behavior were tested.
- O7: Retrieval Lab candidate-pool native select is treated as a browser
  control, not as fake data or a visual defect.
- O9: Analytics range native select is likewise retained pending a concrete
  alignment or accessibility reproduction.

## Coverage boundary

The current preview has the FastAPI backend offline, so loaded-document/source
data and successful retrieval states are intentionally not claimed here. The
receipt was captured at the available compact browser viewport (approximately
640px); the full width/zoom matrix remains a later P1.5/P4.2 gate. No axe run
or source-viewer continuity claim is made by this receipt.
