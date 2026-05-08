from datetime import date, datetime
from worker.types import Filing, Cluster
from worker.cluster.detect import detect_clusters

def make_filing(ticker, name, trade_date, value=55000, title="CEO") -> Filing:
    return Filing(
        filing_date=trade_date, trade_date=trade_date,
        ticker=ticker, company_name=f"{ticker} Corp", insider_name=name,
        insider_title=title, transaction_code="P", shares=10000,
        price_per_share=5.50, trade_value_usd=value,
        shares_owned_after=50000, ownership_change_pct=25.0,
        filing_url="https://sec.gov/1", scraped_at=datetime.now(),
    )

def test_two_insiders_form_cluster():
    filings = [
        make_filing("ACME", "Jane Smith", date(2026, 1, 6)),
        make_filing("ACME", "Bob Jones", date(2026, 1, 8)),
    ]
    clusters = detect_clusters(filings)
    assert len(clusters) == 1
    assert clusters[0].ticker == "ACME"
    assert clusters[0].insider_count == 2

def test_single_insider_not_a_cluster():
    filings = [make_filing("ACME", "Jane Smith", date(2026, 1, 6))]
    clusters = detect_clusters(filings)
    assert clusters == []

def test_insiders_outside_5_day_window_not_clustered():
    filings = [
        make_filing("ACME", "Jane Smith", date(2026, 1, 1)),
        make_filing("ACME", "Bob Jones", date(2026, 1, 10)),
    ]
    clusters = detect_clusters(filings)
    assert clusters == []

def test_combined_value_below_100k_excluded():
    filings = [
        make_filing("ACME", "Jane Smith", date(2026, 1, 6), value=40000),
        make_filing("ACME", "Bob Jones", date(2026, 1, 7), value=40000),
    ]
    clusters = detect_clusters(filings)
    assert clusters == []

def test_different_tickers_not_clustered():
    filings = [
        make_filing("ACME", "Jane Smith", date(2026, 1, 6)),
        make_filing("WXYZ", "Bob Jones", date(2026, 1, 6)),
    ]
    clusters = detect_clusters(filings)
    assert clusters == []

def test_cluster_roles_populated():
    filings = [
        make_filing("ACME", "Jane Smith", date(2026, 1, 6), title="CEO"),
        make_filing("ACME", "Bob Jones", date(2026, 1, 7), title="CFO"),
    ]
    clusters = detect_clusters(filings)
    assert "CEO" in clusters[0].roles
    assert "CFO" in clusters[0].roles
