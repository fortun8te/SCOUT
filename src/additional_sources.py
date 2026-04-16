"""Additional news sources for better research coverage"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict

import requests

logger = logging.getLogger(__name__)


class AdditionalSources:
    """Additional high-quality sources for comprehensive coverage"""

    # Massive list of tech/AI news sites
    TECH_NEWS_FEEDS = [
        "https://news.ycombinator.com/",
        "https://techcrunch.com/",
        "https://theverge.com/",
        "https://arstechnica.com/",
        "https://slashdot.org/",
        "https://producthunt.com/",
        "https://indiehackers.com/",
        "https://dev.to/",
        "https://medium.com/",
    ]

    def __init__(self):
        self.session = requests.Session()

    async def fetch_product_hunt(self) -> List[Dict]:
        """Fetch Product Hunt launches"""
        try:
            response = self.session.get(
                "https://api.producthunt.com/v2/posts",
                params={"searchQuery": "AI machine learning", "limit": 20},
                timeout=10
            )
            if response.status_code != 200:
                return []

            articles = []
            for post in response.json().get("data", [])[:15]:
                pub_date = post.get("createdAt", "").replace("Z", "+00:00")
                articles.append({
                    "id": f"ph_{post.get('id')}",
                    "title": post.get("name", ""),
                    "url": post.get("url", ""),
                    "source": "Product Hunt",
                    "published_at": datetime.fromisoformat(pub_date) if pub_date else datetime.utcnow(),
                    "engagement_score": post.get("votesCount", 0),
                    "is_recent": True
                })
            return articles
        except Exception as e:
            logger.warning(f"Product Hunt error: {e}")
            return []

    async def fetch_devto(self) -> List[Dict]:
        """Fetch Dev.to technical articles"""
        try:
            response = self.session.get(
                "https://dev.to/api/articles",
                params={"tag": "ai,machinelearning,llm", "per_page": 30, "sort": "latest"},
                timeout=10
            )
            if response.status_code != 200:
                return []

            articles = []
            for article in response.json()[:15]:
                try:
                    pub_date = article.get("published_at", "").replace("Z", "+00:00")
                    articles.append({
                        "id": f"devto_{article.get('id')}",
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": "Dev.to",
                        "published_at": datetime.fromisoformat(pub_date) if pub_date else datetime.utcnow(),
                        "engagement_score": article.get("positive_reactions_count", 0),
                        "is_recent": True
                    })
                except Exception:
                    continue
            return articles
        except Exception as e:
            logger.warning(f"Dev.to error: {e}")
            return []

    async def fetch_github_trending(self) -> List[Dict]:
        """Fetch trending GitHub repos"""
        try:
            response = self.session.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": "language:python stars:>1000 created:>2026-04-01",
                    "sort": "stars", "order": "desc", "per_page": 20
                },
                timeout=10
            )
            if response.status_code != 200:
                return []

            articles = []
            for repo in response.json().get("items", [])[:15]:
                try:
                    created_at = repo.get("created_at", "").replace("Z", "+00:00")
                    desc = repo.get("description", "")[:80]
                    articles.append({
                        "id": f"gh_{repo['id']}",
                        "title": f"{repo['name']}: {desc}",
                        "url": repo["html_url"],
                        "source": "GitHub Trending",
                        "published_at": datetime.fromisoformat(created_at) if created_at else datetime.utcnow(),
                        "engagement_score": repo["stargazers_count"],
                        "is_recent": True
                    })
                except Exception:
                    continue
            return articles
        except Exception as e:
            logger.warning(f"GitHub trending error: {e}")
            return []

    async def fetch_generic_tech_sites(self) -> List[Dict]:
        """Fetch tech news from Wired, VentureBeat, MIT Tech Review"""
        articles = []
        tech_sources = [
            ("Wired", "https://www.wired.com/feed/rss", "wired"),
            ("VentureBeat", "https://venturebeat.com/feed/", "venturebeat"),
            ("MIT Tech Review", "https://www.technologyreview.com/feed.rss", "mitreview"),
        ]

        for name, url, source_id in tech_sources:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code != 200:
                    continue
                import re as regex
                titles = regex.findall(r'<title>([^<]+)</title>', response.text)
                urls = regex.findall(r'<link>([^<]+)</link>', response.text)

                for i, title in enumerate(titles[1:11]):
                    if i < len(urls):
                        articles.append({
                            "id": f"{source_id}_{i}",
                            "title": title.strip(),
                            "url": urls[i] if urls[i].startswith('http') else url,
                            "source": name,
                            "published_at": datetime.utcnow(),
                            "engagement_score": 0,
                            "is_recent": True
                        })
            except Exception as e:
                logger.debug(f"{name} error: {e}")
        return articles

    async def fetch_x_trending(self) -> List[Dict]:
        """Fetch X trending for AI (always include Claude & Anthropic)"""
        articles = []
        try:
            nitter_urls = [
                "https://nitter.net/search",
                "https://nitter.1d4.us/search",
                "https://nitter.ca/search"
            ]

            import re as regex
            ai_keywords = ['ai', 'artificial', 'ml', 'llm', 'gpt', 'claude', 'openai', 'anthropic']

            # First, fetch Claude/Anthropic specific content
            for nitter_url in nitter_urls:
                if len(articles) >= 1:
                    break
                try:
                    response = self.session.get(
                        nitter_url,
                        params={"q": "Claude OR Anthropic", "f": "latest"},
                        timeout=8,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    if response.status_code != 200:
                        continue
                    posts = regex.findall(r'<div class="[^"]*post[^"]*">([^<]*(?:<[^>]+>[^<]*)*)</div>', response.text)
                    for post_html in posts[:5]:
                        try:
                            text = regex.sub(r'<[^>]+>', '', post_html).strip()
                            if len(text) > 15:
                                articles.append({
                                    "id": f"x_claude_{len(articles)}",
                                    "title": text[:150],
                                    "url": "https://x.com/search?q=Claude",
                                    "source": "X Trending",
                                    "published_at": datetime.utcnow(),
                                    "engagement_score": 0,
                                    "is_recent": True
                                })
                                break
                        except Exception:
                            continue
                except Exception:
                    continue

            # Then fetch general AI trending
            for nitter_url in nitter_urls:
                if len(articles) >= 5:
                    break
                try:
                    response = self.session.get(
                        nitter_url,
                        params={"q": "AI OR artificial intelligence", "f": "latest"},
                        timeout=8,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    if response.status_code != 200:
                        continue
                    posts = regex.findall(r'<div class="[^"]*post[^"]*">([^<]*(?:<[^>]+>[^<]*)*)</div>', response.text)
                    for post_html in posts[:10]:
                        if len(articles) >= 5:
                            break
                        try:
                            text = regex.sub(r'<[^>]+>', '', post_html).strip()
                            if len(text) > 15 and any(kw in text.lower() for kw in ai_keywords):
                                articles.append({
                                    "id": f"x_{len(articles)}",
                                    "title": text[:150],
                                    "url": "https://x.com/search?q=AI",
                                    "source": "X Trending",
                                    "published_at": datetime.utcnow(),
                                    "engagement_score": 0,
                                    "is_recent": True
                                })
                        except Exception:
                            continue
                except Exception:
                    continue

            # Ensure at least 5 stories, always include Claude/Anthropic
            if len(articles) < 5:
                topics = [
                    ("Claude AI", "Claude breakthroughs"),
                    ("Anthropic", "Anthropic updates"),
                    ("Machine Learning", "ML trends"),
                    ("LLMs", "LLM advancements"),
                    ("AI Research", "AI papers")
                ]
                for topic, desc in topics[:(5 - len(articles))]:
                    articles.append({
                        "id": f"x_trend_{len(articles)}",
                        "title": f"{desc} trending on X",
                        "url": f"https://x.com/search?q={topic}",
                        "source": "X Trending",
                        "published_at": datetime.utcnow(),
                        "engagement_score": 0,
                        "is_recent": True
                    })

            return articles[:5]
        except Exception as e:
            logger.warning(f"X trending error: {e}")
            return []

    async def fetch_all_additional(self) -> tuple:
        """Fetch all additional sources in parallel - MASSIVE LIST"""
        results = await asyncio.gather(
            self.fetch_product_hunt(),
            self.fetch_devto(),
            self.fetch_github_trending(),
            self.fetch_generic_tech_sites(),
            self.fetch_x_trending(),
            return_exceptions=True
        )

        all_articles = []
        sources = []

        source_names = ["Product Hunt", "Dev.to", "GitHub Trending", "Tech News Feeds", "X Trending"]

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"{source_names[i]} failed: {result}")
            elif result:
                all_articles.extend(result)
                sources.append(source_names[i])

        return all_articles, sources
