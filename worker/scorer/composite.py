from worker.types import Cluster

ROLE_WEIGHTS = {
    "CEO": 15, "CFO": 12, "President": 12, "COO": 10,
    "Director": 5, "10% Owner": 8,
}


def score_cluster(cluster: Cluster) -> int:
    score = 0

    # Cluster size (max 30)
    score += min(cluster.insider_count * 10, 30)

    # Total $ value vs market cap (max 25)
    if cluster.market_cap_usd > 0:
        pct_of_mcap = cluster.total_value_usd / cluster.market_cap_usd
        score += min(int(pct_of_mcap * 10_000), 25)

    # Role seniority (max 25)
    score += min(sum(ROLE_WEIGHTS.get(r, 3) for r in cluster.roles), 25)

    # Recency tightness (max 10)
    span_days = (cluster.cluster_end_date - cluster.cluster_start_date).days
    score += max(10 - span_days * 2, 0)

    # Largest single trade size (max 10)
    biggest = max(f.trade_value_usd for f in cluster.filings)
    score += min(biggest // 50_000, 10)

    return min(score, 100)
