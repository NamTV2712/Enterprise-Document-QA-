"""Probe the real discovery search over the on-disk corpus, provider-free.

UI-006 evidence helper: it builds the same BM25 index the retriever builds at
startup (``rank_bm25`` over the index tokenizer) and runs the real
``DiscoveryService`` over the real chunk artifacts, so the shapes recorded here
are production shapes without loading a model, a store, or a provider.

It writes nothing: no corpus, index, evaluation, or workspace state changes.
Run: .venv/Scripts/python.exe scripts/diagnostics/ui006_discovery_probe.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from configs.settings import settings  # noqa: E402
from src.api.discovery import DiscoveryService  # noqa: E402
from src.retrieval.chunk_loader import load_embedded_chunks  # noqa: E402
from src.retrieval.hybrid_retriever import _tokenize  # noqa: E402

QUERIES = ["cloud revenue", "risk factors regarding competition", "supply chain"]


def document_id_of(chunk: dict) -> str:
    accession = chunk.get("accession_number")
    if isinstance(accession, str) and accession:
        return f"{chunk.get('ticker', 'UNKNOWN')}:{accession}"
    return f"{chunk.get('ticker', 'UNKNOWN')}:{chunk.get('filing_date', 'unknown')}"


def catalog_rows(chunks: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for chunk in chunks:
        document_id = document_id_of(chunk)
        row = grouped.setdefault(
            document_id,
            {
                "document_id": document_id,
                "ticker": chunk.get("ticker"),
                "filing_date": chunk.get("filing_date"),
                "report_date": chunk.get("report_date"),
                "accession_number": chunk.get("accession_number"),
                "sections": set(),
                "chunk_count": 0,
                "source_url": None,
            },
        )
        if chunk.get("section"):
            row["sections"].add(chunk["section"])
        row["chunk_count"] += 1
    return [
        {**row, "sections": sorted(row["sections"])}
        for row in sorted(grouped.values(), key=lambda item: item["document_id"])
    ]


def main() -> int:
    chunks = load_embedded_chunks(settings.data_processed_dir)
    print(f"loaded chunks: {len(chunks)}")
    rows = catalog_rows(chunks)
    print(f"catalog documents: {len(rows)}")
    print(f"sections: {sorted({s for row in rows for s in row['sections']})}")
    print(f"tickers: {len({row['ticker'] for row in rows})}")

    bm25 = BM25Okapi([_tokenize(chunk["text"]) for chunk in chunks])
    service = DiscoveryService(
        chunks=lambda: chunks,
        catalog_rows=lambda: rows,
        tokenize=_tokenize,
        score=lambda tokens: [float(score) for score in bm25.get_scores(tokens)],
        document_id_of=document_id_of,
        present=None,
    )

    for query in QUERIES:
        snapshot = service.search(query=query, page=1, page_size=5)
        payload = snapshot.as_payload(1, 5)
        print("\n=== query:", query)
        print("search_id:", payload["search_id"])
        print("total(page units):", payload["total"], "grouping:", payload["grouping"])
        print("scope:", payload["scope"])
        print("facets:", [(f["dimension"], [v for v in f["values"]][:4]) for f in payload["facets"]])
        for item in payload["items"][:2]:
            print("---- item:", json.dumps({
                "document_id": item.get("document_id"),
                "ticker": item.get("ticker"),
                "filing_date": item.get("filing_date"),
                "sections": item.get("sections"),
                "best_score": item.get("best_score"),
                "hit_count": item.get("hit_count"),
                "hits": [
                    {
                        "chunk_id": hit["chunk_id"],
                        "section": hit["section"],
                        "chunk_index": hit["chunk_index"],
                        "score": hit["score"],
                        "snippet": hit["snippet"],
                    }
                    for hit in item.get("hits", [])[:2]
                ],
            }, ensure_ascii=False)[:1200])

    # Cases the UI must render truthfully: no match, a scoped search, chunk
    # grouping, and a page past the first.
    cases = [
        {"query": "zzqqxx nonexistentterm", "page": 1, "page_size": 5},
        {"query": "cloud revenue", "ticker": "AAPL", "year": 2026, "page": 1, "page_size": 5},
        {"query": "supply chain", "group_by": "chunk", "page": 2, "page_size": 5},
        {"query": "supply chain", "group_by": "chunk", "page": 1, "page_size": 5},
    ]
    for case in cases:
        snapshot = service.search(**case)
        payload = snapshot.as_payload(case.get("page", 1), case["page_size"])
        print("\n=== case:", case)
        print("total:", payload["total"], "grouping:", payload["grouping"], "scope:", payload["scope"])
        first = payload["items"][0] if payload["items"] else None
        if first is not None:
            print("first item:", json.dumps(first, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
