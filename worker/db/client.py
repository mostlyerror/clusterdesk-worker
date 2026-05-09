import dataclasses
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from supabase import create_client, Client
from worker.types import Filing, Cluster


class DBClient:
    def __init__(self, url: str, key: str):
        self._sb: Client = create_client(url, key)

    @classmethod
    def from_env(cls) -> "DBClient":
        return cls(
            url=os.environ["SUPABASE_URL"],
            key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )

    def upsert_filings(self, filings: list[Filing]) -> None:
        rows = [
            {
                "filing_date": f.filing_date.isoformat(),
                "trade_date": f.trade_date.isoformat(),
                "ticker": f.ticker,
                "company_name": f.company_name,
                "insider_name": f.insider_name,
                "insider_title": f.insider_title,
                "transaction_code": f.transaction_code,
                "shares": f.shares,
                "price_per_share": float(f.price_per_share),
                "trade_value_usd": f.trade_value_usd,
                "filing_url": f.filing_url,
            }
            for f in filings
        ]
        self._sb.table("filings").upsert(rows, on_conflict="ticker,insider_name,trade_date,shares,price_per_share").execute()

    def upsert_cluster(self, cluster: Cluster) -> None:
        payload = {
            "ticker": cluster.ticker,
            "company_name": cluster.company_name,
            "market_cap_usd": cluster.market_cap_usd,
            "cluster_start_date": cluster.cluster_start_date.isoformat(),
            "cluster_end_date": cluster.cluster_end_date.isoformat(),
            "insider_count": cluster.insider_count,
            "total_value_usd": cluster.total_value_usd,
            "roles": cluster.roles,
            "filings": [
                {k: v.isoformat() if isinstance(v, (date, datetime)) else v
                 for k, v in dataclasses.asdict(f).items()}
                for f in cluster.filings
            ],
        }
        self._sb.table("clusters").upsert(
            {
                "ticker": cluster.ticker,
                "cluster_start_date": cluster.cluster_start_date.isoformat(),
                "cluster_end_date": cluster.cluster_end_date.isoformat(),
                "insider_count": cluster.insider_count,
                "total_value_usd": cluster.total_value_usd,
                "market_cap_usd": cluster.market_cap_usd,
                "score": cluster.score,
                "payload": payload,
            },
            on_conflict="ticker,cluster_end_date",
        ).execute()

    def mark_cluster_published(self, cluster: Cluster, twitter_post_id: Optional[str]) -> None:
        self._sb.table("clusters").update(
            {"published_at": datetime.now(timezone.utc).isoformat(), "twitter_post_id": twitter_post_id}
        ).eq("ticker", cluster.ticker).eq("cluster_end_date", cluster.cluster_end_date.isoformat()).execute()

    def upsert_ticker_page(self, cluster: Cluster) -> None:
        payload = {
            "ticker": cluster.ticker,
            "company_name": cluster.company_name,
            "market_cap_usd": cluster.market_cap_usd,
            "cluster_start_date": cluster.cluster_start_date.isoformat(),
            "cluster_end_date": cluster.cluster_end_date.isoformat(),
            "insider_count": cluster.insider_count,
            "total_value_usd": cluster.total_value_usd,
            "roles": cluster.roles,
            "score": cluster.score,
            "filings": [
                {k: v.isoformat() if isinstance(v, (date, datetime)) else v
                 for k, v in dataclasses.asdict(f).items()}
                for f in cluster.filings
            ],
        }
        self._sb.table("ticker_pages").upsert(
            {
                "ticker": cluster.ticker,
                "cluster_date": cluster.cluster_end_date.isoformat(),
                "payload": payload,
                "score": cluster.score,
            },
            on_conflict="ticker,cluster_date",
        ).execute()

    def get_recently_published_tickers(self, days: int = 30) -> set[str]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = (
            self._sb.table("clusters")
            .select("ticker")
            .gte("published_at", cutoff)
            .execute()
        )
        return {row["ticker"] for row in result.data}

    def get_last_post_times(self) -> dict[str, datetime]:
        result = (
            self._sb.table("clusters")
            .select("ticker,published_at")
            .not_.is_("published_at", "null")
            .order("published_at", desc=True)
            .execute()
        )
        seen: dict[str, datetime] = {}
        for row in result.data:
            if row["ticker"] not in seen:
                seen[row["ticker"]] = datetime.fromisoformat(row["published_at"]).replace(tzinfo=timezone.utc)
        return seen

    def get_market_cap_cache(self, ticker: str) -> Optional[int]:
        result = (
            self._sb.table("market_cap_cache")
            .select("market_cap_usd,fetched_at")
            .eq("ticker", ticker)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        fetched_at = datetime.fromisoformat(row["fetched_at"]).replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - fetched_at).total_seconds() > 86400:
            return None
        return row["market_cap_usd"]

    def set_market_cap_cache(self, ticker: str, market_cap_usd: int) -> None:
        self._sb.table("market_cap_cache").upsert(
            {"ticker": ticker, "market_cap_usd": market_cap_usd, "fetched_at": datetime.now(timezone.utc).isoformat()}
        ).execute()

    def get_email_subscribers(self) -> list[str]:
        result = self._sb.table("email_subscribers").select("email").execute()
        return [row["email"] for row in result.data]

    def get_clusters_published_this_week(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        monday = (now - timedelta(days=now.weekday())).date()
        result = (
            self._sb.table("clusters")
            .select("*")
            .gte("published_at", monday.isoformat())
            .not_.is_("published_at", "null")
            .order("published_at", desc=True)
            .execute()
        )
        return result.data
