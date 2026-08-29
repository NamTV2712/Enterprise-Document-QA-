from scripts.diagnostics.query_shaper_ab import _all_terms_hit, _summarize_results


class _Chunk:
    def __init__(self, chunk_id: str, ticker: str, text: str):
        self.chunk_id = chunk_id
        self.ticker = ticker
        self.text = text


def test_summary_reports_required_terms_and_ticker_leakage() -> None:
    summary = _summarize_results(
        [_Chunk("AMZN_1", "AMZN", "AWS net sales 107,556 128,725")],
        "AMZN", ("107,556", "128,725"),
    )

    assert _all_terms_hit(summary)
    assert not summary["ticker_leakage"]


def test_summary_detects_cross_ticker_result() -> None:
    summary = _summarize_results(
        [_Chunk("MSFT_1", "MSFT", "cloud growth")], "AMZN", ()
    )

    assert summary["ticker_leakage"]
