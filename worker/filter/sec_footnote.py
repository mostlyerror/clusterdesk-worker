import logging
import time
import requests

logger = logging.getLogger(__name__)
PLAN_KEYWORDS = ("10b5-1", "rule 10b5-1", "10b5–1")


def is_10b5_1_plan(filing_url: str) -> bool:
    if not filing_url:
        return False
    try:
        time.sleep(0.5)
        resp = requests.get(
            filing_url,
            headers={"User-Agent": "ClusterDesk research@clusterdesk.io"},
            timeout=10,
        )
        resp.raise_for_status()
        text = resp.text.lower()
        return any(kw in text for kw in PLAN_KEYWORDS)
    except Exception as e:
        logger.warning("Could not fetch SEC filing %s: %s — not excluding", filing_url, e)
        return False
