# SHOWCASE-002 — Public Showcase Quality Receipt

Documentation/artifact audit dated **2026-10-03**. Starting `main`:
`9d7acf9c7c5bf1ad345f8a3783b97680c6c49035`. Product behavior is unchanged;
the code release and its test counts remain bound to
`cbaacc3765f8dbca2ff04247cb24fd773751a0f9` in the
[final improvement receipt](IMPROVEMENT_FINAL_RECEIPT.md).

## Architecture artifacts

| Artifact | SHA-256 |
|---|---|
| [Authored JSON](architecture/sec-research-copilot-showcase.architecture.json) | `eb070ea87d71d8c17943e4c2dc96f6028343232f622d7a5a45adcb596b0266d8` |
| [Generated HTML, Git LF bytes](architecture/sec-research-copilot-showcase.html) | `ffd582970f692deb59e833ba24ab9296f5a195fb5a48590ecc1763efb50ed3b8` |
| Local Archify delivery bytes | `864907864dbbd0f98f4174c5efe09af5ccaec3dc75019f838a1630e50aa90882` |
| [Canonical SVG export](assets/sec-research-copilot-architecture.svg) | `6b4d483e9aabfb714d7c582e79a3f9dc20f6029936379638d0812f3b1b9b3065` |

Archify `quality_profile=showcase`: **9/9 checks, zero errors, zero warnings**.
Git's existing automatic CRLF→LF filter normalizes the HTML's line endings;
its blob equals the delivery exactly after that conversion. Both byte forms
passed the browser gate. No generated HTML content was manually edited.
Delivery verified 11 repository source references against the starting revision.
Nine primary nodes show separate Quick and Deep paths, DATA-004 authority,
two process-local fixed workers, a single bounded Agent, closed tools and shared
retrieval/evidence infrastructure. The diagram is a communication overview;
[full architecture](../ARCHITECTURE.md) owns detailed contracts.

Commands, from repository root:

```powershell
node .agents/skills/archify/bin/archify.mjs validate architecture docs/architecture/sec-research-copilot-showcase.architecture.json --quality showcase --repo-root . --json
node .agents/skills/archify/bin/archify.mjs deliver architecture docs/architecture/sec-research-copilot-showcase.architecture.json docs/architecture/sec-research-copilot-showcase.html --quality showcase --repo-root . --json
node .agents/skills/archify/bin/archify.mjs visual-check docs/architecture/sec-research-copilot-showcase.html --json
```

The final delivered HTML passed the browser gate at **1440×900, 1600×1000,
1920×1080 and 2048×1320** without page overflow. Light/dark captures at the
smallest/largest endpoint were separately inspected: labels and all nine nodes
are contained, connectors are readable, and no card, label or dock collision
remains. One focused visual composition correction reduced vertical spacing and
removed redundant cards after the first candidate failed containment.

The SVG was downloaded through the generated viewer's **Export → SVG** command,
with trailing whitespace normalized before final checks, and inspected as a
standalone browser image. It retains
tags for the SEC corpus, cross-encoder and DATA-005 shared DB. Source and HTML
were frozen after the successful validation/delivery; the generated HTML was
not hand-edited. Diagnostic captures/receipts for this task stay in ignored local
audit storage rather than the public artifact set. Archify itself was not updated.

## Public presentation and file decisions

- Public display name: **SEC Research Copilot**. Repository slug remains
  `NamTV2712/Enterprise-Document-QA-`.
- [README](../README.md) presents Live Demo, Quick/Deep, one architecture image,
  six features, stack, engineering highlights, measured results, frozen validation,
  developer setup, visible limitations and deeper documentation links.
- The old technical sections are preserved in
  [Engineering Reference](ENGINEERING_REFERENCE.md), explicitly marked as
  historical where appropriate. Incoming historical README anchors are retained.
- Portfolio case study, demo guide, application copy and interview guide use the
  new display name; relevant historical names, code SHAs and evidence are retained.
- Public essentials (source, frontend, config, tests, Docker and architecture)
  remain. Engineering evidence (`PROJECT_STATE.md`, `TODO.md`, protocols/receipts
  and existing diagnostic architecture evidence) remains. Agent/developer tooling
  under `.agents/` remains, including its original licenses/notices.
- Added public files are the diagram source/HTML/SVG, engineering reference,
  documentation index, this receipt, root `LICENSE` and `SECURITY.md`.
  No tracked files are deleted. No product screenshot is added.
- Root MIT covers project-owned source/docs; bundled third-party licenses and
  notices are preserved. Source history identifies NamTV2712 as the project-code
  author. External dependencies and SEC filing content are not relicensed.

## Availability and claims

The [Live Demo](https://frontend-one-gamma-f9jf11u8ec.vercel.app) returned HTTP 200
and rendered the frontend, but displayed **API offline** and **Model unavailable**
during this audit. No question or provider call was submitted. README and the
Demo Guide label the availability accurately; the guide is not a published video.

GitHub description/homepage/topics were updated and read back successfully.
GitHub private vulnerability reporting was verified **disabled**; the
[security policy](../SECURITY.md) invents no email/private channel. Reporters can
request a private contact without posting vulnerability details.

Public measurements remain explicitly controlled development results. No
production SLA, distributed execution, exactly-once external effects, guaranteed
accuracy, blanket security or full accessibility certification is claimed.
Historical experiments and rejected capacity results remain accessible; they are
not promoted into new public benchmark claims.

This task uses docs/link/Markdown/SVG/privacy checks and Archify validation.
No new product test campaign, live Groq call, dependency update, schema change,
migration, capacity change or CI change is required for this docs-only scope.

## Documentation quality checks

- README UTF-8 Git blob bytes (consistent LF): **132,753 → 27,205**;
  final Windows checkout is **27,712 bytes**. Useful technical section bodies
  are preserved in the engineering reference, with relative link bases adjusted.
- Markdown structure and **222 relative file/anchor links** across nine changed
  Markdown documents passed. Historical README anchors remain resolvable.
  No Mermaid blocks remain in these changed documents, so no Mermaid parser
  gate is needed for this artifact set.
- The SVG is valid XML and self-contained: no external resource dependency,
  executable content or `foreignObject`. Embedded theme glyphs are static SVG.
- Changed public content matched no real local secret values, credential-shaped
  provider/GitHub keys or Windows user paths. The existing TEST-005 token remains
  explicitly a public synthetic fixture. All public Vercel references use the
  verified homepage URL.
- Root/docs audit covered 82 tracked files; 42 engineering-evidence files and
  237 developer-tooling files remain. Three historical receipts/plans contain
  documented local paths; these are retained engineering context and are not
  copied into the public overview. Existing design references and diagnostic
  assets are intentional evidence, not newly exposed product screenshots.
