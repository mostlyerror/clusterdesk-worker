import os
import logging
import requests
from worker.db.client import DBClient

logger = logging.getLogger(__name__)

LOOPS_API_URL = "https://app.loops.so/api/v1/transactional"


def send_weekly_email(db: DBClient, dry_run: bool = False) -> None:
    clusters = db.get_clusters_published_this_week()
    if not clusters:
        logger.info("No clusters published this week — skipping weekly email")
        return

    template_id = os.environ.get("LOOPS_WEEKLY_TEMPLATE_ID", "")
    api_key = os.environ.get("LOOPS_API_KEY", "")

    if dry_run:
        logger.info("[DRY_RUN] Would send weekly email with %d clusters", len(clusters))
        for c in clusters:
            logger.info("  - %s (score %s)", c.get("ticker"), c.get("score"))
        return

    if not template_id or not api_key:
        logger.error("LOOPS_WEEKLY_TEMPLATE_ID or LOOPS_API_KEY not set")
        return

    payload = {
        "transactionalId": template_id,
        "audience": "all",
        "dataVariables": {
            "clusters": [
                {
                    "ticker": c["ticker"],
                    "score": c["score"],
                    "payload": c["payload"],
                }
                for c in clusters
            ]
        },
    }

    resp = requests.post(
        LOOPS_API_URL,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    resp.raise_for_status()
    logger.info("Weekly email sent: %d clusters", len(clusters))
