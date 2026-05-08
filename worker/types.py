from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Filing:
    filing_date: date
    trade_date: date
    ticker: str
    company_name: str
    insider_name: str
    insider_title: str
    transaction_code: str
    shares: int
    price_per_share: float
    trade_value_usd: int
    shares_owned_after: Optional[int]
    ownership_change_pct: Optional[float]
    filing_url: str
    scraped_at: datetime


@dataclass
class Cluster:
    ticker: str
    company_name: str
    market_cap_usd: int
    cluster_start_date: date
    cluster_end_date: date
    insider_count: int
    filings: list[Filing]
    total_value_usd: int
    roles: list[str]
    first_seen_at: datetime
    score: int = 0
