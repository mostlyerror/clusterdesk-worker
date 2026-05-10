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

    lines = []
    for c in clusters:
        name = c["payload"]["company_name"]
        ticker = c["ticker"]
        score = c["score"]
        url = f"https://clusterdesk.io/buys/{ticker}"
        lines.append(
            f'<strong><a href="{url}">{ticker}</a></strong> — {name} &nbsp;<span style="color:#22C55E">Score: {score}</span>'
        )
    summary = "<br><br>".join(lines)

    if dry_run:
        logger.info(
            "[DRY_RUN] Would send weekly email to %d subscribers with %d clusters",
            len(subscribers), len(clusters),
        )
        logger.info("Summary:\n%s", summary)
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
                    "dataVariables": {"summary": summary},
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
