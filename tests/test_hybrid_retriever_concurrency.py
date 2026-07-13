import threading
import time

from src.retrieval.hybrid_retriever import HybridRetriever


class FakeBM25:
    def get_scores(self, tokens):
        return [1.0]


class FakeStore:
    def search(self, query_vector, top_k, ticker=None, section=None):
        return [{"chunk_id": "chunk-1"}]


class SlowCrossEncoder:
    def __init__(self):
        self.call_order = []

    def predict(self, pairs):
        call_id = pairs[0][0]
        self.call_order.append(f"start-{call_id}")
        time.sleep(0.05)
        self.call_order.append(f"end-{call_id}")
        return [1.0]


def make_retriever() -> HybridRetriever:
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.embedder = None
    retriever.store = FakeStore()
    retriever.device = "cpu"
    retriever._all_chunks = [
        {
            "chunk_id": "chunk-1",
            "ticker": "AAPL",
            "section": "business",
            "filing_date": "2024-11-01",
            "text": "Apple business overview",
        }
    ]
    retriever._chunks_by_id = {"chunk-1": retriever._all_chunks[0]}
    retriever._chunk_index_map = {"chunk-1": 0}
    retriever.bm25 = FakeBM25()
    retriever.cross_encoder = SlowCrossEncoder()
    retriever._model_lock = threading.Lock()
    return retriever


def test_model_lock_serializes_concurrent_retrieve_with_embedding_calls():
    retriever = make_retriever()

    def retrieve(call_id: str):
        retriever.retrieve_with_embedding(
            query=call_id,
            query_embedding=[0.1, 0.2],
            top_k=1,
            ticker="AAPL",
            section="business",
        )

    t1 = threading.Thread(target=retrieve, args=("1",))
    t2 = threading.Thread(target=retrieve, args=("2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert retriever.cross_encoder.call_order in (
        ["start-1", "end-1", "start-2", "end-2"],
        ["start-2", "end-2", "start-1", "end-1"],
    )
