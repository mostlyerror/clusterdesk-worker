from unittest.mock import MagicMock, patch
from datetime import date, datetime
from worker.db.client import DBClient
from worker.types import Filing, Cluster

@patch("worker.db.client.create_client")
def test_upsert_filing(mock_create_client):
    mock_sb = MagicMock()
    mock_create_client.return_value = mock_sb
    mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [{"id": 1}]

    client = DBClient(url="https://x.supabase.co", key="service_key")
    f = Filing(
        filing_date=date(2026, 1, 10), trade_date=date(2026, 1, 8),
        ticker="ACME", company_name="Acme Corp", insider_name="Jane",
        insider_title="CEO", transaction_code="P", shares=10000,
        price_per_share=5.5, trade_value_usd=55000,
        shares_owned_after=50000, ownership_change_pct=25.0,
        filing_url="https://sec.gov/1", scraped_at=datetime.now(),
    )
    client.upsert_filings([f])
    mock_sb.table.assert_called_with("filings")

@patch("worker.db.client.create_client")
def test_get_recent_published_tickers(mock_create_client):
    mock_sb = MagicMock()
    mock_create_client.return_value = mock_sb
    mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = [
        {"ticker": "ACME"}
    ]
    client = DBClient(url="https://x.supabase.co", key="service_key")
    result = client.get_recently_published_tickers(days=30)
    assert "ACME" in result
