import threading
from unittest.mock import MagicMock

from src.generation.generator import Generator
from src.generation.rag_pipeline import RAGPipeline
from src.retrieval.retriever import RetrievedChunk


class FakeProviderStream:
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    def __iter__(self):
        return iter(self.chunks)

    def close(self) -> None:
        self.closed = True


def _retrieved_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="AAPL_test_business_0",
        ticker="AAPL",
        section="business",
        filing_date="2025-10-31",
        score=0.9,
        text="Apple business context.",
        citation="AAPL 10-K, Business",
    )


def test_pipeline_stops_without_caching_partial_stream() -> None:
    cancel_event = threading.Event()
    generator = MagicMock()
    generator.model = "mock-model"

    def cancel_after_first_token(*args, **kwargs):
        assert kwargs["cancel_event"] is cancel_event
        yield "first token"
        cancel_event.set()
        yield "stale token"

    generator.generate_stream.side_effect = cancel_after_first_token
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.generator = generator
    pipeline.rewriter = MagicMock()
    pipeline.rewriter.rewrite.return_value = "What is Apple's business?"
    pipeline.retriever = MagicMock()
    pipeline.retriever.embed_query.return_value = [0.1, 0.2]
    pipeline.retriever.retrieve_with_embedding.return_value = [_retrieved_chunk()]
    pipeline.cache = MagicMock()
    pipeline.cache.get.return_value = None
    pipeline.memory = MagicMock()

    events = list(
        pipeline.query_stream(
            question="What is Apple's business?",
            cancel_event=cancel_event,
        )
    )

    assert [event_type for event_type, _ in events] == ["sources", "token"]
    assert events[-1] == ("token", "first token")
    pipeline.cache.set.assert_not_called()
    pipeline.memory.add_turn.assert_not_called()


def test_groq_stream_closes_provider_connection_on_cancel() -> None:
    first_chunk = MagicMock()
    first_chunk.choices[0].delta.content = "first"
    second_chunk = MagicMock()
    second_chunk.choices[0].delta.content = "second"
    provider_stream = FakeProviderStream([first_chunk, second_chunk])
    generator = Generator.__new__(Generator)
    generator.model = "mock-model"
    generator.client = MagicMock()
    generator.client.chat.completions.create.return_value = provider_stream
    cancel_event = threading.Event()

    tokens = generator._call_groq_stream(
        "prompt",
        cancel_event=cancel_event,
    )
    assert next(tokens) == "first"
    cancel_event.set()
    assert list(tokens) == []
    assert provider_stream.closed is True


def test_gemini_stream_closes_provider_connection_on_cancel() -> None:
    first_chunk = MagicMock(text="first")
    second_chunk = MagicMock(text="second")
    provider_stream = FakeProviderStream([first_chunk, second_chunk])
    generator = Generator.__new__(Generator)
    generator.model = "mock-model"
    generator.client = MagicMock()
    generator.client.models.generate_content_stream.return_value = provider_stream
    cancel_event = threading.Event()

    tokens = generator._call_gemini_stream(
        "prompt",
        cancel_event=cancel_event,
    )
    assert next(tokens) == "first"
    cancel_event.set()
    assert list(tokens) == []
    assert provider_stream.closed is True
