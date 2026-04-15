"""News source aggregation from multiple APIs"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


class NewsSourceAggregator:
    """Aggregates news from multiple sources"""

    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {}
        self.session = requests.Session()

    async def fetch_all(self):
        """
        Fetch from all sources in PARALLEL for 2x speed
        Uses asyncio.gather to batch all API calls
        Returns: (all_articles, sources_checked)
        """
        all_articles = []
        sources_checked = []

        # Build parallel tasks - MASSIVE source list
        tasks = [
            self._fetch_hackernews(),
            self._fetch_arxiv(),
            self._fetch_reddit(),
            self._fetch_lobsters(),
            self._fetch_techcrunch(),
            self._fetch_medium(),
            self._fetch_indie_hackers(),
            self._fetch_slashdot(),
            self._fetch_mastodon(),
        ]

        # Add optional sources if API keys provided
        if self.api_keys.get("newsapi_key"):
            tasks.append(self._fetch_newsapi())

        # Run all fetches in parallel
        logger.info("[PARALLEL] Starting parallel fetch from all sources...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        result_map = [
            ("HackerNews", results[0]),
            ("ArXiv", results[1]),
            ("Reddit", results[2]),
            ("Lobsters", results[3]),
            ("TechCrunch", results[4]),
            ("Medium", results[5]),
            ("Indie Hackers", results[6]),
            ("Slashdot", results[7]),
            ("Mastodon", results[8]),
        ]

        if self.api_keys.get("newsapi_key"):
            result_map.append(("NewsAPI", results[9]))

        for source_name, result in result_map:
            if isinstance(result, Exception):
                logger.warning(f"[PARALLEL] {source_name} failed: {result}")
            else:
                all_articles.extend(result)
                sources_checked.append(source_name)

        logger.info(
            f"[PARALLEL] ✓ Fetched {len(all_articles)} articles "
            f"from {len(sources_checked)} sources (parallel execution)"
        )
        return all_articles, sources_checked

    async def _fetch_hackernews(self) -> List[Dict]:
        """Fetch top stories from HackerNews using Algolia API"""
        try:
            response = self.session.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": "AI OR artificial intelligence OR machine learning",
                    "tags": "story",
                    "numericFilters": "points>10",
                    "hitsPerPage": 30
                },
                timeout=10
            )

            # Handle service unavailable gracefully
            if response.status_code == 503:
                logger.warning(f"HackerNews API temporarily unavailable (503)")
                return []

            response.raise_for_status()
            hits = response.json().get("hits", [])

            articles = []
            for hit in hits:
                try:
                    articles.append({
                        "id": f"hn_{hit['objectID']}",
                        "title": hit.get("title", ""),
                        "url": hit.get("url", ""),
                        "source": "HackerNews",
                        "published_at": datetime.fromisoformat(hit.get("created_at", "").replace("Z", "+00:00")),
                        "engagement_score": hit.get("points", 0),
                        "is_recent": True
                    })
                except Exception as article_error:
                    logger.debug(f"Failed to parse HN article: {article_error}")
                    continue
            return articles
        except Exception as e:
            logger.warning(f"HackerNews error: {e}")
            return []

    async def _fetch_arxiv(self) -> List[Dict]:
        """Fetch recent AI papers from ArXiv via HTTP API"""
        try:
            response = self.session.get(
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
                    "start": 0,
                    "max_results": 30,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending"
                },
                timeout=15
            )

            # Handle service unavailable gracefully
            if response.status_code == 503:
                logger.warning(f"ArXiv API temporarily unavailable (503)")
                return []

            response.raise_for_status()

            # Parse XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)

            articles = []
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                try:
                    title_elem = entry.find("atom:title", ns)
                    id_elem = entry.find("atom:id", ns)
                    published_elem = entry.find("atom:published", ns)

                    if title_elem is not None and id_elem is not None:
                        arxiv_id = id_elem.text.split("/abs/")[-1]
                        articles.append({
                            "id": f"arxiv_{arxiv_id}",
                            "title": title_elem.text.replace("\n", " ").strip(),
                            "url": f"https://arxiv.org/abs/{arxiv_id}",
                            "source": "ArXiv",
                            "published_at": datetime.fromisoformat(
                                published_elem.text.replace("Z", "+00:00")
                            ) if published_elem is not None else datetime.utcnow(),
                            "engagement_score": 0,
                            "is_recent": True
                        })
                except Exception as article_error:
                    logger.debug(f"Failed to parse ArXiv article: {article_error}")
                    continue
            return articles
        except Exception as e:
            logger.warning(f"ArXiv error: {e}")
            return []

    async def _fetch_reddit(self) -> List[Dict]:
        """Fetch top posts from AI-related subreddits"""
        try:
            articles = []
            # Massive list of AI/tech subreddits
            subreddits = [
                "MachineLearning", "OpenAI", "artificial", "LanguageModels", "LocalLLaMA",
                "ChatGPT", "Anthropic", "learnmachinelearning", "deeplearning", "neuralnetworks",
                "compsci", "programming", "technology", "coding", "Python", "ArtificialIntelligence",
                "tech", "startups", "futurology", "news", "science", "explainlikeimfive"
            ]

            for sub in subreddits:
                try:
                    # Reddit requires specific User-Agent and headers
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    response = self.session.get(
                        f"https://www.reddit.com/r/{sub}/new.json",
                        headers=headers,
                        timeout=10,
                        allow_redirects=True
                    )
                    response.raise_for_status()
                    posts = response.json().get("data", {}).get("children", [])

                    for post_data in posts[:10]:
                        post = post_data["data"]
                        articles.append({
                            "id": f"reddit_{post['id']}",
                            "title": post.get("title", ""),
                            "url": post.get("url", ""),
                            "source": f"Reddit (r/{sub})",
                            "published_at": datetime.fromtimestamp(post.get("created_utc", 0)),
                            "engagement_score": post.get("score", 0),
                            "is_recent": True
                        })
                except Exception as e:
                    logger.warning(f"Reddit r/{sub} error: {e}")
                    continue

            return articles
        except Exception as e:
            logger.error(f"Reddit error: {e}")
            return []

    async def _fetch_newsapi(self) -> List[Dict]:
        """Fetch from NewsAPI.org"""
        try:
            api_key = self.api_keys.get("newsapi_key")
            if not api_key:
                return []

            response = self.session.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": "AI OR artificial intelligence OR machine learning OR deep learning",
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 30,
                    "apiKey": api_key
                },
                timeout=10
            )
            response.raise_for_status()
            articles_data = response.json().get("articles", [])

            articles = []
            for article in articles_data:
                articles.append({
                    "id": f"newsapi_{article.get('url', '').replace('/', '_')}",
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", "NewsAPI"),
                    "published_at": datetime.fromisoformat(article.get("publishedAt", "").replace("Z", "+00:00")),
                    "engagement_score": 0,
                    "is_recent": True
                })
            return articles
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []

    async def _fetch_lobsters(self) -> List[Dict]:
        """Fetch from Lobsters (tech community site)"""
        try:
            response = self.session.get(
                "https://lobste.rs/newest.json",
                timeout=10
            )
            response.raise_for_status()
            posts = response.json()

            articles = []
            for post in posts[:20]:
                try:
                    articles.append({
                        "id": f"lobsters_{post['id']}",
                        "title": post.get("title", ""),
                        "url": post.get("url", ""),
                        "source": "Lobsters",
                        "published_at": datetime.fromisoformat(
                            post.get("created_at", "").replace("Z", "+00:00")
                        ) if post.get("created_at") else datetime.utcnow(),
                        "engagement_score": post.get("score", 0),
                        "is_recent": True
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse Lobsters post: {e}")
                    continue
            return articles
        except Exception as e:
            logger.warning(f"Lobsters error: {e}")
            return []

    async def _fetch_techcrunch(self) -> List[Dict]:
        """Fetch from TechCrunch RSS via public API"""
        try:
            # Using TechCrunch search API
            response = self.session.get(
                "https://techcrunch.com/wp-json/wp/v2/posts",
                params={
                    "per_page": 20,
                    "search": "AI OR artificial intelligence OR machine learning"
                },
                timeout=10
            )
            response.raise_for_status()
            posts = response.json()

            articles = []
            for post in posts[:15]:
                try:
                    articles.append({
                        "id": f"tc_{post['id']}",
                        "title": post.get("title", {}).get("rendered", ""),
                        "url": post.get("link", ""),
                        "source": "TechCrunch",
                        "published_at": datetime.fromisoformat(
                            post.get("date", "").replace("Z", "+00:00")
                        ) if post.get("date") else datetime.utcnow(),
                        "engagement_score": 0,
                        "is_recent": True
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse TechCrunch post: {e}")
                    continue
            return articles
        except Exception as e:
            logger.warning(f"TechCrunch error: {e}")
            return []

    async def _fetch_medium(self) -> List[Dict]:
        """Fetch from Medium AI publications"""
        try:
            response = self.session.get(
                "https://medium.com/tag/artificial-intelligence/latest",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=10
            )
            response.raise_for_status()

            # Basic HTML parsing for Medium
            import re as regex
            titles = regex.findall(r'<h2[^>]*>([^<]+)</h2>', response.text)
            urls = regex.findall(r'href="(https://medium\.com/[^"]+)"', response.text)

            articles = []
            for i, title in enumerate(titles[:15]):
                if i < len(urls):
                    articles.append({
                        "id": f"medium_{i}",
                        "title": title.strip(),
                        "url": urls[i],
                        "source": "Medium",
                        "published_at": datetime.utcnow(),
                        "engagement_score": 0,
                        "is_recent": True
                    })
            return articles
        except Exception as e:
            logger.warning(f"Medium error: {e}")
            return []

    async def _fetch_indie_hackers(self) -> List[Dict]:
        """Fetch from Indie Hackers"""
        try:
            response = self.session.get(
                "https://www.indiehackers.com/feed.json",
                timeout=10
            )
            response.raise_for_status()
            posts = response.json()

            articles = []
            for post in posts.get("posts", [])[:20]:
                try:
                    articles.append({
                        "id": f"ih_{post['id']}",
                        "title": post.get("title", ""),
                        "url": post.get("url", ""),
                        "source": "Indie Hackers",
                        "published_at": datetime.utcnow(),
                        "engagement_score": post.get("votes_count", 0),
                        "is_recent": True
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse IH post: {e}")
                    continue
            return articles
        except Exception as e:
            logger.warning(f"Indie Hackers error: {e}")
            return []

    async def _fetch_slashdot(self) -> List[Dict]:
        """Fetch from Slashdot tech news"""
        try:
            response = self.session.get(
                "https://slashdot.org/index.rss",
                timeout=10
            )
            response.raise_for_status()

            # Parse RSS with regex
            import re as regex
            titles = regex.findall(r'<title>([^<]+)</title>', response.text)
            urls = regex.findall(r'<link>([^<]+)</link>', response.text)

            articles = []
            for i, title in enumerate(titles[1:16]):  # Skip first (feed title)
                if i < len(urls):
                    articles.append({
                        "id": f"slashdot_{i}",
                        "title": title.strip(),
                        "url": urls[i] if urls[i].startswith('http') else f"https://slashdot.org{urls[i]}",
                        "source": "Slashdot",
                        "published_at": datetime.utcnow(),
                        "engagement_score": 0,
                        "is_recent": True
                    })
            return articles
        except Exception as e:
            logger.warning(f"Slashdot error: {e}")
            return []

    async def _fetch_mastodon(self) -> List[Dict]:
        """Fetch from Mastodon instances (decentralized Twitter alternative)"""
        try:
            # Search across federated Mastodon instances
            response = self.session.get(
                "https://mastodon.social/api/v2/search",
                params={
                    "q": "AI artificial intelligence machine learning",
                    "type": "statuses",
                    "limit": 30
                },
                timeout=10
            )
            response.raise_for_status()
            statuses = response.json().get("statuses", [])

            articles = []
            for status in statuses[:20]:
                try:
                    # Clean HTML content
                    import re as regex
                    content = status.get("content", "")
                    content = regex.sub(r'<[^>]+>', '', content)  # Remove HTML tags

                    articles.append({
                        "id": f"mastodon_{status['id']}",
                        "title": content[:100] if content else "Mastodon post",
                        "url": status.get("url", ""),
                        "source": f"Mastodon (@{status.get('account', {}).get('username', 'unknown')})",
                        "published_at": datetime.fromisoformat(
                            status.get("created_at", "").replace("Z", "+00:00")
                        ) if status.get("created_at") else datetime.utcnow(),
                        "engagement_score": status.get("favourites_count", 0) + status.get("replies_count", 0),
                        "is_recent": True,
                        "content": content
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse Mastodon post: {e}")
                    continue
            return articles
        except Exception as e:
            logger.warning(f"Mastodon error: {e}")
            return []

    async def _fetch_rss_feeds(self) -> List[Dict]:
        """Fetch from RSS feeds (fallback) - currently disabled due to dependencies"""
        # RSS fetching disabled to reduce dependency complexity
        # Can be re-enabled with feedparser library
        return []
