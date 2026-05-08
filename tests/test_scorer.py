from datetime import date, datetime
from worker.types import Filing, Cluster
from worker.scorer.composite import score_cluster

def make_cluster(insiders=2, total_value=120_000, market_cap=200_000_000,
                 roles=None, span_days=1, biggest_trade=80_000) -> Cluster:
    if roles is None:
        roles = ["CEO", "CFO"]
    filings = [
        Filing(
            filing_date=date(2026, 1, 6), trade_date=date(2026, 1, 6),
            ticker="ACME", company_name="Acme", insider_name=f"Person {i}",
            insider_title=roles[i % len(roles)], transaction_code="P",
            shares=1000, price_per_share=10.0,
            trade_value_usd=biggest_trade if i == 0 else (total_value - biggest_trade) // max(insiders - 1, 1),
            shares_owned_after=5000, ownership_change_pct=10.0,
            filing_url="", scraped_at=datetime.now(),
        )
        for i in range(insiders)
    ]
    return Cluster(
        ticker="ACME", company_name="Acme Corp", market_cap_usd=market_cap,
        cluster_start_date=date(2026, 1, 6),
        cluster_end_date=date(2026, 1, 6 + span_days),
        insider_count=insiders, filings=filings,
        total_value_usd=total_value, roles=roles,
        first_seen_at=datetime.now(),
    )

def test_score_is_bounded_0_to_100():
    c = make_cluster(insiders=10, total_value=5_000_000, roles=["CEO", "CFO", "President"])
    assert 0 <= score_cluster(c) <= 100

def test_more_insiders_scores_higher():
    c2 = make_cluster(insiders=2)
    c3 = make_cluster(insiders=3)
    assert score_cluster(c3) > score_cluster(c2)

def test_higher_value_pct_scores_higher():
    low = make_cluster(total_value=100_000, market_cap=200_000_000)
    high = make_cluster(total_value=500_000, market_cap=200_000_000)
    assert score_cluster(high) > score_cluster(low)

def test_senior_roles_score_higher():
    directors = make_cluster(roles=["Director", "Director"])
    executives = make_cluster(roles=["CEO", "CFO"])
    assert score_cluster(executives) > score_cluster(directors)

def test_tighter_window_scores_higher():
    tight = make_cluster(span_days=1)
    loose = make_cluster(span_days=4)
    assert score_cluster(tight) > score_cluster(loose)
