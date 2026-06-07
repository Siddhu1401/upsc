import logging
import sys
import time
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

from src.scraper import scrape_all_feeds
from src.filter import filter_batch
from src.analyzer import analyze_batch
from src.database import save_articles

ARTICLE_CAP = 10000
BATCH_SIZE = 10

def run():
    log.info("=== UPSC Dashboard Pipeline START ===")

    # Phase 1 — Ingestion
    log.info("Phase 1: Scraping RSS feeds...")
    raw_articles = scrape_all_feeds()
    
    # HARD CAP
    raw_articles = raw_articles[:ARTICLE_CAP]
    log.info(f"Scraped {len(raw_articles)} raw articles (capped at {ARTICLE_CAP}).")

    if not raw_articles:
        log.warning("No articles scraped. Aborting pipeline.")
        return

    # Phase 2+3 — Hybrid Funnel
    log.info("Phase 2+3: Running hybrid funnel (deterministic filter → fast analysis)...")
    enriched_articles = []
    total_batches = (len(raw_articles) + BATCH_SIZE - 1) // BATCH_SIZE

    processed_count = 0

    for i in range(0, len(raw_articles), BATCH_SIZE):
        batch = raw_articles[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1

        # The Filter Gate (No API, instant)
        relevance_flags = filter_batch(batch, batch_num)

        # Conditional Analysis
        relevant_articles = []
        prev_count = processed_count
        
        for article, is_relevant in zip(batch, relevance_flags):
            processed_count += 1
            if is_relevant:
                relevant_articles.append(article)
                
        # Each model self-throttles — no extra sleep needed here

        batch_enriched_count = 0
        if relevant_articles:
            # Analyze all relevant articles from this batch in ONE single API call
            enriched_chunk = analyze_batch(relevant_articles)
            if enriched_chunk:
                enriched_articles.extend(enriched_chunk)
                batch_enriched_count = len(enriched_chunk)
        
        # Batch Logging
        flags_str = "[" + ", ".join(["T" if flag else "F" for flag in relevance_flags]) + "]"
        log.info(f"Batch {batch_num}/{total_batches}: Filtered {flags_str} | Enriched: {batch_enriched_count}")

        # Models self-throttle — no extra gap needed


    log.info(f"Funnel complete — {len(enriched_articles)} articles fully enriched.")

    if not enriched_articles:
        log.warning("No enriched articles to save. Aborting pipeline.")
        return

    # Phase 4 — Persistence
    log.info("Phase 4: Persisting to database...")
    total_in_db = save_articles(enriched_articles)
    log.info(f"Database updated. Total live articles: {total_in_db}.")

    log.info("=== UPSC Dashboard Pipeline COMPLETE ===")

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log.critical(f"Pipeline failed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)
