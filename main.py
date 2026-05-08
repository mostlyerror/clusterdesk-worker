import logging
import os
from datetime import datetime

import sentry_sdk
import typer
from dotenv import load_dotenv

load_dotenv()

sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN", ""), traces_sample_rate=0.0)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = typer.Typer()


def _build_db():
    from worker.db.client import DBClient
    return DBClient.from_env()


@app.command()
def pipeline(dry_run: bool = typer.Option(None)):
    """Run the full daily pipeline: scrape → filter → cluster → score → publish."""
    from worker.scraper.openinsider import scrape_openinsider
    from worker.filter.rules import apply_filters
    from worker.cluster.detect import detect_clusters
    from worker.scorer.composite import score_cluster
    from worker.publisher.ticker_page import publish_ticker_page
    from worker.publisher.twitter import post_to_twitter

    if dry_run is None:
        dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    min_score = int(os.environ.get("MIN_SCORE_THRESHOLD", "60"))

    db = _build_db()

    filings = scrape_openinsider()
    filtered = apply_filters(filings, db=db)
    db.upsert_filings(filtered)

    clusters = detect_clusters(filtered)

    # Enrich clusters with market cap (already cached in DB from filter step)
    for c in clusters:
        c.market_cap_usd = db.get_market_cap_cache(c.ticker) or 0

    recently_published = db.get_recently_published_tickers(days=30)
    new_clusters = [c for c in clusters if c.ticker not in recently_published]

    scored = []
    for c in new_clusters:
        c.score = score_cluster(c)
        scored.append(c)

    top = sorted(scored, key=lambda c: c.score, reverse=True)[:3]
    qualifying = [c for c in top if c.score >= min_score]

    logging.info("%d qualifying clusters (score ≥ %d)", len(qualifying), min_score)

    for cluster in qualifying:
        publish_ticker_page(cluster, db=db, dry_run=dry_run)
        post_id = post_to_twitter(cluster, db=db, dry_run=dry_run)
        db.upsert_cluster(cluster)
        if post_id and post_id != "dry_run":
            db.mark_cluster_published(cluster, twitter_post_id=post_id)
        elif not dry_run:
            pass  # post was rate-limited, cluster saved but not marked published


@app.command()
def preview():
    """Run pipeline in DRY_RUN mode — no posts, no emails."""
    typer.echo("Running in DRY_RUN mode (no posts, no emails)")
    os.environ["DRY_RUN"] = "true"
    pipeline(dry_run=True)


@app.command()
def backfill(days: int = typer.Option(14, help="Number of days to backfill")):
    """Backfill filings from the last N days into the database."""
    typer.echo(f"Backfilling last {days} days (no publishing)")
    from worker.scraper.openinsider import scrape_openinsider
    from worker.filter.rules import apply_filters

    db = _build_db()
    filings = scrape_openinsider()
    filtered = apply_filters(filings, db=db)
    db.upsert_filings(filtered)
    typer.echo(f"Backfilled {len(filtered)} filtered filings")


@app.command(name="weekly-email")
def weekly_email(dry_run: bool = typer.Option(None)):
    """Send the weekly digest email via Loops."""
    from worker.publisher.email_weekly import send_weekly_email

    if dry_run is None:
        dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    db = _build_db()
    send_weekly_email(db=db, dry_run=dry_run)


@app.command(name="weekly-email-preview")
def weekly_email_preview():
    """Preview the weekly digest to stdout."""
    os.environ["DRY_RUN"] = "true"
    weekly_email(dry_run=True)


if __name__ == "__main__":
    app()
