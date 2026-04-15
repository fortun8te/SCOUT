"""Analytics and statistics tracking for news bot"""

import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Track and analyze news bot metrics and trends"""

    def __init__(self, stats_file: Path = Path("data/stats.json")):
        self.stats_file = stats_file
        self.stats = self._load_stats()

    def _load_stats(self) -> Dict:
        """Load statistics from file"""
        if not self.stats_file.exists():
            return self._create_default_stats()

        try:
            with open(self.stats_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
            return self._create_default_stats()

    def _create_default_stats(self) -> Dict:
        """Create default stats structure"""
        return {
            "total_articles_processed": 0,
            "total_articles_sent": 0,
            "runs": [],
            "top_sources": {},
            "trending_keywords": {},
            "category_distribution": {},
            "hourly_distribution": {},
            "discovery_rate": 0
        }

    def record_run(self, articles_fetched: int, articles_sent: int,
                   sources: List[str], articles: List[Dict]) -> None:
        """Record a monitoring run"""

        run_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "articles_fetched": articles_fetched,
            "articles_sent": articles_sent,
            "sources_checked": sources,
            "discovery_rate": articles_sent / max(articles_fetched, 1)
        }

        self.stats["runs"].append(run_entry)
        self.stats["total_articles_processed"] += articles_fetched
        self.stats["total_articles_sent"] += articles_sent

        # Update source rankings
        for source in sources:
            self.stats["top_sources"][source] = self.stats["top_sources"].get(source, 0) + 1

        # Update trending keywords
        for article in articles:
            title = article.get("title", "").lower()
            for keyword in ["gpt", "claude", "llm", "ai", "model", "neural", "transformer"]:
                if keyword in title:
                    self.stats["trending_keywords"][keyword] = \
                        self.stats["trending_keywords"].get(keyword, 0) + 1

        # Update hourly distribution
        hour = datetime.utcnow().hour
        hour_key = f"hour_{hour:02d}"
        self.stats["hourly_distribution"][hour_key] = \
            self.stats["hourly_distribution"].get(hour_key, 0) + 1

        self.save()

    def get_summary(self) -> str:
        """Get human-readable analytics summary"""
        if not self.stats["runs"]:
            return "No data yet"

        total_runs = len(self.stats["runs"])
        total_sent = self.stats["total_articles_sent"]
        avg_per_run = total_sent / max(total_runs, 1)

        # Top sources
        if self.stats["top_sources"]:
            top_source = max(self.stats["top_sources"],
                           key=self.stats["top_sources"].get)
        else:
            top_source = "Unknown"

        # Trending keywords
        if self.stats["trending_keywords"]:
            trending = sorted(
                self.stats["trending_keywords"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            trending_str = ", ".join(f"{k}({v})" for k, v in trending)
        else:
            trending_str = "None yet"

        summary = f"""
📊 SCOUT Analytics Summary
═════════════════════════════
Runs: {total_runs}
Articles sent: {total_sent}
Avg per run: {avg_per_run:.1f}
Top source: {top_source}
Trending: {trending_str}
"""
        return summary

    def save(self) -> None:
        """Save stats to file"""
        try:
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
