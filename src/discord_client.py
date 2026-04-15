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

        # For DMs, we'll get the DM channel on first use
        if user_id and not channel_id:
            self._init_dm_channel()

        if channel_id:
            self.api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        else:
            self.api_url = None

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
            header_embed = {
                "title": "🤖 AI News Update",
                "description": f"Latest AI news digest • {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC",
                "color": 0x1f77b4,
                "fields": []
            }

            total_articles = sum(len(v) for v in articles_by_category.values())
            header_embed["fields"].append({
                "name": "Stories",
                "value": str(total_articles),
                "inline": True
            })

            for category in articles_by_category:
                if articles_by_category[category]:
                    header_embed["fields"].append({
                        "name": category.title(),
                        "value": str(len(articles_by_category[category])),
                        "inline": True
                    })

            embeds.append(header_embed)

            # Create embeds for each article (max 10 per category)
            category_names = {
                "models": "🚀 NEW MODELS",
                "breaking": "🚨 BREAKING",
                "research": "📚 RESEARCH",
                "technical": "⚙️ TECHNICAL",
                "other": "📰 OTHER"
            }

            article_count = 0
            for category, articles in articles_by_category.items():
                if not articles or article_count >= 25:  # Max 25 articles across embeds
                    continue

                cat_color = self.CATEGORY_COLORS.get(category, 0x606060)
                cat_name = category_names.get(category, "OTHER")

                for article in articles[:5]:  # Max 5 per category
                    if article_count >= 25:
                        break

                    embed = {
                        "title": article.get("title", "No title")[:256],
                        "url": article.get("url", ""),
                        "color": cat_color,
                        "fields": []
                    }

                    # Add summary if available
                    summary = article.get("summary", "")
                    if summary:
                        embed["description"] = summary[:200]

                    # Add source and score
                    source = article.get("source", "Unknown")
                    score = article.get("relevance_score", 0)
                    embed["fields"].append({
                        "name": f"Source • Relevance",
                        "value": f"{source} • {score:.0%}",
                        "inline": False
                    })

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

            embed = {
                "title": f"🚨 BREAKING: {article.get('title', 'Breaking News')[:200]}",
                "url": article.get("url", ""),
                "color": 0xff006e,  # Red for breaking
                "fields": []
            }

            # Add source and timestamp
            source = article.get("source", "Unknown")
            score = article.get("relevance_score", 0)
            embed["fields"].append({
                "name": "Source • Relevance",
                "value": f"{source} • {score:.0%}",
                "inline": False
            })

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
                "title": "⚠️ SCOUT Monitor Error",
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
        lines = []
        lines.append("🤖 **AI News Update**")
        lines.append("")

        total_articles = sum(len(v) for v in articles_by_category.values())
        lines.append(f"**{total_articles} stories**")
        lines.append("")

        category_names = {
            "models": "🚀 NEW MODELS",
            "breaking": "🚨 BREAKING",
            "research": "📚 RESEARCH",
            "technical": "⚙️ TECHNICAL",
            "other": "📰 OTHER"
        }

        article_num = 1

        for category, articles in articles_by_category.items():
            if not articles:
                continue

            cat_name = category_names.get(category, "OTHER")
            lines.append(f"**{cat_name}** ({len(articles)})")
            lines.append("")

            for article in articles[:5]:
                title = article.get("title", "No title")[:75]
                score = article.get("relevance_score", 0)
                source = article.get("source", "Unknown")
                url = article.get("url", "")

                lines.append(f"{article_num}. **{title}**")
                lines.append(f"   {source} · {score:.0%} · {url[:50]}...")
                lines.append("")
                article_num += 1

        lines.append("---")
        lines.append("Next update in 6 hours")

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
                "title": "📊 SCOUT Daily Analytics",
                "color": 0x1f77b4,
                "fields": [
                    {
                        "name": "Runs",
                        "value": str(total_runs),
                        "inline": True
                    },
                    {
                        "name": "Articles Sent",
                        "value": str(total_sent),
                        "inline": True
                    },
                    {
                        "name": "Avg Per Run",
                        "value": f"{avg_per_run:.1f}",
                        "inline": True
                    },
                    {
                        "name": "Discovery Rate",
                        "value": f"{discovery_rate:.1%}",
                        "inline": True
                    },
                    {
                        "name": "Top Source",
                        "value": top_source_str,
                        "inline": False
                    },
                    {
                        "name": "Trending Keywords",
                        "value": trending_str,
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
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
