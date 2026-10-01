"""Registered provider-free bilingual query matrix.

The expected signals are authored here rather than produced by the query
normalizer under test.  The matrix is intentionally small enough to run in
every offline suite while covering language, period, entity, ambiguity, and
scope paths.
"""

from __future__ import annotations

import unicodedata


_CASES = [
    ("revenue", "What was Apple's total revenue in 2024?", "Tổng doanh thu của Apple trong năm 2024 là bao nhiêu?", "AAPL", ("revenue", "2024")),
    ("gross-profit", "What was Microsoft's gross profit in 2023?", "Lợi nhuận gộp của Microsoft trong năm 2023 là bao nhiêu?", "MSFT", ("gross profit", "2023")),
    ("operating-income", "Compare operating income for 2023 and 2024 at Apple.", "So sánh lợi nhuận hoạt động của Apple trong năm 2023 và 2024.", "AAPL", ("operating income", "2023", "2024")),
    ("net-income", "What was Amazon's net income in 2024?", "Lợi nhuận ròng của Amazon năm 2024 là bao nhiêu?", "AMZN", ("net income", "2024")),
    ("assets", "What total assets did Google report in 2024?", "Google báo cáo tổng tài sản bao nhiêu trong năm 2024?", "GOOGL", ("assets", "2024")),
    ("liabilities", "What liabilities did Meta report in 2024?", "Meta báo cáo nợ phải trả bao nhiêu trong năm 2024?", "META", ("liabilities", "2024")),
    ("equity", "What was Nvidia's shareholders' equity in 2024?", "Vốn chủ sở hữu của Nvidia trong năm 2024 là bao nhiêu?", "NVDA", ("equity", "2024")),
    ("cash-flow", "What operating cash flow did Tesla report in 2024?", "Tesla báo cáo dòng tiền từ hoạt động kinh doanh bao nhiêu năm 2024?", "TSLA", ("operating cash flow", "2024")),
    ("revenue-growth", "How did revenue grow from 2023 to 2024 at Apple?", "Doanh thu của Apple tăng thế nào từ 2023 đến 2024?", "AAPL", ("revenue", "2023", "2024")),
    ("profit-growth", "Did Microsoft's gross profit increase from 2023 to 2024?", "Lợi nhuận gộp của Microsoft có tăng từ 2023 đến 2024 không?", "MSFT", ("gross profit", "2023", "2024")),
    ("share", "What share of revenue came from Services at Apple?", "Services chiếm tỷ trọng doanh thu bao nhiêu ở Apple?", "AAPL", ("revenue share",)),
    ("dependency", "Which company depends more on cloud revenue, Microsoft or Apple?", "Microsoft hay Apple phụ thuộc nhiều hơn vào doanh thu cloud?", "MSFT", ("revenue share", "MSFT", "AAPL")),
    ("risk", "What are all major risks Microsoft discloses?", "Microsoft công bố tất cả nhóm rủi ro chính nào?", "MSFT", ("risk",)),
    ("cyber-risk", "What cybersecurity risks does Amazon disclose?", "Amazon công bố rủi ro an ninh mạng nào?", "AMZN", ("cybersecurity",)),
    ("competition", "What competition risk does Apple disclose?", "Apple công bố rủi ro cạnh tranh nào?", "AAPL", ("competition",)),
    ("regulatory", "What regulatory risks does Meta disclose?", "Meta công bố rủi ro pháp lý nào?", "META", ("regulatory",)),
    ("business", "Summarize Apple's business overview.", "Tóm tắt tổng quan hoạt động kinh doanh của Apple.", "AAPL", ("business",)),
    ("mdna", "What explains Microsoft's revenue change in MD&A?", "MD&A giải thích thay đổi doanh thu của Microsoft thế nào?", "MSFT", ("revenue", "MD&A")),
    ("financials", "Show the financial statement evidence for Amazon.", "Cho xem bằng chứng báo cáo tài chính của Amazon.", "AMZN", ("financial statements",)),
    ("source-audit", "Which sources support Apple's revenue answer?", "Nguồn nào hỗ trợ câu trả lời doanh thu của Apple?", "AAPL", ("revenue", "source")),
    ("unknown-period", "What revenue is reported without assuming a fiscal period?", "Doanh thu nào được nêu mà không tự đoán kỳ tài chính?", "AAPL", ("revenue", "unknown period")),
    ("missing-year", "Do we have evidence for Apple's 2022 revenue?", "Có bằng chứng doanh thu Apple năm 2022 không?", "AAPL", ("revenue", "2022")),
    ("negative", "Did revenue decline, not increase, at Tesla?", "Doanh thu của Tesla giảm chứ không tăng phải không?", "TSLA", ("revenue", "decline")),
    ("filter-conflict", "Compare Apple and Microsoft while filtering only AAPL.", "So sánh Apple và Microsoft khi bộ lọc chỉ có AAPL.", "AAPL", ("comparison", "filter conflict")),
    ("listing", "List the main revenue families disclosed by Microsoft.", "Liệt kê các nhóm doanh thu chính Microsoft công bố.", "MSFT", ("revenue", "list")),
    ("qualify", "What can the supplied excerpts establish about Apple Services?", "Các đoạn trích đã cung cấp xác lập được gì về Apple Services?", "AAPL", ("Services", "bounded")),
    ("period-label", "Use fiscal year 2024, not filing year, for Apple's revenue.", "Dùng năm tài chính 2024, không phải năm nộp hồ sơ, cho doanh thu Apple.", "AAPL", ("revenue", "FY2024")),
    ("currency", "What currency and scale apply to Apple's Services value?", "Giá trị Services của Apple dùng tiền tệ và quy mô nào?", "AAPL", ("Services", "currency", "scale")),
    ("denominator", "What denominator is used for Microsoft's revenue share?", "Mẫu số nào được dùng cho tỷ trọng doanh thu của Microsoft?", "MSFT", ("revenue share", "denominator")),
    ("footnote", "Does the footnote change the reported revenue value?", "Chú thích có thay đổi giá trị doanh thu được báo cáo không?", "AAPL", ("revenue", "footnote")),
    ("table-row", "Use the total revenue row, not the adjacent Services row.", "Dùng dòng tổng doanh thu, không dùng dòng Services kế bên.", "AAPL", ("revenue", "row")),
    ("growth-rate", "What is the reported revenue growth rate?", "Tỷ lệ tăng trưởng doanh thu được báo cáo là bao nhiêu?", "MSFT", ("growth rate",)),
    ("market-share", "Does the filing disclose market share?", "Hồ sơ có công bố thị phần không?", "MSFT", ("market share",)),
    ("auditor", "Who audited Apple's financial statements?", "Ai kiểm toán báo cáo tài chính của Apple?", "AAPL", ("auditor",)),
    ("segments", "What business segments does Honeywell report?", "Honeywell báo cáo các phân khúc kinh doanh nào?", "HON", ("segments",)),
    ("international", "What international risks are disclosed?", "Những rủi ro quốc tế nào được công bố?", "MSFT", ("international",)),
    ("out-of-corpus", "What is the filing's view on a non-existent company?", "Hồ sơ nói gì về một công ty không có trong corpus?", "", ("insufficient evidence",)),
    ("follow-up", "How does that compare with the prior year?", "Điều đó so với năm trước như thế nào?", "AAPL", ("follow-up",)),
    ("language", "Answer this revenue question in Vietnamese.", "Trả lời câu hỏi doanh thu này bằng tiếng Việt.", "AAPL", ("answer language",)),
    ("format", "Return the answer as a concise table with citations.", "Trả lời dưới dạng bảng ngắn gọn kèm citation.", "AAPL", ("format", "citation")),
]


def _without_diacritics(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d").replace("Đ", "D")


WORKSPACE_QUERY_MATRIX = tuple(
    {
        "id": f"{case_id}-{variant}",
        "case_id": case_id,
        "variant": variant,
        "language": "en" if variant == "en" else "vi",
        "accented": variant != "vi-unaccented",
        "query": query if variant == "en" else (vi_query if variant == "vi" else _without_diacritics(vi_query)),
        "ticker": ticker or None,
        "expected_signals": signals,
    }
    for case_id, query, vi_query, ticker, signals in _CASES
    for variant in ("en", "vi", "vi-unaccented")
)
