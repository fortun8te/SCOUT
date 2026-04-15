"""Handle real-time webhook notifications for breaking news"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Process incoming webhook events for real-time alerts"""

    # High-priority keywords that trigger immediate alerts
    BREAKING_KEYWORDS = [
        "gpt-5", "gpt-6", "o1", "o3",  # OpenAI
        "claude 4", "claude 5",  # Anthropic
        "gemini 2", "gemini 3",  # Google
        "llama 4", "llama 5",  # Meta
        "outage", "down", "offline",  # Outages
        "breach", "security", "vulnerability",  # Security
        "acquisition", "shutdown", "acquired"  # Major events
    ]

    def process_github_webhook(self, payload: Dict) -> bool:
        """Process GitHub webhook for repo releases/updates"""
        try:
            action = payload.get("action")
            repo = payload.get("repository", {}).get("name", "")

            # Monitor specific repos
            monitored_repos = [
                "anthropics/anthropic-sdk",
                "openai/gpt-4",
                "ggerganov/llama.cpp"
            ]

            if repo not in monitored_repos:
                return False

            # Check for releases or major commits
            if action == "released":
                return True

            # Check commit messages
            if action == "push":
                commits = payload.get("commits", [])
                for commit in commits:
                    msg = commit.get("message", "").lower()
                    if any(kw in msg for kw in self.BREAKING_KEYWORDS):
                        logger.info(f"Breaking commit detected: {repo}")
                        return True

            return False

        except Exception as e:
            logger.error(f"GitHub webhook error: {e}")
            return False

    def process_custom_alert(self, title: str, url: str) -> bool:
        """Process custom real-time alert"""
        title_lower = title.lower()

        # Check for breaking keywords
        is_breaking = any(kw in title_lower for kw in self.BREAKING_KEYWORDS)

        if is_breaking:
            logger.info(f"Real-time breaking alert: {title}")
            return True

        return False

    @staticmethod
    def should_send_immediately(article: Dict) -> bool:
        """Check if article should be sent immediately (real-time) vs batched"""
        score = article.get("relevance_score", 0)
        title = article.get("title", "").lower()

        # Very high relevance + breaking keywords
        if score > 0.9:
            breaking = any(kw in title for kw in WebhookHandler.BREAKING_KEYWORDS)
            if breaking:
                return True

        return False
