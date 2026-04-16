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
from src.content_extractor import content_extractor

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

        # HARD time window: only articles from last 8 hours
        # This prevents resending old articles even when state file is missing
        # (e.g., in cloud Routine runs where state doesn't persist)
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=8)
        fresh_articles = []
        for a in all_articles:
            pub = a.get("published_at")
            if isinstance(pub, datetime):
                if pub.tzinfo is not None:
                    pub = pub.replace(tzinfo=None)
                if pub >= cutoff:
                    fresh_articles.append(a)
            else:
                # No date available — keep it (let filter/quality handle)
                fresh_articles.append(a)
        logger.info(
            f"[RECENCY] Kept {len(fresh_articles)} articles from last 8h "
            f"(dropped {len(all_articles) - len(fresh_articles)} older)"
        )
        all_articles = fresh_articles

        # Semantic deduplication (remove near-duplicates from same batch)
        logger.info("[DEDUP-BATCH] Running semantic deduplication...")
        deduplicated = deduplicator.find_duplicates(all_articles)
        logger.info(
            f"[DEDUP-BATCH] ✓ Removed {len(all_articles) - len(deduplicated)} "
            f"near-duplicates"
        )

        # Cross-source trending detection: annotate representatives with
        # trending_source_count so the filter can boost their score.
        trending_map = deduplicator.detect_trending(deduplicated)
        multi_source = sum(1 for v in trending_map.values() if v > 1)
        logger.info(
            f"[TRENDING] Found {multi_source} articles covered by 2+ sources"
        )

        # Filter and rank articles (balance: filter AI-relevant but not too strict)
        filter_engine = FilterEngine(threshold=0.20)
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

        # Enrich top articles with full page content (for thin RSS summaries)
        if new_articles:
            try:
                top_for_enrich = sorted(
                    new_articles,
                    key=lambda x: x.get("relevance_score", 0),
                    reverse=True,
                )[:10]
                needs_enrich = [
                    a for a in top_for_enrich
                    if len(a.get("summary", "") or "") < 100 and a.get("url")
                ]
                enriched_count = 0
                if needs_enrich:
                    results = await asyncio.gather(
                        *(content_extractor.extract(a["url"], timeout=5) for a in needs_enrich),
                        return_exceptions=True,
                    )
                    for article, text in zip(needs_enrich, results):
                        if isinstance(text, str) and text:
                            article["summary"] = text
                            enriched_count += 1
                logger.info(f"[ENRICH] Extracted content for {enriched_count} articles")
            except Exception as e:
                logger.warning(f"[ENRICH] Enrichment failed: {e}")

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
            # Keep only top 1-5 articles with SOURCE DIVERSITY
            # (max 2 from same source to avoid one source dominating)
            import re as _re
            ranked = sorted(
                new_articles,
                key=lambda x: x.get("relevance_score", 0),
                reverse=True
            )

            # GUARANTEE: at least one Claude-related article if any exist
            claude_pattern = _re.compile(
                r"\b(claude|anthropic|opus|sonnet|haiku)\b", _re.IGNORECASE
            )
            claude_articles = [
                a for a in ranked
                if claude_pattern.search(a.get("title", ""))
                or claude_pattern.search(a.get("summary", ""))
            ]

            top_articles = []
            source_counts = {}

            # Seed with top Claude article if available
            if claude_articles:
                top_articles.append(claude_articles[0])
                source_counts[claude_articles[0].get("source", "Unknown")] = 1
                logger.info(
                    f"[CLAUDE] Seeded digest with: {claude_articles[0].get('title', '')[:60]}"
                )

            # Fill the rest with top-ranked, respecting source diversity
            for article in ranked:
                if article in top_articles:
                    continue
                src = article.get("source", "Unknown")
                if source_counts.get(src, 0) >= 2:
                    continue
                top_articles.append(article)
                source_counts[src] = source_counts.get(src, 0) + 1
                if len(top_articles) >= 5:
                    break
            # Fallback: if diversity filter was too strict, fill with top-ranked
            if len(top_articles) < 3:
                for article in ranked:
                    if article not in top_articles:
                        top_articles.append(article)
                        if len(top_articles) >= 5:
                            break

            logger.info(
                f"[CURATE] Filtered {len(new_articles)} articles down to top {len(top_articles)} by relevance"
            )

            # Categorize top articles only
            categorized = filter_engine.categorize(top_articles)
            logger.info(
                f"[FORMAT] Categorized: "
                f"{', '.join(f'{k}:{len(v)}' for k, v in categorized.items() if v)}"
            )

            # Attach bracketed label (e.g. [RELEASE]) to each article for Discord
            label_counts = {}
            for category, cat_articles in categorized.items():
                for article in cat_articles:
                    article["category"] = category
                    label = filter_engine.detect_label(article)
                    article["label"] = label
                    key = label or "(none)"
                    label_counts[key] = label_counts.get(key, 0) + 1
            if label_counts:
                logger.info(
                    f"[LABELS] "
                    f"{', '.join(f'{k}:{v}' for k, v in label_counts.items())}"
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
