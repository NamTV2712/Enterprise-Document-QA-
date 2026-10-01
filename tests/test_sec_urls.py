from src.api.sec_urls import sanitize_sec_browser_url


def test_allows_only_https_sec_archive_sources() -> None:
    assert sanitize_sec_browser_url(
        "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/"
    ) == "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/"
    assert sanitize_sec_browser_url(
        "https://www.sec.gov:443/Archives/edgar/data/320193/filing.htm#item1"
    ) == "https://www.sec.gov:443/Archives/edgar/data/320193/filing.htm#item1"


def test_rejects_other_hosts_paths_and_url_authority_tricks() -> None:
    unsafe = [
        "http://www.sec.gov/Archives/edgar/data/1/filing.htm",
        "https://sec.gov/Archives/edgar/data/1/filing.htm",
        "https://evil.sec.gov/Archives/edgar/data/1/filing.htm",
        "https://www.sec.gov.evil.test/Archives/edgar/data/1/filing.htm",
        "https://data.sec.gov/submissions/CIK0000320193.json",
        "https://www.sec.gov/files/company_tickers.json",
        "https://www.sec.gov/Archives/example",
        "https://user:pass@www.sec.gov/Archives/edgar/data/1/filing.htm",
        "https://www.sec.gov:8443/Archives/edgar/data/1/filing.htm",
        "not a URL",
    ]
    assert all(sanitize_sec_browser_url(value) is None for value in unsafe)
