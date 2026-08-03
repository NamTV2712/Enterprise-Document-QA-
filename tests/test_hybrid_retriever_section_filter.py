import threading

from src.retrieval.hybrid_retriever import HybridRetriever


class FakeBM25:
    def __init__(self, chunk_count: int):
        self.chunk_count = chunk_count

    def get_scores(self, tokens):
        return [1.0] * self.chunk_count


class FakeStore:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks

    def search(self, query_vector, top_k, ticker=None, section=None):
        return [
            {"chunk_id": chunk["chunk_id"]}
            for chunk in self.chunks
            if (ticker is None or chunk["ticker"] == ticker)
            and (section is None or chunk["section"] == section)
        ][:top_k]


class FakeCrossEncoder:
    def predict(self, pairs, **kwargs):
        return [1.0] * len(pairs)


def _build_retriever() -> HybridRetriever:
    chunks = [
        {
            "chunk_id": "AAPL_financial_table",
            "ticker": "AAPL",
            "section": "financial_table",
            "filing_date": "2025-01-01",
            "text": (
                "### Consolidated Balance Sheets\n"
                "| Metric | 2025 | 2024 |\n"
                "|---|---|---|\n"
                "| Assets - Total assets | 359,241 | 364,980 |"
            ),
        },
        {
            "chunk_id": "AAPL_financial_statements",
            "ticker": "AAPL",
            "section": "financial_statements",
            "filing_date": "2025-01-01",
            "text": "Apple financial statement discussion.",
        },
        {
            "chunk_id": "MSFT_auditor_signature",
            "ticker": "MSFT",
            "section": "financial_statements",
            "filing_date": "2025-01-01",
            "text": (
                "/s/ Deloitte & Touche LLP\n"
                "We have served as Microsoft's auditor since 1983."
            ),
        },
        {
            "chunk_id": "MSFT_financial_table",
            "ticker": "MSFT",
            "section": "financial_table",
            "filing_date": "2025-01-01",
            "text": "| Metric | 2025 | 2024 |\n| Revenue | 1 | 2 |",
        },
    ]
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever._all_chunks = chunks
    retriever._chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    retriever._chunk_index_map = {
        chunk["chunk_id"]: index for index, chunk in enumerate(chunks)
    }
    retriever.bm25 = FakeBM25(len(chunks))
    retriever.store = FakeStore(chunks)
    retriever.cross_encoder = FakeCrossEncoder()
    retriever._model_lock = threading.Lock()
    return retriever


def test_total_assets_query_respects_financial_statements_section_filter():
    retriever = _build_retriever()

    results = retriever.retrieve_with_embedding(
        query="What was Apple's total assets?",
        query_embedding=[0.1, 0.2],
        ticker="AAPL",
        section="financial_statements",
        top_k=5,
    )

    assert results
    assert {chunk.section for chunk in results} == {"financial_statements"}


def test_auditor_query_respects_financial_table_section_filter():
    retriever = _build_retriever()

    results = retriever.retrieve_with_embedding(
        query="Who audited Microsoft's financial statements?",
        query_embedding=[0.1, 0.2],
        ticker="MSFT",
        section="financial_table",
        top_k=5,
    )

    assert results
    assert {chunk.section for chunk in results} == {"financial_table"}


def test_total_assets_query_without_section_filter_still_uses_structured_match():
    retriever = _build_retriever()

    results = retriever.retrieve_with_embedding(
        query="What was Apple's total assets?",
        query_embedding=[0.1, 0.2],
        ticker="AAPL",
        section=None,
        top_k=5,
    )

    assert results[0].chunk_id == "AAPL_financial_table"
    assert results[0].score == 10.0
