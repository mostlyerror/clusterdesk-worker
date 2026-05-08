from datetime import date, datetime
from worker.types import Filing, Cluster

def test_filing_fields():
    f = Filing(
        filing_date=date(2026, 1, 10),
        trade_date=date(2026, 1, 8),
        ticker="ACME",
        company_name="Acme Corp",
        insider_name="Jane Smith",
        insider_title="CEO",
        transaction_code="P",
        shares=10000,
        price_per_share=5.50,
        trade_value_usd=55000,
        shares_owned_after=50000,
        ownership_change_pct=25.0,
        filing_url="https://www.sec.gov/Archives/...",
        scraped_at=datetime(2026, 1, 10, 9, 0),
    )
    assert f.ticker == "ACME"
    assert f.trade_value_usd == 55000

def test_cluster_total_value():
    f1 = Filing(
        filing_date=date(2026, 1, 10), trade_date=date(2026, 1, 8),
        ticker="ACME", company_name="Acme Corp", insider_name="Jane Smith",
        insider_title="CEO", transaction_code="P", shares=10000,
        price_per_share=5.50, trade_value_usd=55000,
        shares_owned_after=50000, ownership_change_pct=25.0,
        filing_url="https://sec.gov/1", scraped_at=datetime.now(),
    )
    f2 = Filing(
        filing_date=date(2026, 1, 11), trade_date=date(2026, 1, 9),
        ticker="ACME", company_name="Acme Corp", insider_name="Bob Jones",
        insider_title="CFO", transaction_code="P", shares=8000,
        price_per_share=5.60, trade_value_usd=44800,
        shares_owned_after=20000, ownership_change_pct=66.7,
        filing_url="https://sec.gov/2", scraped_at=datetime.now(),
    )
    c = Cluster(
        ticker="ACME", company_name="Acme Corp", market_cap_usd=200_000_000,
        cluster_start_date=date(2026, 1, 8), cluster_end_date=date(2026, 1, 9),
        insider_count=2, filings=[f1, f2],
        total_value_usd=99800, roles=["CEO", "CFO"],
        first_seen_at=datetime.now(), score=0,
    )
    assert c.insider_count == 2
    assert c.total_value_usd == 99800
