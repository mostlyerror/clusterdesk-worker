import responses as resp_mock
from pathlib import Path
from worker.scraper.openinsider import scrape_openinsider
from worker.types import Filing

CLUSTER_BUYS_HTML = (Path(__file__).parent / "fixtures" / "cluster_buys.html").read_text()
INSIDER_PURCHASES_HTML = (Path(__file__).parent / "fixtures" / "insider_purchases.html").read_text()


@resp_mock.activate
def test_scrape_returns_filings():
    resp_mock.add(resp_mock.GET, "http://openinsider.com/latest-cluster-buys",
                  body=CLUSTER_BUYS_HTML, status=200)
    resp_mock.add(resp_mock.GET, "http://openinsider.com/latest-insider-purchases-25k",
                  body=INSIDER_PURCHASES_HTML, status=200)
    filings = scrape_openinsider()
    assert len(filings) > 0
    assert all(isinstance(f, Filing) for f in filings)


@resp_mock.activate
def test_scrape_deduplicates():
    # Use same HTML for both URLs — should deduplicate
    resp_mock.add(resp_mock.GET, "http://openinsider.com/latest-cluster-buys",
                  body=CLUSTER_BUYS_HTML, status=200)
    resp_mock.add(resp_mock.GET, "http://openinsider.com/latest-insider-purchases-25k",
                  body=CLUSTER_BUYS_HTML, status=200)
    filings = scrape_openinsider()
    keys = [(f.ticker, f.insider_name, str(f.trade_date), f.shares) for f in filings]
    assert len(keys) == len(set(keys)), "Duplicate filings found"


@resp_mock.activate
def test_scrape_returns_empty_on_no_table():
    resp_mock.add(resp_mock.GET, "http://openinsider.com/latest-cluster-buys",
                  body="<html><body>No data</body></html>", status=200)
    resp_mock.add(resp_mock.GET, "http://openinsider.com/latest-insider-purchases-25k",
                  body="<html><body>No data</body></html>", status=200)
    filings = scrape_openinsider()
    assert filings == []
