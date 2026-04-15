"""Real-time Bluesky news monitoring via Jetstream"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BlueskyJetstreamMonitor:
    """Monitor Bluesky for real-time AI news via Jetstream WebSocket"""

    def __init__(self, keywords: Optional[List[str]] = None):
        """
        Initialize Bluesky monitor

        Args:
            keywords: List of keywords to filter posts (optional, gets all by default)
        """
        self.keywords = keywords or [
            "AI", "artificial intelligence", "machine learning", "LLM", "GPT",
            "Claude", "neural", "transformer", "model", "breakthrough", "release",
            "deployment", "API", "algorithm", "dataset", "research"
        ]
        self.jetstream_urls = [
            "wss://jetstream1.us-east.bsky.network/subscribe",
            "wss://jetstream2.us-east.bsky.network/subscribe",
            "wss://jetstream3.us-east.bsky.network/subscribe",
        ]
        self.timeout = 5  # Timeout for fetching initial batch

    async def fetch_recent_posts(self) -> List[Dict]:
        """
        Fetch recent Bluesky posts about AI
        Uses REST API for initial batch (faster than WebSocket for one-shot queries)
        """
        articles = []

        # Using bsky.app social API for initial batch
        try:
            async with aiohttp.ClientSession() as session:
                # Search feed endpoint (public, no auth needed)
                async with session.get(
                    "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                    params={
                        "q": " OR ".join(self.keywords[:10]),  # Top 10 keywords
                        "limit": 30,
                        "sort": "latest"
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        posts = data.get("posts", [])

                        for post in posts:
                            record = post.get("record", {})
                            author = post.get("author", {})

                            articles.append({
                                "id": f"bluesky_{post['uri']}",
                                "title": record.get("text", "")[:100],
                                "url": f"https://bsky.app/profile/{author.get('handle', '')}/post/{post['uri'].split('/')[-1]}",
                                "source": f"Bluesky (@{author.get('handle', 'unknown')})",
                                "published_at": datetime.fromisoformat(
                                    record.get("createdAt", "").replace("Z", "+00:00")
                                ),
                                "engagement_score": post.get("likeCount", 0) +
                                                   post.get("replyCount", 0) +
                                                   post.get("repostCount", 0),
                                "is_recent": True,
                                "content": record.get("text", "")
                            })

                        logger.info(f"Fetched {len(articles)} posts from Bluesky")
                        return articles
                    else:
                        logger.warning(f"Bluesky API returned status {resp.status}")
                        return []

        except Exception as e:
            logger.error(f"Bluesky fetch error: {e}")
            return []

    async def stream_realtime(self, callback, duration_seconds: int = 60):
        """
        Stream real-time posts from Jetstream
        This is for continuous monitoring (not used in 6-hour batch job)
        """
        for jetstream_url in self.jetstream_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(jetstream_url, timeout=30) as ws:
                        logger.info(f"Connected to {jetstream_url}")

                        start_time = asyncio.get_event_loop().time()

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    event = json.loads(msg.data)

                                    # Filter for posts (not other events)
                                    if event.get("#t") == "com.atproto.sync.subscribeRepos":
                                        await self._process_event(event, callback)

                                    # Check duration
                                    elapsed = asyncio.get_event_loop().time() - start_time
                                    if elapsed > duration_seconds:
                                        break

                                except json.JSONDecodeError:
                                    continue

                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error("WebSocket error, trying next instance")
                                break

                        break  # Success, don't try other instances

            except Exception as e:
                logger.warning(f"Jetstream {jetstream_url} failed: {e}, trying next...")
                continue

    async def _process_event(self, event: Dict, callback) -> None:
        """Process a Jetstream event and extract posts"""
        try:
            blocks = event.get("blocks", [])
            for block in blocks:
                decoded = json.loads(block)
                if decoded.get("$type") == "com.atproto.repo.strongRef":
                    # This is a post reference
                    post_text = decoded.get("value", {}).get("text", "")

                    # Check if any keyword matches
                    if any(kw.lower() in post_text.lower() for kw in self.keywords):
                        await callback(post_text)
        except Exception as e:
            logger.debug(f"Event processing error: {e}")
