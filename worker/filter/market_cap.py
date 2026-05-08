import logging
from typing import Optional
import yfinance as yf
from worker.db.client import DBClient

logger = logging.getLogger(__name__)


def get_market_cap(ticker: str, db: DBClient) -> Optional[int]:
    cached = db.get_market_cap_cache(ticker)
    if cached is not None:
        return cached

    try:
        info = yf.Ticker(ticker).info
        mcap = info.get("marketCap")
        if mcap is not None:
            db.set_market_cap_cache(ticker, int(mcap))
            return int(mcap)
    except Exception as e:
        logger.warning("yfinance failed for %s: %s", ticker, e)

    return None
