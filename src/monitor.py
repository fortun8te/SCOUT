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
from src.discord_client import DiscordNotifier
from src.bluesky_source import BlueskyJetstreamMonitor
from src.summarizer import SummarizerEngine
from src.analytics import AnalyticsEngine
from src.deduplicator import DeduplicatorEngine
from src.retry_handler import RetryHandler
from src.cache_manager import CacheManager
from src.additional_sources import AdditionalSources
from src.webhook_handler import WebhookHandler
from src.bot_status import BotStatusManager
from src.quality_checker import QualityChecker

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
    bot_manager = None
    try:
        logger.info("=" * 70)
        logger.info("SCOUT News Monitor Starting")
        logger.info(f"Run time: {datetime.utcnow().isoformat()}Z")
        logger.info("=" * 70)

        # Connect bot in background to maintain DND status
        bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
        if bot_token:
            try:
                bot_manager = BotStatusManager(bot_token)
                await bot_manager.connect_and_wait()
            except Exception as e:
                logger.warning(f"[BOT] Connection failed: {e} (continuing anyway)")
                bot_manager = None

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

        # Skip low-quality additional sources (Product Hunt, Dev.to, GitHub trending are marketing/spam)
        # Comment this out to add them back if needed
        # logger.info("[SOURCES] Fetching Product Hunt, Dev.to, GitHub trending...")
        # additional_articles, additional_sources = await additional.fetch_all_additional()
        # all_articles.extend(additional_articles)
        # sources_checked.extend(additional_sources)

        logger.info(
            f"[FETCH] ✓ Fetched {len(all_articles)} total articles "
            f"from {len(sources_checked)} sources"
        )

        if not all_articles:
            logger.warning("⚠️ No articles fetched from any source")
            # Even if APIs fail, try to send something
            logger.info("Attempting fallback: will try to send cache or placeholder")
            # Could send analytics or error summary instead
            try:
                notifier = DiscordNotifier(
                    bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
                    user_id=os.getenv("DISCORD_USER_ID", "")
                )
                fallback_msg = (
                    f"**SCOUT Status Update**\n\n"
                    f"No articles found in this run at "
                    f"{datetime.utcnow().isoformat(timespec='seconds')}Z.\n"
                    f"All news sources may be temporarily unavailable or rate-limited.\n"
                    f"Next run in ~6 hours — will retry all sources automatically."
                )
                notifier.send_digest(fallback_msg)
            except:
                pass
            return

        # Semantic deduplication (remove near-duplicates from same batch)
        logger.info("[DEDUP-BATCH] Running semantic deduplication...")
        deduplicated = deduplicator.find_duplicates(all_articles)
        logger.info(
            f"[DEDUP-BATCH] ✓ Removed {len(all_articles) - len(deduplicated)} "
            f"near-duplicates"
        )

        # Filter and rank articles (strict - only quality news)
        filter_engine = FilterEngine(threshold=0.35)
        filtered_articles = filter_engine.filter_and_rank(deduplicated)
        logger.info(
            f"[FILTER] ✓ Filtered to {len(filtered_articles)} "
            f"high-quality articles"
        )

        # Quality assurance - remove BS/garbage
        quality_checker = QualityChecker()
        quality_articles = quality_checker.filter_articles(filtered_articles)
        logger.info(
            f"[QUALITY] ✓ {len(quality_articles)} articles passed quality checks"
        )
        filtered_articles = quality_articles

        # Get new articles (not processed before, with state dedup)
        new_articles = state.get_new_articles(filtered_articles)
        logger.info(f"[DEDUP-STATE] ✓ Found {len(new_articles)} new articles to send")

        # Progressive fallback — always try to send SOMETHING
        if len(new_articles) == 0:
            logger.warning("[SAFETY] Zero new articles after state dedup. Engaging progressive fallback...")

            # Tier 1: Lower filter threshold to 0.25 (still strict)
            loose_filter = FilterEngine(threshold=0.25)
            tier1 = quality_checker.filter_articles(loose_filter.filter_and_rank(deduplicated))
            new_articles = state.get_new_articles(tier1)
            if new_articles:
                logger.info(f"[SAFETY] Tier 1 recovered {len(new_articles)} articles (threshold=0.25)")

            # Tier 2: Skip quality checker but keep threshold strict
            if len(new_articles) == 0:
                tier2 = FilterEngine(threshold=0.25).filter_and_rank(deduplicated)
                new_articles = state.get_new_articles(tier2)
                if new_articles:
                    logger.info(f"[SAFETY] Tier 2 recovered {len(new_articles)} articles (no quality check)")

            # Tier 3: Ignore state dedup — send recent-ish articles even if seen before
            if len(new_articles) == 0 and deduplicated:
                logger.warning("[SAFETY] Tier 3: state dedup ignored — sending recent articles regardless")
                new_articles = sorted(
                    deduplicated,
                    key=lambda x: x.get("relevance_score", 0),
                    reverse=True,
                )[:5]

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

        # Prepare Discord notification (supports both channel and DM mode)
        notifier = DiscordNotifier(
            bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
            channel_id=os.getenv("DISCORD_CHANNEL_ID", ""),
            user_id=os.getenv("DISCORD_USER_ID", "")
        )

        if new_articles:
            # Keep only top 1-5 articles by relevance score
            top_articles = sorted(
                new_articles,
                key=lambda x: x.get("relevance_score", 0),
                reverse=True
            )[:5]  # Max 5 articles

            logger.info(
                f"[CURATE] Filtered {len(new_articles)} articles down to top {len(top_articles)} by relevance"
            )

            # Categorize top articles only
            categorized = filter_engine.categorize(top_articles)
            logger.info(
                f"[FORMAT] Categorized: "
                f"{', '.join(f'{k}:{len(v)}' for k, v in categorized.items() if v)}"
            )

            # Send immediate breaking news alerts (score > 0.9 + breaking category)
            breaking_articles = categorized.get("breaking", [])
            if breaking_articles:
                logger.info(f"[BREAKING] Sending {len(breaking_articles)} breaking news alerts...")
                for article in breaking_articles[:1]:  # Alert on top breaking news only
                    if article.get("relevance_score", 0) > 0.85:
                        notifier.send_breaking_alert(article)

            # Format and send digest (prefer rich embeds)
            logger.info("[DISCORD] Sending curated digest with rich embeds...")
            if notifier.send_digest_embeds(categorized):
                logger.info(f"Discord notification sent with {len(top_articles)} articles (embeds)")
            else:
                # Fallback to text format if embeds fail
                logger.warning("Embed send failed, falling back to text format")
                digest = notifier.format_digest(categorized)
                if notifier.send_digest(digest):
                    logger.info(f"Discord notification sent with {len(top_articles)} articles (text)")
                else:
                    logger.error("Failed to send Discord notification")

            # Send analytics summary (every 4 runs = daily if running 4x/day)
            if state.state['run_count'] % 4 == 0:
                analytics_summary = analytics.get_summary()
                # Try to send as embed, fall back to text
                if not notifier.send_analytics_embed(analytics.stats):
                    notifier.send_digest(f"**Daily Analytics**\n\n{analytics_summary}")
                logger.info("Daily analytics summary sent")
        else:
            logger.info("No new articles to send this run")

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
        logger.error(f"CRITICAL ERROR: {e}", exc_info=True)

        # Try to send comprehensive error alert to Discord
        try:
            error_notifier = DiscordNotifier(
                bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
                user_id=os.getenv("DISCORD_USER_ID", "")
            )

            # Include error context
            error_msg = f"""SCOUT Monitor Failed

Error: {str(e)[:150]}
Time: {datetime.utcnow().isoformat()}Z

Check logs at: claude.ai/code/routines
Next attempt: 6 hours"""
            error_notifier.send_error_alert(error_msg.strip())
            logger.info("Error alert sent to Discord")

        except Exception as alert_error:
            logger.error(f"Failed to send error alert: {alert_error}")

        # In cloud environment, exit cleanly (let Routine see error in logs)
        logger.info("=" * 70)
        logger.error("MONITOR FAILED - Check logs above for details")
        logger.info("=" * 70)
        exit(1)

    finally:
        # Disconnect bot at end of execution
        if 'bot_manager' in locals() and bot_manager:
            try:
                await bot_manager.disconnect()
            except Exception as e:
                logger.warning(f"Bot disconnect error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
