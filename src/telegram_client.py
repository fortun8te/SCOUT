"""Telegram notification client"""

import logging
import subprocess
import json
from typing import Dict, List

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends formatted news digests to Telegram"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send_digest(self, digest_text: str) -> bool:
        """Send formatted digest message"""
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": digest_text,
                "parse_mode": "HTML"
            }

            result = subprocess.run(
                [
                    "curl", "-X", "POST", self.api_url,
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def format_digest(self, articles_by_category: Dict[str, List[Dict]]) -> str:
        """Format articles into a readable digest"""
        lines = []
        lines.append("<b>AI News Update</b>")
        lines.append("")

        total_articles = sum(len(v) for v in articles_by_category.values())
        lines.append(f"{total_articles} stories")
        lines.append("")

        # Category names without emoji
        category_names = {
            "models": "NEW MODELS",
            "breaking": "BREAKING",
            "research": "RESEARCH",
            "technical": "TECHNICAL",
            "other": "OTHER"
        }

        article_num = 1

        for category, articles in articles_by_category.items():
            if not articles:
                continue

            cat_name = category_names.get(category, "OTHER")

            lines.append(f"<b>{cat_name}</b>")
            lines.append("")

            for article in articles[:5]:  # Top 5 per category
                title = article.get("title", "No title")[:75]  # Truncate
                score = article.get("relevance_score", 0)
                source = article.get("source", "Unknown")
                summary = article.get("summary", "")

                # Escape HTML special chars
                title = (title.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;"))
                if summary:
                    summary = (summary.replace("&", "&amp;")
                              .replace("<", "&lt;")
                              .replace(">", "&gt;"))

                lines.append(f"{article_num}. {title}")
                if summary:
                    lines.append(f"   {summary}")
                lines.append(f"   {source} | {score:.0%} relevant")
                lines.append(f"   {article.get('url', '#')}")
                lines.append("")
                article_num += 1

        lines.append("---")
        lines.append(f"Next update in 3 hours")

        return "\n".join(lines)

    def send_error_alert(self, error_message: str) -> bool:
        """Send error notification"""
        message = f"⚠️ <b>News Bot Error</b>\n\n{error_message}"
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            result = subprocess.run(
                [
                    "curl", "-X", "POST", self.api_url,
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to send error alert: {e}")
            return False
