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

    cluster_data = [
        {
            "ticker": c["ticker"],
            "score": c["score"],
            "company_name": c["payload"]["company_name"],
        }
        for c in clusters
    ]

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
