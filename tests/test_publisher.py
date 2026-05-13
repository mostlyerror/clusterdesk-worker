from datetime import date, datetime
from unittest.mock import MagicMock, patch
from worker.types import Filing, Cluster
from worker.publisher.twitter import post_to_twitter, _format_tweet
from worker.publisher.ticker_page import publish_ticker_page
from worker.publisher.email_weekly import send_weekly_email, _build_cluster_payload

def make_cluster() -> Cluster:
    f = Filing(
        filing_date=date(2026, 1, 6), trade_date=date(2026, 1, 6),
        ticker="ACME", company_name="Acme Corp", insider_name="Jane",
        insider_title="CEO", transaction_code="P", shares=10000,
        price_per_share=5.5, trade_value_usd=55000,
        shares_owned_after=50000, ownership_change_pct=25.0,
        filing_url="", scraped_at=datetime.now(),
    )
    f2 = Filing(
        filing_date=date(2026, 1, 7), trade_date=date(2026, 1, 7),
        ticker="ACME", company_name="Acme Corp", insider_name="Bob",
        insider_title="CFO", transaction_code="P", shares=8000,
        price_per_share=5.6, trade_value_usd=44800,
        shares_owned_after=20000, ownership_change_pct=66.7,
        filing_url="", scraped_at=datetime.now(),
    )
    return Cluster(
        ticker="ACME", company_name="Acme Corp", market_cap_usd=200_000_000,
        cluster_start_date=date(2026, 1, 6), cluster_end_date=date(2026, 1, 7),
        insider_count=2, filings=[f, f2], total_value_usd=99800,
        roles=["CEO", "CFO"], first_seen_at=datetime.now(), score=75,
    )

def test_format_tweet_contains_ticker():
    c = make_cluster()
    tweet = _format_tweet(c)
    assert "$ACME" in tweet
    assert "Score: 75/100" in tweet
    assert "clusterdesk.io/buys/ACME" in tweet

def test_dry_run_does_not_call_api():
    mock_db = MagicMock()
    mock_db.get_last_post_times.return_value = {}
    with patch("worker.publisher.twitter._can_post", return_value=(True, "")):
        result = post_to_twitter(make_cluster(), db=mock_db, dry_run=True)
    assert result == "dry_run"

def test_ticker_page_dry_run_skips_webhook():
    mock_db = MagicMock()
    publish_ticker_page(make_cluster(), db=mock_db, dry_run=True)
    mock_db.upsert_ticker_page.assert_called_once()

def test_weekly_email_dry_run():
    mock_db = MagicMock()
    mock_db.get_clusters_published_this_week.return_value = [
        {"ticker": "ACME", "score": 75, "payload": {}}
    ]
    send_weekly_email(db=mock_db, dry_run=True)
    mock_db.get_clusters_published_this_week.assert_called_once()

def test_weekly_email_skips_when_no_clusters():
    mock_db = MagicMock()
    mock_db.get_clusters_published_this_week.return_value = []
    send_weekly_email(db=mock_db, dry_run=False)

def test_weekly_email_payload_includes_reason_to_care_fields():
    row = {
        "ticker": "ACME",
        "score": 75,
        "payload": {
            "company_name": "Acme Corp",
            "insider_count": 2,
            "total_value_usd": 125000,
            "market_cap_usd": 200000000,
            "cluster_start_date": "2026-01-06",
            "cluster_end_date": "2026-01-07",
            "roles": ["CEO", "CFO"],
        },
    }

    payload = _build_cluster_payload(row)

    assert payload == {
        "ticker": "ACME",
        "score": 75,
        "company_name": "Acme Corp",
        "insider_count": 2,
        "total_value_usd": 125000,
        "market_cap_usd": 200000000,
        "cluster_start_date": "2026-01-06",
        "cluster_end_date": "2026-01-07",
        "roles": ["CEO", "CFO"],
    }
