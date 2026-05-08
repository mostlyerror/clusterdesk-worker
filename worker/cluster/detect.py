import logging
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
from worker.types import Filing, Cluster

logger = logging.getLogger(__name__)

WINDOW_DAYS = 5
MIN_INSIDERS = 2
MIN_COMBINED_VALUE = 100_000


def _trading_day_span(start: date, end: date) -> int:
    """Count trading days (Mon–Fri) between two dates, inclusive."""
    if start > end:
        start, end = end, start
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


def detect_clusters(filings: list[Filing]) -> list[Cluster]:
    by_ticker: dict[str, list[Filing]] = defaultdict(list)
    for f in filings:
        by_ticker[f.ticker].append(f)

    clusters = []
    for ticker, ticker_filings in by_ticker.items():
        ticker_filings.sort(key=lambda f: f.trade_date)
        cluster = _find_best_cluster(ticker, ticker_filings)
        if cluster:
            clusters.append(cluster)

    logger.info("Detected %d clusters from %d filings", len(clusters), len(filings))
    return clusters


def _find_best_cluster(ticker: str, filings: list[Filing]) -> Cluster | None:
    best: list[Filing] | None = None

    for anchor in filings:
        window = [
            f for f in filings
            if f.trade_date >= anchor.trade_date
            and _trading_day_span(anchor.trade_date, f.trade_date) <= WINDOW_DAYS
        ]
        distinct_insiders = len({f.insider_name for f in window})
        total_value = sum(f.trade_value_usd for f in window)

        if distinct_insiders >= MIN_INSIDERS and total_value >= MIN_COMBINED_VALUE:
            if best is None or distinct_insiders > len({f.insider_name for f in best}):
                best = window

    if best is None:
        return None

    return Cluster(
        ticker=ticker,
        company_name=best[0].company_name,
        market_cap_usd=0,  # enriched in main.py after detection
        cluster_start_date=min(f.trade_date for f in best),
        cluster_end_date=max(f.trade_date for f in best),
        insider_count=len({f.insider_name for f in best}),
        filings=best,
        total_value_usd=sum(f.trade_value_usd for f in best),
        roles=list({f.insider_title for f in best}),
        first_seen_at=datetime.now(timezone.utc),
    )
