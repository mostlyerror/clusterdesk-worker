import os
import logging
import requests
from worker.types import Cluster
from worker.db.client import DBClient

logger = logging.getLogger(__name__)


def publish_ticker_page(cluster: Cluster, db: DBClient, dry_run: bool = False) -> None:
    db.upsert_ticker_page(cluster)
    logger.info("Upserted ticker_page for %s", cluster.ticker)

    if dry_run:
        logger.info("[DRY_RUN] Would trigger ISR revalidation for %s", cluster.ticker)
        return

    _trigger_revalidation(cluster.ticker)


def _trigger_revalidation(ticker: str) -> None:
    url = os.environ.get("REVALIDATE_WEBHOOK_URL", "")
    secret = os.environ.get("REVALIDATE_SECRET", "")
    if not url:
        logger.warning("REVALIDATE_WEBHOOK_URL not set — skipping ISR trigger")
        return
    try:
        resp = requests.post(
            url,
            json={"path": f"/buys/{ticker}"},
            headers={"x-revalidate-secret": secret},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("ISR revalidation triggered for /buys/%s", ticker)
    except Exception as e:
        logger.warning("ISR revalidation failed for %s: %s", ticker, e)
