#!/usr/bin/env python3
"""
Main news monitoring orchestrator
Runs as Claude Code Routine (every 6 hours)
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
    """Main orchestration function"""
    try:
        logger.info("=" * 60)
        logger.info("AI News Monitor Starting")
        logger.info(f"Run time: {datetime.utcnow().isoformat()}Z")
        logger.info("=" * 60)

        # Initialize components
        state = StateManager(Path("data/processed_news.json"))
        logger.info(f"Loaded state: {state.state['run_count']} previous runs")

        # API keys from environment
        api_keys = {
            "newsapi_key": os.getenv("NEWSAPI_KEY", ""),
            "claude_api_key": os.getenv("CLAUDE_API_KEY", ""),
        }

        # Initialize news sources
        sources = NewsSourceAggregator(api_keys=api_keys)
        logger.info("News source aggregator initialized")

        # Fetch news from all sources
        logger.info("Fetching news from all sources...")
        all_articles, sources_checked = await sources.fetch_all()
        logger.info(f"Fetched {len(all_articles)} articles from {len(sources_checked)} sources")

        if not all_articles:
            logger.warning("No articles fetched from any source")
            return

        # Filter and rank articles
        filter_engine = FilterEngine(threshold=0.5)
        filtered_articles = filter_engine.filter_and_rank(all_articles)
        logger.info(f"Filtered to {len(filtered_articles)} high-quality articles")

        # Get new articles (not processed before)
        new_articles = state.get_new_articles(filtered_articles)
        logger.info(f"Found {len(new_articles)} new articles to send")

        # Update statistics
        state.update_stats(sources_checked, len(new_articles))

        # Prepare Telegram notification
        notifier = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", "")
        )

        if new_articles:
            # Categorize articles
            categorized = filter_engine.categorize(new_articles)
            logger.info(f"Categorized articles: {[f'{k}:{len(v)}' for k, v in categorized.items() if v]}")

            # Format and send digest
            digest = notifier.format_digest(categorized)
            logger.info("Formatted digest, sending via Telegram...")

            if notifier.send_digest(digest):
                logger.info(f"✓ Telegram notification sent with {len(new_articles)} articles")
            else:
                logger.error("Failed to send Telegram notification")
        else:
            logger.info("No new articles to send")

        # Save state
        state.save()
        logger.info(f"State saved: {len(state.state['processed_articles'])} total articles tracked")

        logger.info("=" * 60)
        logger.info("Monitor completed successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}", exc_info=True)

        # Try to send error alert
        try:
            notifier = TelegramNotifier(
                bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
                chat_id=os.getenv("TELEGRAM_CHAT_ID", "")
            )
            notifier.send_error_alert(f"Monitor failed: {str(e)}")
        except Exception as alert_error:
            logger.error(f"Failed to send error alert: {alert_error}")

        raise


if __name__ == "__main__":
    asyncio.run(main())
