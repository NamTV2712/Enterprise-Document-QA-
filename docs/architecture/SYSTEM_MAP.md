# FilingScope architecture poster

The poster presents **Evidence-Grounded SEC Filing Research with Hybrid RAG &
Durable AI Agents** as a numbered technical infographic. Its light background,
colored bands and detailed cards are designed for a GitHub README and portfolio
review. All technologies and execution boundaries are specific to this project.

[Full-resolution PNG](system-map.png) · [Editable SVG](system-map.svg) ·
[Interactive component overview](system-map.html) ·
[Overview specification](system-map.architecture.json)

The SVG is the editable source of the static poster. The HTML is a deliberately
smaller component overview with source links, theme switching and zoom; it is
not a pixel-for-pixel rendering of the detailed poster. Download HTML and open
it locally, since GitHub's file viewer does not execute it.

## Read the numbered bands

1. **Offline corpus preparation:** acquire SEC 10-K HTML, extract sections and
   financial tables, create token-aware chunks, encode them with Nomic, seal a
   hash-bound embedding generation, and publish vectors plus text/metadata to
   Qdrant. Table chunks retain reporting periods and units.
2. **Quick Research:** shape the submitted query, create its embedding, inspect
   eligible cache entries, retrieve scoped candidates, merge their ranks with
   RRF, rerank with a cross-encoder, and render evidence for grounded generation.
   The browser receives a streamed answer and inspectable source references.
3. **Private Deep Research:** explicitly admit a local research goal with access
   and provider grants, persist the run, claim work through bounded consumers,
   and execute one Agent with four typed tools. SQLite owns progress, events and
   results, including cancellation and conservative restart outcomes.
4. **Deployment and operating boundaries:** Vercel hosts the frontend; the owner
   runs the Docker API and public ngrok tunnel. Private execution requires its
   own local workspace configuration. Qdrant local and cloud are alternatives.

## Details that matter when reading the arrows

- **Cache lookup follows query embedding.** Only stateless/history-free streaming
  requests are eligible. A hit replays the stored answer and sources, bypassing
  retrieval and generation. The main retrieval path represents a cache miss.
- **Retrieval rank sources execute sequentially.** BM25, dense and optional
  lexical candidates are complementary lists, not a promise of parallel work.
  RRF uses `sum(1 / (60 + rank))`, with rank starting at one. Eligible structured
  matches can be promoted after cross-encoder filtering and before final top-k.
- **Grounding preserves evidence identity.** Source labels, units and periods
  connect the generated answer to evidence. Indexed excerpts and original
  document acquisition/viewer admission are separate capabilities.
- **The application executes Agent tools.** Groq returns a strict structured
  decision; schema, policy and budget checks precede the tool adapter. The tools
  are `search_documents`, `inspect_retrieval`, `read_document` and `ask_rag`.
- **SQLite is authoritative.** Atomic claims and short revisioned writes are
  separate from provider/tool calls. A wake hint accelerates idle admission;
  polling remains the fallback. Uncertain running work becomes interrupted on
  restart instead of automatically replaying possible external effects.
- **Public and private access have different requirements.** Local execution
  checks socket peer, allowed Host, Origin when present, a memory-only bearer
  and capability/provider grants. Public Compose does not provision the private
  SQLite workspace. Local Qdrant uses one API process because its store is locked.

## Technology and source references

| Responsibility | Technology | Source |
|---|---|---|
| SEC acquisition | Python `requests` | [SEC client](../../src/ingestion/sec_client.py) |
| Parse and chunk | BeautifulSoup, lxml, tiktoken; financial-table extraction | [Chunker](../../src/ingestion/chunker.py), [table chunks](../../scripts/add_table_chunks.py) |
| Embeddings | SentenceTransformers, `nomic-ai/nomic-embed-text-v1.5`; pinned revision | [Embedder](../../src/retrieval/embedder.py) |
| Freshness and indexing | Immutable generation manifests, SHA-256, Qdrant cosine vectors | [Generation](../../src/retrieval/embedding_generation.py), [indexing](../../scripts/index_chunks.py) |
| Hybrid retrieval | BM25, Qdrant dense, optional lexical ladder, RRF, MS MARCO MiniLM cross-encoder | [Retriever](../../src/retrieval/hybrid_retriever.py) |
| Cache and context | Semantic cache, scope-aware rendered evidence | [RAG pipeline](../../src/generation/rag_pipeline.py) |
| Grounded generation | Groq; configurable default `openai/gpt-oss-120b` | [Generator](../../src/generation/generator.py) |
| Agent decisions and tools | Strict Pydantic schema, Groq structured output, closed registry | [Provider](../../src/agent/provider.py), [registry](../../src/agent/registry.py) |
| Durable execution | SQLite WAL, revisioned jobs, two process-local consumers by default | [Jobs](../../src/workspace/jobs.py), [worker](../../src/workspace/worker.py) |
| Frontend and deployment | React 19, TypeScript, Vite, Vercel; Docker, Uvicorn, ngrok | [Frontend](../../frontend/package.json), [Compose](../../docker-compose.yml), [setup](../SETUP.md) |
| Private access | Local workspace gate and separate provider consent | [Access](../../src/api/access.py), [Agent service](../../src/agent/durable.py) |

The source review binds to code revision
`db31bbe263708363b37a66ea45ac10be4e1f2470`. The subsequent upstream README-only
commit `f8cf539` was preserved before publication. This is a documentation
change, not a new provider, quality or production capacity evaluation.

## Artifact verification

The interactive overview passed all nine deterministic artifact checks with
zero composition errors or warnings. Automated browser measurements passed at
1440x900, 1600x1000, 1920x1080 and 2048x1320. Light and dark endpoint screenshots
were inspected separately from those automated checks. One browser-layout
correction compacted excess vertical spacing without hiding overflow or shrinking
typography.

- Specification SHA-256: `075c9c3c7501811e4f16feba808813e738889429216afc33c45b7663f4dc9bcf`
- HTML SHA-256: `2ff3c50367e53cddb400810bffad4e89784ff7420c0f5e9e249a9c372232128d`
- HTML size: 744,708 bytes.

The static SVG/PNG receives a separate text-fit, connector and visual review;
the interactive validator does not certify the poster's distinct composition.
Diagnostic screenshots and machine receipts remain local and are not published
as product documentation. Viewer and optional brand-mark notices are available
in [Diagram Viewer Notices](../licenses/DIAGRAM_NOTICES.md).
