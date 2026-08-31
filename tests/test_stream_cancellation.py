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


def _aws_growth_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="AMZN_test_mdna_0",
        ticker="AMZN",
        section="mdna",
        filing_date="2026-02-06",
        score=0.9,
        text=(
            "Year Ended December 31,\n\n2024\n2025\nNet Sales:\nAWS\n"
            "107,556\n128,725\n"
        ),
        citation="AMZN 10-K, MD&A",
    )


AWS_GROWTH_QUESTION = (
    "How does Amazon's AWS segment compare to Microsoft's cloud business "
    "in terms of growth?"
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


def test_applicable_stream_buffers_before_emitting_corrected_answer() -> None:
    generator = Generator.__new__(Generator)
    generator.model = "mock-model"
    generator._call_groq_stream = lambda *args, **kwargs: iter(
        ["AWS grew 20% in 2025 [Source 1]."]
    )
    correction = "AWS net sales were 107,556 in 2024 and 128,725 in 2025 [Source 1]."
    generator._call_groq = MagicMock(return_value=correction)

    tokens = list(
        generator.generate_stream(
            AWS_GROWTH_QUESTION,
            [_aws_growth_chunk()],
        )
    )

    assert tokens == [correction]
    generator._call_groq.assert_called_once()


def test_non_applicable_stream_keeps_original_streaming_path() -> None:
    generator = Generator.__new__(Generator)
    generator.model = "mock-model"
    generator._call_groq_stream = MagicMock(
        return_value=iter(["first", "second"])
    )

    tokens = list(
        generator.generate_stream(
            "What is Apple's business?",
            [_retrieved_chunk()],
        )
    )

    assert tokens == ["first", "second"]
    generator._call_groq_stream.assert_called_once()


def test_direct_generation_applies_one_period_value_correction() -> None:
    generator = Generator.__new__(Generator)
    generator.model = "mock-model"
    generator._call_groq = MagicMock(
        side_effect=[
            "AWS grew 20% in 2025 [Source 1].",
            "AWS net sales were 107,556 in 2024 and 128,725 in 2025 [Source 1].",
        ]
    )

    response = generator.generate(AWS_GROWTH_QUESTION, [_aws_growth_chunk()])

    assert "107,556" in response.answer
    assert "128,725" in response.answer
    assert generator._call_groq.call_count == 2
