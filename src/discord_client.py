"""Discord bot integration for news digests with rich embeds"""

import json
import logging
import subprocess
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Send news digests to Discord with rich embeds"""

    # Color codes for different categories (Discord decimal color values)
    CATEGORY_COLORS = {
        "models": 0x00b4d8,      # Blue
        "breaking": 0xff006e,    # Red/Pink
        "research": 0x8338ec,    # Purple
        "technical": 0xfbf007,   # Yellow
        "other": 0x606060        # Gray
    }

    def __init__(self, bot_token: str, channel_id: str = None, user_id: str = None):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.user_id = user_id
        self.dm_channel_id = None
        self.api_url = None

        # Set API URL based on what's available
        if channel_id:
            # Prefer channel mode
            self.api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        elif user_id:
            # Fall back to DM mode
            self._init_dm_channel()

    def _init_dm_channel(self):
        """Initialize DM channel with user"""
        try:
            result = subprocess.run(
                [
                    "curl", "-s", "-X", "POST",
                    "https://discord.com/api/v10/users/@me/channels",
                    "-H", f"Authorization: Bot {self.bot_token}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps({"recipient_id": self.user_id})
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    self.dm_channel_id = response.get("id")
                    if self.dm_channel_id:
                        self.api_url = f"https://discord.com/api/v10/channels/{self.dm_channel_id}/messages"
                        logger.info(f"DM channel initialized: {self.dm_channel_id}")
                    else:
                        logger.error(f"No channel ID in response: {result.stdout}")
                except json.JSONDecodeError as je:
                    logger.error(f"Failed to parse DM response: {result.stdout} - {je}")
            else:
                logger.error(f"Failed to init DM channel: {result.stderr}")
        except Exception as e:
            logger.error(f"DM channel init error: {e}")

    def send_digest(self, digest_text: str) -> bool:
        """Send formatted digest to Discord (plain text fallback)"""
        try:
            if not self.api_url:
                logger.error("Cannot send digest: Discord API URL not initialized")
                return False

            # Discord has 2000 char limit per message, split if needed
            if len(digest_text) > 1950:
                chunks = self._split_message(digest_text, 1950)
            else:
                chunks = [digest_text]

            for chunk in chunks:
                payload = {
                    "content": chunk
                }

                result = subprocess.run(
                    [
                        "curl", "-X", "POST", self.api_url,
                        "-H", f"Authorization: Bot {self.bot_token}",
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(payload)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    logger.error(f"Discord API error: {result.stderr}")
                    return False

            logger.info(f"Discord message sent ({len(chunks)} chunks)")
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False

    def send_digest_embeds(self, articles_by_category: Dict[str, List[Dict]]) -> bool:
        """Send formatted digest using Discord embeds for rich formatting"""
        try:
            if not self.api_url:
                logger.error("Cannot send embeds: Discord API URL not initialized")
                return False

            embeds = []

            # Create header embed
            total_articles = sum(len(v) for v in articles_by_category.values())
            now = datetime.now()
            date_str = now.strftime("%B %d, %Y")
            time_str = now.strftime("%I:%M %p")

            header_embed = {
                "title": date_str,
                "description": f"{time_str}\n{total_articles} stories",
                "color": 0x1f77b4
            }

            embeds.append(header_embed)

            # Create embeds for each article (max 10 total, 3 per category)
            article_count = 0
            for category, articles in articles_by_category.items():
                if not articles or article_count >= 10:
                    continue

                cat_color = self.CATEGORY_COLORS.get(category, 0x606060)

                for article in articles[:3]:
                    if article_count >= 10:
                        break

                    title = article.get("title", "")[:150]
                    url = article.get("url", "")
                    source = article.get("source", "Unknown")
                    summary = article.get("summary", "")

                    # Build description with summary or content
                    description = ""
                    if summary:
                        description = summary[:200]
                    else:
                        content = article.get("content", "")[:200]
                        if content:
                            description = content

                    embed = {
                        "title": title,
                        "url": url,
                        "color": cat_color,
                        "description": description if description else source
                    }

                    embeds.append(embed)
                    article_count += 1

            # Split into groups of 10 embeds (Discord limit per message)
            for i in range(0, len(embeds), 10):
                chunk_embeds = embeds[i:i+10]
                payload = {
                    "embeds": chunk_embeds
                }

                result = subprocess.run(
                    [
                        "curl", "-X", "POST", self.api_url,
                        "-H", f"Authorization: Bot {self.bot_token}",
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(payload)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    logger.error(f"Discord embed error: {result.stderr}")
                    return False

            logger.info(f"Discord embeds sent ({len(embeds)} embeds)")
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord embeds: {e}")
            return False

    def send_breaking_alert(self, article: Dict) -> bool:
        """Send immediate alert for breaking news"""
        try:
            if not self.api_url:
                logger.error("Cannot send breaking alert: Discord API URL not initialized")
                return False

            title = article.get('title', 'Breaking News')[:200]
            source = article.get("source", "Unknown")
            score = article.get("relevance_score", 0)
            url = article.get("url", "")

            embed = {
                "title": title,
                "url": url,
                "color": 0xff006e,
                "fields": [
                    {
                        "name": "Source",
                        "value": source,
                        "inline": True
                    },
                    {
                        "name": "Relevance",
                        "value": f"{score:.0%}",
                        "inline": True
                    }
                ]
            }

            payload = {
                "embeds": [embed]
            }

            result = subprocess.run(
                [
                    "curl", "-X", "POST", self.api_url,
                    "-H", f"Authorization: Bot {self.bot_token}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"Breaking news alert sent: {article.get('title', '')[:60]}...")
                return True
            else:
                logger.error(f"Breaking alert error: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to send breaking alert: {e}")
            return False

    def send_error_alert(self, error_message: str) -> bool:
        """Send error notification to Discord"""
        try:
            if not self.api_url:
                logger.error("Cannot send error alert: Discord API URL not initialized")
                return False

            embed = {
                "title": "SCOUT Monitor Error",
                "description": error_message[:2048],
                "color": 0xff6b6b,
                "fields": [{
                    "name": "Time",
                    "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "inline": False
                }]
            }

            payload = {
                "embeds": [embed]
            }

            result = subprocess.run(
                [
                    "curl", "-X", "POST", self.api_url,
                    "-H", f"Authorization: Bot {self.bot_token}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to send Discord error: {e}")
            return False

    def format_digest(self, articles_by_category: Dict[str, List[Dict]]) -> str:
        """Format articles for Discord text fallback"""
        from datetime import datetime
        lines = []

        now = datetime.now()
        date_str = now.strftime("%B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        total_articles = sum(len(v) for v in articles_by_category.values())

        lines.append(f"# {date_str}")
        lines.append(f"## {time_str}")
        lines.append(f"**{total_articles} stories**")
        lines.append("")

        article_num = 1
        for category, articles in articles_by_category.items():
            if not articles:
                continue

            for article in articles[:3]:  # Max 3 per category
                title = article.get("title", "")[:100]
                source = article.get("source", "Unknown")
                summary = article.get("summary", "")

                lines.append(f"**{article_num}. {title}**")

                # Add summary if available, otherwise use first 100 chars of content
                if summary:
                    lines.append(summary[:120])
                else:
                    content = article.get("content", "")[:120]
                    if content:
                        lines.append(content)

                lines.append(f"_{source}_")
                lines.append("")
                article_num += 1

        return "\n".join(lines)

    def send_analytics_embed(self, stats: Dict) -> bool:
        """Send analytics summary as Discord embed"""
        try:
            if not self.api_url:
                logger.error("Cannot send analytics: Discord API URL not initialized")
                return False

            # Calculate metrics
            total_runs = len(stats.get("runs", []))
            total_sent = stats.get("total_articles_sent", 0)
            total_fetched = stats.get("total_articles_processed", 0)

            avg_per_run = total_sent / max(total_runs, 1)
            discovery_rate = total_sent / max(total_fetched, 1)

            # Top source
            top_sources = stats.get("top_sources", {})
            if top_sources:
                top_source = max(top_sources.items(), key=lambda x: x[1])
                top_source_str = f"{top_source[0]} ({top_source[1]} checks)"
            else:
                top_source_str = "N/A"

            # Trending keywords
            trending_kw = stats.get("trending_keywords", {})
            if trending_kw:
                top_keywords = sorted(trending_kw.items(), key=lambda x: x[1], reverse=True)[:5]
                trending_str = ", ".join(f"{k}({v})" for k, v in top_keywords)
            else:
                trending_str = "None yet"

            embed = {
                "title": "SCOUT Daily Analytics",
                "color": 0x1f77b4,
                "fields": [
                    {
                        "name": "Runs",
                        "value": str(total_runs),
                        "inline": True
                    },
                    {
                        "name": "Articles",
                        "value": str(total_sent),
                        "inline": True
                    },
                    {
                        "name": "Avg/Run",
                        "value": f"{avg_per_run:.1f}",
                        "inline": True
                    },
                    {
                        "name": "Discovery",
                        "value": f"{discovery_rate:.1%}",
                        "inline": True
                    },
                    {
                        "name": "Top Source",
                        "value": top_source_str,
                        "inline": False
                    },
                    {
                        "name": "Trending",
                        "value": trending_str,
                        "inline": False
                    }
                ]
            }

            payload = {"embeds": [embed]}

            result = subprocess.run(
                [
                    "curl", "-X", "POST", self.api_url,
                    "-H", f"Authorization: Bot {self.bot_token}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("Analytics embed sent successfully")
                return True
            else:
                logger.error(f"Analytics embed error: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to send analytics embed: {e}")
            return False

    @staticmethod
    def _split_message(text: str, max_length: int = 1950) -> List[str]:
        """Split message by newlines to respect Discord limit"""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current = ""

        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_length:
                if current:
                    chunks.append(current)
                current = line
            else:
                current += "\n" + line if current else line

        if current:
            chunks.append(current)

        return chunks
