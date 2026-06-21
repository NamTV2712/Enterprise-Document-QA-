from src.ingestion.sec_client import SECEdgarClient

def test_get_cik_apple():
    client = SECEdgarClient(user_agent="Li Back cauvang2172@gmail.com")
    assert client.get_cik("AAPL") == 320193