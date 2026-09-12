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


def test_vietnamese_comparison_keeps_all_companies_and_adds_only_hints() -> None:
    normalized = normalize_retrieval_question(
        "So sánh doanh thu của Apple và Microsoft năm 2024"
    )

    assert normalized.detected_ticker is None
    assert normalized.translation_method == "lexical_hints"
    assert "Apple" in normalized.question
    assert "Microsoft" in normalized.question
    assert "total revenue" in normalized.question


def test_unaccented_vietnamese_metrics_are_normalized_without_losing_entities() -> None:
    normalized = normalize_retrieval_question(
        "So sanh ty le dich vu cua Apple va Microsoft nam 2024"
    )

    assert normalized.translation_method == "lexical_hints"
    assert "Apple" in normalized.question
    assert "Microsoft" in normalized.question
    assert "share" in normalized.question
    assert "services" in normalized.question


def test_gross_profit_does_not_fall_through_to_net_income() -> None:
    normalized = normalize_retrieval_question(
        "Lợi nhuận gộp của Apple năm 2024 là bao nhiêu?"
    )

    assert normalized.question == "What was Apple's gross profit in 2024?"
    assert "net income" not in normalized.question
    assert normalized.requested_periods == ("2024",)


def test_multiple_periods_are_preserved_instead_of_collapsed() -> None:
    normalized = normalize_retrieval_question(
        "Doanh thu Apple từ 2023 đến 2024 thay đổi thế nào?"
    )

    assert normalized.translation_method == "lexical_hints"
    assert normalized.requested_periods == ("2023", "2024")
    assert "2023" in normalized.question
    assert "2024" in normalized.question
    assert normalized.is_comparative is True


def test_unaccented_comparison_is_not_collapsed_to_one_year() -> None:
    normalized = normalize_retrieval_question(
        "So sanh doanh thu Apple nam 2023 va 2024"
    )

    assert normalized.translation_method == "lexical_hints"
    assert normalized.requested_periods == ("2023", "2024")
    assert "2023" in normalized.question
    assert "2024" in normalized.question
