from unittest.mock import MagicMock

from src.memory.query_rewriter import QueryRewriter


def _make_mock_generator(provider: str = "groq", rewrite_response: str = "rewritten query"):
    """Create a fake Generator with the Groq response shape used by QueryRewriter."""
    mock_generator = MagicMock()
    mock_generator.provider = provider
    mock_generator.model = "fake-model"

    mock_message = MagicMock()
    mock_message.content = rewrite_response
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_generator.client.chat.completions.create.return_value = mock_response

    return mock_generator


def test_no_history_returns_original_query_unchanged() -> None:
    """The first question in a session must not spend an LLM rewrite call."""
    mock_generator = _make_mock_generator()
    rewriter = QueryRewriter(mock_generator)

    result = rewriter.rewrite("What are Apple's risks?", history_messages=[])

    assert result == "What are Apple's risks?"
    mock_generator.client.chat.completions.create.assert_not_called()


def test_with_history_calls_llm_and_returns_rewritten_query() -> None:
    mock_generator = _make_mock_generator(rewrite_response="What is Apple's total revenue?")
    rewriter = QueryRewriter(mock_generator)
    history = [
        {"role": "user", "content": "What are Apple's risks?"},
        {"role": "assistant", "content": "Apple faces competition..."},
    ]

    result = rewriter.rewrite("What about their revenue?", history_messages=history)

    assert result == "What is Apple's total revenue?"
    mock_generator.client.chat.completions.create.assert_called_once()


def test_llm_failure_falls_back_to_original_query() -> None:
    """Rewrite failures must not crash the RAG pipeline."""
    mock_generator = _make_mock_generator()
    mock_generator.client.chat.completions.create.side_effect = Exception("API timeout")
    rewriter = QueryRewriter(mock_generator)
    history = [
        {"role": "user", "content": "prev Q"},
        {"role": "assistant", "content": "prev A"},
    ]

    result = rewriter.rewrite("What about their revenue?", history_messages=history)

    assert result == "What about their revenue?"


def test_empty_llm_response_falls_back_to_original_query() -> None:
    """Do not pass an empty rewritten query into retrieval."""
    mock_generator = _make_mock_generator(rewrite_response="")
    rewriter = QueryRewriter(mock_generator)
    history = [
        {"role": "user", "content": "Q"},
        {"role": "assistant", "content": "A"},
    ]

    result = rewriter.rewrite("What about their revenue?", history_messages=history)

    assert result == "What about their revenue?"


def test_history_truncated_to_last_two_turns_in_prompt() -> None:
    """Only the last four messages should be sent to control rewrite token cost."""
    mock_generator = _make_mock_generator(rewrite_response="rewritten")
    rewriter = QueryRewriter(mock_generator)
    long_history = []
    for index in range(6):
        long_history.append({"role": "user", "content": f"Q{index}"})
        long_history.append({"role": "assistant", "content": f"A{index}"})

    rewriter.rewrite("follow-up question", history_messages=long_history)

    call_args = mock_generator.client.chat.completions.create.call_args
    sent_messages = call_args.kwargs["messages"]
    user_prompt = sent_messages[-1]["content"]

    assert "Q5" in user_prompt
    assert "A5" in user_prompt
    assert "Q4" in user_prompt
    assert "A4" in user_prompt
    assert "Q0" not in user_prompt
    assert "A0" not in user_prompt
