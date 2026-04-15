#!/usr/bin/env python3
"""
Main news monitoring orchestrator - SCOUT Phase 2
Runs as Claude Code Routine (every 6 hours)

Enhanced with:
- Real-time Bluesky monitoring
- Optional AI summaries (Google Gemini/Groq free tiers)
- Advanced analytics and trending
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.news_sources import NewsSourceAggregator
from src.filter import FilterEngine
from src.state import StateManager
from src.telegram_client import TelegramNotifier
from src.bluesky_source import BlueskyJetstreamMonitor
from src.summarizer import SummarizerEngine
from src.analytics import AnalyticsEngine
from src.deduplicator import DeduplicatorEngine
from src.retry_handler import RetryHandler
from src.cache_manager import CacheManager
from src.additional_sources import AdditionalSources
from src.webhook_handler import WebhookHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('monitor.log')
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Main orchestration function - Phase 2 Enhanced"""
    try:
        logger.info("=" * 70)
        logger.info("🚀 SCOUT News Monitor Starting (Phase 2)")
        logger.info(f"Run time: {datetime.utcnow().isoformat()}Z")
        logger.info("=" * 70)

        # Initialize components
        state = StateManager(Path("data/processed_news.json"))
        logger.info(f"[STATE] Loaded: {state.state['run_count']} previous runs")

        analytics = AnalyticsEngine(Path("data/stats.json"))
        logger.info("[ANALYTICS] Initialized")

        # API keys from environment
        api_keys = {
            "newsapi_key": os.getenv("NEWSAPI_KEY", ""),
            "claude_api_key": os.getenv("CLAUDE_API_KEY", ""),
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        }

        # Initialize news sources
        sources = NewsSourceAggregator(api_keys=api_keys)
        logger.info("[SOURCES] News aggregator initialized")

        # Initialize Bluesky real-time monitor
        bluesky = BlueskyJetstreamMonitor()
        logger.info("[SOURCES] Bluesky Jetstream initialized")

        # Initialize summarizer (optional)
        summarizer = SummarizerEngine(
            provider="gemini" if api_keys.get("gemini_api_key") else None,
            api_key=api_keys.get("gemini_api_key")
        )
        if summarizer.enabled:
            logger.info("[SUMMARY] Google Gemini enabled")
        else:
            logger.info("[SUMMARY] Summarization disabled (no GEMINI_API_KEY)")

        # Initialize deduplicator, retry handler, cache, and additional sources
        deduplicator = DeduplicatorEngine(similarity_threshold=0.85)
        retrier = RetryHandler(max_retries=3, base_delay=1.0)
        cache = CacheManager(Path("data/cache"))
        additional = AdditionalSources()
        webhook = WebhookHandler()

        logger.info("[DEDUP] Semantic deduplicator initialized")
        logger.info("[RETRY] Exponential backoff retry enabled (3 attempts)")
        logger.info("[CACHE] Smart caching enabled")

        # Fetch news from all sources in PARALLEL
        logger.info("[FETCH] Starting comprehensive news fetch from 8+ sources in parallel...")
        all_articles, sources_checked = await sources.fetch_all()

        # Add Bluesky articles (real-time) with retry
        logger.info("[BLUESKY] Fetching Bluesky posts...")
        bluesky_articles = await retrier.execute_with_retry(
            bluesky.fetch_recent_posts
        ) or []
        all_articles.extend(bluesky_articles)
        if bluesky_articles:
            sources_checked.append("Bluesky")

        # Add additional sources (Product Hunt, Dev.to, GitHub trending)
        logger.info("[SOURCES] Fetching Product Hunt, Dev.to, GitHub trending...")
        additional_articles, additional_sources = await additional.fetch_all_additional()
        all_articles.extend(additional_articles)
        sources_checked.extend(additional_sources)

        logger.info(
            f"[FETCH] ✓ Fetched {len(all_articles)} total articles "
            f"from {len(sources_checked)} sources"
        )

        if not all_articles:
            logger.warning("⚠️ No articles fetched from any source")
            return

        # Semantic deduplication (remove near-duplicates from same batch)
        logger.info("[DEDUP-BATCH] Running semantic deduplication...")
        deduplicated = deduplicator.find_duplicates(all_articles)
        logger.info(
            f"[DEDUP-BATCH] ✓ Removed {len(all_articles) - len(deduplicated)} "
            f"near-duplicates"
        )

        # Filter and rank articles
        filter_engine = FilterEngine(threshold=0.5)
        filtered_articles = filter_engine.filter_and_rank(deduplicated)
        logger.info(
            f"[FILTER] ✓ Filtered to {len(filtered_articles)} "
            f"high-quality articles"
        )

        # Get new articles (not processed before, with state dedup)
        new_articles = state.get_new_articles(filtered_articles)
        logger.info(f"[DEDUP-STATE] ✓ Found {len(new_articles)} new articles to send")

        # Add summaries if enabled
        if summarizer.enabled and new_articles:
            logger.info("[SUMMARY] Adding summaries to top articles...")
            for article in new_articles[:10]:  # Summarize top 10
                summary = summarizer.summarize(
                    article.get("content", article.get("title", ""))
                )
                if summary:
                    article["summary"] = summary
                    logger.debug(f"  ✓ Summarized: {article['title'][:50]}...")

        # Update statistics
        state.update_stats(sources_checked, len(new_articles))
        analytics.record_run(len(all_articles), len(new_articles),
                           sources_checked, new_articles)

        # Prepare Telegram notification
        notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", "")
        )

        if new_articles:
            # Categorize articles
            categorized = filter_engine.categorize(new_articles)
            logger.info(
                f"[FORMAT] Categorized: "
                f"{', '.join(f'{k}:{len(v)}' for k, v in categorized.items() if v)}"
            )

            # Format and send digest
            digest = notifier.format_digest(categorized)
            logger.info("[TELEGRAM] Sending digest...")

            if notifier.send_digest(digest):
                logger.info(f"✓ Telegram notification sent with {len(new_articles)} articles")
            else:
                logger.error("✗ Failed to send Telegram notification")

            # Send analytics summary weekly (if run count is multiple of 28)
            if state.state['run_count'] % 28 == 0:
                analytics_summary = analytics.get_summary()
                notifier.send_digest(analytics_summary)
                logger.info("📊 Weekly analytics summary sent")
        else:
            logger.info("ℹ️ No new articles to send this run")

        # Save state
        state.save()
        logger.info(
            f"[STATE] ✓ Saved: "
            f"{len(state.state['processed_articles'])} total articles tracked"
        )

        logger.info("=" * 70)
        logger.info("✅ Monitor completed successfully")
        logger.info(f"Next run in 6 hours")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR: {e}", exc_info=True)

        # Try to send comprehensive error alert to Telegram
        try:
            notifier = TelegramNotifier(
                bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
                chat_id=os.getenv("TELEGRAM_CHAT_ID", "")
            )

            # Include error context
            error_msg = f"""
💥 SCOUT Monitor Failed

Error: {str(e)[:150]}
Time: {datetime.utcnow().isoformat()}Z

Check logs at: claude.ai/code/routines
Next attempt: 6 hours
"""
            notifier.send_error_alert(error_msg.strip())
            logger.info("✓ Error alert sent to Telegram")

        except Exception as alert_error:
            logger.error(f"Failed to send error alert: {alert_error}")

        # In cloud environment, exit cleanly (let Routine see error in logs)
        logger.info("=" * 70)
        logger.error("MONITOR FAILED - Check logs above for details")
        logger.info("=" * 70)
        # Don't raise - let Routine capture the error in its transcript
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())



if __name__ == "__main__":
    asyncio.run(main())
