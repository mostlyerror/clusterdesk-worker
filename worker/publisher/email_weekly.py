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

    subscribers = db.get_email_subscribers()
    if not subscribers:
        logger.info("No subscribers — skipping weekly email")
        return

    template_id = os.environ.get("LOOPS_WEEKLY_TEMPLATE_ID", "")
    api_key = os.environ.get("LOOPS_API_KEY", "")

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
            "[DRY_RUN] Would send weekly email to %d subscribers with %d clusters",
            len(subscribers), len(clusters),
        )
        for c in cluster_data:
            logger.info("  - %s (score %s)", c["ticker"], c["score"])
        return

    if not template_id or not api_key:
        logger.error("LOOPS_WEEKLY_TEMPLATE_ID or LOOPS_API_KEY not set")
        return

    sent = failed = 0
    for email in subscribers:
        try:
            resp = requests.post(
                LOOPS_API_URL,
                json={
                    "transactionalId": template_id,
                    "email": email,
                    "dataVariables": {"clusters": cluster_data},
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            resp.raise_for_status()
            sent += 1
        except Exception as exc:
            logger.warning("Failed to send weekly email to %s: %s", email, exc)
            failed += 1

    logger.info("Weekly email sent to %d/%d subscribers", sent, sent + failed)
