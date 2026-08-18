from src.retrieval.query_normalizer import detect_ticker, normalize_retrieval_question


def test_detect_ticker_requires_one_unambiguous_company() -> None:
    assert detect_ticker("What was Tesla's revenue?") == "TSLA"
    assert detect_ticker("Compare Apple and Microsoft revenue") is None


def test_vietnamese_revenue_query_is_translated_for_retrieval() -> None:
    normalized = normalize_retrieval_question(
        "Doanh thu của Tesla năm 2024 là bao nhiêu?"
    )

    assert normalized.detected_ticker == "TSLA"
    assert normalized.translated_from_vietnamese is True
    assert normalized.question == "What was Tesla's total revenue in 2024?"


def test_unknown_vietnamese_intent_is_not_guessed() -> None:
    question = "Tesla đang đối mặt với vấn đề gì?"

    assert normalize_retrieval_question(question).question == question
