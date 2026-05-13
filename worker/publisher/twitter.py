import os
import logging
from datetime import datetime, timedelta, timezone, date

import tweepy

from worker.types import Cluster
from worker.db.client import DBClient

logger = logging.getLogger(__name__)

CT_OFFSET = timedelta(hours=-5)   # Central Time (approximate — good enough for posting window)
POST_WINDOW_START = 9             # 9 AM CT
POST_WINDOW_END = 16              # 4 PM CT
MIN_SPACING_MINUTES = 90
MAX_DAILY_POSTS = int(os.environ.get("MAX_DAILY_POSTS", "3"))
POST_COOLDOWN_DAYS = 7


def _format_tweet(cluster: Cluster) -> str:
    span = (cluster.cluster_end_date - cluster.cluster_start_date).days + 1
    lines = [
        "🚨 Cluster buy alert",
        "",
        f"${cluster.ticker} · {cluster.company_name}",
        f"Market cap: ${cluster.market_cap_usd // 1_000_000}M",
        "",
        f"{cluster.insider_count} insiders bought ${cluster.total_value_usd:,.0f} over {span} days:",
    ]
    for f in cluster.filings:
        lines.append(f"• {f.insider_title}: ${f.trade_value_usd:,.0f}")
    lines += [
        "",
        f"Score: {cluster.score}/100",
        "",
        f"Full details → clusterdesk.io/buys/{cluster.ticker}",
    ]
    return "\n".join(lines)


def _can_post(cluster: Cluster, db: DBClient) -> tuple[bool, str]:
    last_post_times = db.get_last_post_times()

    if cluster.ticker in last_post_times:
        days_ago = (datetime.now(timezone.utc) - last_post_times[cluster.ticker]).days
        if days_ago < POST_COOLDOWN_DAYS:
            return False, f"posted {days_ago}d ago (cooldown {POST_COOLDOWN_DAYS}d)"

    today_posts = sum(
        1 for posted_at in last_post_times.values()
        if posted_at.date() == datetime.now(timezone.utc).date()
    )
    if today_posts >= MAX_DAILY_POSTS:
        return False, f"daily limit reached ({today_posts}/{MAX_DAILY_POSTS})"

    now_ct = datetime.now(timezone.utc) + CT_OFFSET
    if not (POST_WINDOW_START <= now_ct.hour < POST_WINDOW_END):
        return False, f"outside posting window ({now_ct.hour}:xx CT)"

    if last_post_times:
        most_recent = max(last_post_times.values())
        minutes_since = (datetime.now(timezone.utc) - most_recent).total_seconds() / 60
        if minutes_since < MIN_SPACING_MINUTES:
            return False, f"only {minutes_since:.0f}m since last post (min {MIN_SPACING_MINUTES}m)"

    return True, ""


def post_to_twitter(cluster: Cluster, db: DBClient, dry_run: bool = False) -> str | None:
    tweet_text = _format_tweet(cluster)

    if dry_run:
        logger.info("[DRY_RUN] Would post:\n%s", tweet_text)
        return "dry_run"

    can, reason = _can_post(cluster, db)
    if not can:
        logger.info("Skipping %s tweet: %s", cluster.ticker, reason)
        return None

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    response = client.create_tweet(text=tweet_text)
    post_id = str(response.data["id"])
    logger.info("Posted tweet %s for %s", post_id, cluster.ticker)
    return post_id
