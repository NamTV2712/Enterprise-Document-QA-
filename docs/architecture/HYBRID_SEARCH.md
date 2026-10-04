# Hybrid Search diagram

[PNG](hybrid-search.png) · [Interactive HTML](hybrid-search.html) ·
[Editable specification](hybrid-search.dataflow.json)

The README image explains complementary retrieval and the transformation from
ranked candidates to cited evidence. Download the HTML and open it locally to
inspect nodes, relationships, themes and clean exports.

## Source evidence

- [`HybridRetriever._retrieve_with_embedding`](../../src/retrieval/hybrid_retriever.py):
  ticker/section filtering, BM25 candidates, Qdrant vector candidates, optional
  lexical ladder, fusion by `chunk_id`, RRF constant 60, bounded candidate pool,
  cross-encoder query/passage scoring, relative relevance cutoff, optional
  structured-match promotion and final top-k.
- [`RAGPipeline`](../../src/generation/rag_pipeline.py): query shaping, embedding
  reuse, cache-hit replay, retrieval on a cache miss and source metadata for SSE.
- [`Generator`](../../src/generation/generator.py): rendered evidence context,
  grounded generation instructions and citation-bearing responses.

Branches depict independent rank sources. The implementation executes retrieval
stages sequentially. This focused cache-miss view omits cache replay, conversation
rewriting and exceptional paths. Eligible financial-table queries can promote a
structured match before top-k selection. The diagram does not claim measured
search quality, timing or concurrent branch execution.

## Delivery and review

Authored on 2026-10-04 using the installed diagram renderer. Project documentation
uses English. The specification and HTML are retained for reproducible edits.

| Item | Recorded result |
|---|---|
| Diagram type | `dataflow` |
| Deterministic delivery | 9/9 showcase checks; 0 errors, 0 warnings |
| Specification bytes | 4,585 |
| HTML bytes | 727,573 |
| Browser review | CUA; four exact desktop viewport measurements |
| Theme coverage | Light/dark at 1440×900 and 2048×1320 |
| Containment | No horizontal or vertical overflow at checked desktop sizes |
| Perceptual review | Passed; actual HTML in both themes and exported PNG inspected |
| Visual correction rounds | 2 |
| README export | Native full-diagram light-theme PNG; 4320×2000 |

Specification SHA-256:
`3049bb25d5b05fb76059ea4534b73c29ee012352992efb009565e6aa495aba8f`

HTML SHA-256:
`83516b51bd0a51186ab2c45603ccf6efa781d78550cf2df326bc237fb48dc749`

The checked desktop sizes were 1440×900, 1600×1000, 1920×1080 and 2048×1320.
Browser evidence was collected through the available CUA interface. The renderer's
separate `visual-check` command was not run; CUA evidence is a separate review
record and does not claim that command passed. Local screenshots and diagnostic
receipts remain outside Git. Only the public diagram assets and this source note
are published.
