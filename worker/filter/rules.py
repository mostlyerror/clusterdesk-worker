import logging
from worker.types import Filing
from worker.db.client import DBClient
from worker.filter.market_cap import get_market_cap
from worker.filter.sec_footnote import is_10b5_1_plan

logger = logging.getLogger(__name__)

LOCKED_FILTERS = {
    "transaction_code": ["P"],
    "min_trade_value_usd": 25_000,
    "min_share_price": 2.00,
    "min_market_cap_usd": 50_000_000,
    "max_market_cap_usd": 500_000_000,
}


def apply_filters(filings: list[Filing], db: DBClient) -> list[Filing]:
    passed = []
    for f in filings:
        reason = _reject_reason(f, db)
        if reason:
            logger.debug("DROP %s/%s: %s", f.ticker, f.insider_name, reason)
        else:
            passed.append(f)
    logger.info("Filter: %d/%d filings passed", len(passed), len(filings))
    return passed


def _reject_reason(f: Filing, db: DBClient) -> str:
    if f.transaction_code not in LOCKED_FILTERS["transaction_code"]:
        return f"transaction_code={f.transaction_code}"
    if f.trade_value_usd < LOCKED_FILTERS["min_trade_value_usd"]:
        return f"trade_value_usd={f.trade_value_usd}"
    if f.price_per_share < LOCKED_FILTERS["min_share_price"]:
        return f"price_per_share={f.price_per_share}"

    mcap = get_market_cap(f.ticker, db=db)
    if mcap is None:
        return "market_cap_unavailable"
    if mcap < LOCKED_FILTERS["min_market_cap_usd"]:
        return f"market_cap={mcap} below min"
    if mcap > LOCKED_FILTERS["max_market_cap_usd"]:
        return f"market_cap={mcap} above max"

    if is_10b5_1_plan(f.filing_url):
        return "10b5-1 plan detected"

    return ""
