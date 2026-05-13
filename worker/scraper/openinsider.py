"""Scraper for OpenInsider insider filing data."""

import logging
import random
import re
import time
from datetime import date, datetime, timezone
from typing import Optional

import requests
import sentry_sdk
from bs4 import BeautifulSoup

from worker.types import Filing

logger = logging.getLogger(__name__)

BASE_URL = "http://openinsider.com"
URLS = [
    f"{BASE_URL}/latest-insider-purchases-25k?fd=2",
]

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

# Column indices for latest-insider-purchases-25k table
# [0]=X [1]=FilingDate [2]=TradeDate [3]=Ticker [4]=Company
# [5]=InsiderName [6]=Title [7]=TradeType [8]=Price
# [9]=Qty [10]=Owned [11]=ΔOwn [12]=Value
COL_FILING_DATE = 1
COL_TRADE_DATE = 2
COL_TICKER = 3
COL_COMPANY_NAME = 4
COL_INSIDER_NAME = 5
COL_TITLE = 6
COL_TRADE_TYPE = 7
COL_PRICE = 8
COL_QTY = 9
COL_OWNED = 10
COL_DELTA_OWN = 11
COL_VALUE = 12


def _fetch_html(url: str) -> str:
    """Fetch URL with retry (3x, exponential backoff)."""
    ua = random.choice(USER_AGENTS)
    headers = {"User-Agent": ua}
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            if attempt == 2:
                logger.error("Failed to fetch %s after 3 attempts: %s", url, exc)
                raise
            wait = 2 ** attempt
            logger.warning("Fetch attempt %d failed for %s: %s — retrying in %ds",
                           attempt + 1, url, exc, wait)
            time.sleep(wait)
    return ""  # unreachable


def _clean_number(text: str) -> str:
    """Strip currency signs, commas, +/- prefixes, % suffix."""
    return re.sub(r"[$,+%]", "", text).strip()


def _parse_int(text: str) -> Optional[int]:
    """Parse integer from a possibly formatted string like '+28,429' or '1,050,908'."""
    cleaned = _clean_number(text).lstrip("-").replace("-", "")
    # Handle negative values: '-' at start means negative
    negative = text.strip().startswith("-")
    if not cleaned:
        return None
    try:
        value = int(cleaned)
        return -value if negative else value
    except ValueError:
        return None


def _parse_float(text: str) -> Optional[float]:
    """Parse float from a possibly formatted string like '$204.52'."""
    cleaned = _clean_number(text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(text: str) -> Optional[date]:
    """Parse a date from strings like '2026-05-07' or '2026-05-08 11:57:36'."""
    text = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


_TITLE_CODES = {
    "4": "10% Owner",
    "10": "10% Owner",
    "D": "Director",
    "O": "Officer",
    "DO": "Dir & Officer",
    "OD": "Dir & Officer",
    "H": "Officer, Dir & 10% Owner",
    "": "Unknown",
}


def _normalize_title(raw: str) -> str:
    """Map SEC Form 4 relationship codes to readable strings."""
    return _TITLE_CODES.get(raw.strip(), raw.strip()) or "Unknown"


def _parse_table(html: str) -> list[Filing]:
    """Parse the tinytable from OpenInsider HTML into a list of Filing objects."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="tinytable")
    if table is None:
        return []

    rows = table.find_all("tr")
    filings: list[Filing] = []
    scraped_at = datetime.now(timezone.utc)

    for row in rows[1:]:  # skip header row
        cells = row.find_all("td")
        if len(cells) < 13:
            continue

        try:
            # --- Filing date & URL ---
            filing_date_cell = cells[COL_FILING_DATE]
            filing_date = _parse_date(filing_date_cell.get_text(strip=True))
            if filing_date is None:
                continue

            filing_url = ""
            link = filing_date_cell.find("a", href=True)
            if link:
                href = link["href"]
                filing_url = href if href.startswith("http") else f"{BASE_URL}{href}"

            # --- Trade date ---
            trade_date = _parse_date(cells[COL_TRADE_DATE].get_text(strip=True))
            if trade_date is None:
                continue

            # --- Ticker & company ---
            ticker = cells[COL_TICKER].get_text(strip=True)
            company_name = cells[COL_COMPANY_NAME].get_text(strip=True)
            if not ticker:
                continue

            # --- Insider name & title ---
            insider_name = cells[COL_INSIDER_NAME].get_text(strip=True)
            insider_title = _normalize_title(cells[COL_TITLE].get_text(strip=True))

            # --- Transaction code ---
            trade_type_text = cells[COL_TRADE_TYPE].get_text(strip=True)
            # Format: "P - Purchase" → extract just the code
            transaction_code = trade_type_text.split(" - ")[0].strip() if " - " in trade_type_text else trade_type_text

            # --- Price ---
            price_text = cells[COL_PRICE].get_text(strip=True)
            price_per_share = _parse_float(price_text)
            if price_per_share is None:
                price_per_share = 0.0

            # --- Qty (shares) ---
            qty_text = cells[COL_QTY].get_text(strip=True)
            shares = _parse_int(qty_text)
            if shares is None:
                continue

            # --- Shares owned after ---
            owned_text = cells[COL_OWNED].get_text(strip=True)
            shares_owned_after = _parse_int(owned_text)

            # --- Ownership change % ---
            delta_text = cells[COL_DELTA_OWN].get_text(strip=True)
            delta_cleaned = _clean_number(delta_text)
            try:
                ownership_change_pct = float(delta_cleaned) if delta_cleaned else None
            except ValueError:
                ownership_change_pct = None

            # --- Trade value ---
            value_text = cells[COL_VALUE].get_text(strip=True)
            trade_value = _parse_int(value_text)
            if trade_value is None:
                trade_value = 0

            filing = Filing(
                filing_date=filing_date,
                trade_date=trade_date,
                ticker=ticker,
                company_name=company_name,
                insider_name=insider_name,
                insider_title=insider_title,
                transaction_code=transaction_code,
                shares=shares,
                price_per_share=price_per_share,
                trade_value_usd=trade_value,
                shares_owned_after=shares_owned_after,
                ownership_change_pct=ownership_change_pct,
                filing_url=filing_url,
                scraped_at=scraped_at,
            )
            filings.append(filing)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping unparseable row: %s", exc)
            continue

    return filings


def scrape_openinsider() -> list[Filing]:
    """Scrape OpenInsider and return deduplicated Filing list."""
    all_filings: list[Filing] = []

    for url in URLS:
        try:
            html = _fetch_html(url)
        except requests.RequestException:
            logger.error("Skipping URL %s due to repeated fetch failure", url)
            continue

        filings = _parse_table(html)
        logger.info("Fetched %d filings from %s", len(filings), url)
        all_filings.extend(filings)

    # Deduplicate by (ticker, insider_name, trade_date, shares)
    seen: set[tuple] = set()
    deduped: list[Filing] = []
    for f in all_filings:
        key = (f.ticker, f.insider_name, str(f.trade_date), f.shares)
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    logger.info("Total filings after dedup: %d (from %d raw)", len(deduped), len(all_filings))

    if len(deduped) < 5:
        msg = (
            f"OpenInsider scraper returned only {len(deduped)} filings — "
            "possible HTML structure change."
        )
        logger.warning(msg)
        sentry_sdk.capture_message(msg, level="warning")

    return deduped
