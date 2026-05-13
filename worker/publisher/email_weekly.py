import os
import logging
import requests
from worker.db.client import DBClient

logger = logging.getLogger(__name__)


def send_weekly_email(db: DBClient, dry_run: bool = False) -> None:
    clusters = db.get_clusters_published_this_week()
    if not clusters:
        logger.info("No clusters published this week — skipping weekly email")
        return

    cluster_data = [_build_cluster_payload(c) for c in clusters]

    if dry_run:
        logger.info(
            "[DRY_RUN] Would send weekly email with %d clusters", len(clusters)
        )
        for c in cluster_data:
            logger.info("  - %s (score %s)", c["ticker"], c["score"])
        return

    web_url = os.environ.get("WEB_BASE_URL", "https://clusterdesk.io")
    secret = os.environ.get("REVALIDATE_SECRET", "")

    if not secret:
        logger.error("REVALIDATE_SECRET not set — cannot send weekly email")
        return

    resp = requests.post(
        f"{web_url}/api/send-weekly",
        json={"clusters": cluster_data},
        headers={"x-revalidate-secret": secret},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info(
        "Weekly email complete: %d sent, %d failed",
        data.get("sent", 0),
        data.get("failed", 0),
    )


def _build_cluster_payload(cluster: dict) -> dict:
    payload = cluster.get("payload") or {}
    return {
        "ticker": cluster["ticker"],
        "score": cluster["score"],
        "company_name": payload.get("company_name", cluster["ticker"]),
        "insider_count": payload.get("insider_count"),
        "total_value_usd": payload.get("total_value_usd"),
        "market_cap_usd": payload.get("market_cap_usd"),
        "cluster_start_date": payload.get("cluster_start_date"),
        "cluster_end_date": payload.get("cluster_end_date"),
        "roles": payload.get("roles", []),
    }
