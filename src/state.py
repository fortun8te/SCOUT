"""State management for processed news articles"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class StateManager:
    """Manages processed_news.json state file"""

    def __init__(self, state_file: Path = Path("data/processed_news.json")):
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> Dict:
        """Load state from JSON file"""
        if not self.state_file.exists():
            logger.warning(f"State file not found at {self.state_file}, creating new")
            return self._create_default_state()

        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return self._create_default_state()

    def _create_default_state(self) -> Dict:
        """Create default state structure"""
        return {
            "last_run": datetime.utcnow().isoformat() + "Z",
            "processed_articles": {},
            "run_count": 0,
            "statistics": {
                "total_processed": 0,
                "sent_today": 0,
                "sources_checked": []
            }
        }

    def is_processed(self, article_id: str) -> bool:
        """Check if article has been processed before"""
        return article_id in self.state.get("processed_articles", {})

    def mark_processed(self, article: Dict) -> None:
        """Mark article as processed"""
        article_id = article.get("id")
        if not article_id:
            logger.warning("Article missing ID, skipping")
            return

        self.state["processed_articles"][article_id] = {
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "source": article.get("source", ""),
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "score": article.get("relevance_score", 0)
        }

    def get_new_articles(self, articles: List[Dict]) -> List[Dict]:
        """Filter articles that haven't been processed"""
        new = []
        for article in articles:
            if not self.is_processed(article.get("id")):
                new.append(article)
                self.mark_processed(article)
        return new

    def update_stats(self, sources_checked: List[str], sent_count: int) -> None:
        """Update run statistics"""
        self.state["last_run"] = datetime.utcnow().isoformat() + "Z"
        self.state["run_count"] = self.state.get("run_count", 0) + 1
        self.state["statistics"]["total_processed"] = len(
            self.state.get("processed_articles", {})
        )
        self.state["statistics"]["sent_today"] = sent_count
        self.state["statistics"]["sources_checked"] = sources_checked

    def save(self) -> None:
        """Save state to JSON file"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
