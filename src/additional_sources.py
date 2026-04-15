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
        """Fetch from Product Hunt (tech launches)"""
        try:
            response = self.session.get(
                "https://api.producthunt.com/v2/posts",
                params={
                    "searchQuery": "AI machine learning",
                    "limit": 20
                },
                timeout=10
            )

            if response.status_code != 200:
                return []

            posts = response.json().get("data", [])
            articles = []

            for post in posts[:15]:
                articles.append({
                    "id": f"ph_{post.get('id')}",
                    "title": post.get("name", ""),
                    "url": post.get("url", ""),
                    "source": "Product Hunt",
                    "published_at": datetime.fromisoformat(
                        post.get("createdAt", "").replace("Z", "+00:00")
                    ) if post.get("createdAt") else datetime.utcnow(),
                    "engagement_score": post.get("votesCount", 0),
                    "is_recent": True
                })

            return articles
        except Exception as e:
            logger.warning(f"Product Hunt error: {e}")
            return []

    async def fetch_devto(self) -> List[Dict]:
        """Fetch from Dev.to (technical articles)"""
        try:
            response = self.session.get(
                "https://dev.to/api/articles",
                params={
                    "tag": "ai,machinelearning,llm",
                    "per_page": 30,
                    "sort": "latest"
                },
                timeout=10
            )

            if response.status_code != 200:
                return []

            articles = []
            for article in response.json()[:15]:
                try:
                    pub_date = article.get("published_at", "")
                    if pub_date:
                        published_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    else:
                        published_at = datetime.utcnow()

                    articles.append({
                        "id": f"devto_{article.get('id')}",
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": "Dev.to",
                        "published_at": published_at,
                        "engagement_score": article.get("positive_reactions_count", 0),
                        "is_recent": True
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse Dev.to article: {e}")
                    continue

            return articles
        except Exception as e:
            logger.warning(f"Dev.to error: {e}")
            return []

    async def fetch_github_trending(self) -> List[Dict]:
        """Fetch trending AI/ML repos from GitHub"""
        try:
            response = self.session.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": "language:python stars:>1000 created:>2026-04-01",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 20
                },
                timeout=10
            )

            if response.status_code != 200:
                return []

            articles = []
            for repo in response.json().get("items", [])[:15]:
                try:
                    created_at = repo.get("created_at", "")
                    if created_at:
                        published_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        published_at = datetime.utcnow()

                    articles.append({
                        "id": f"gh_{repo['id']}",
                        "title": f"{repo['name']}: {repo.get('description', '')[:80]}",
                        "url": repo["html_url"],
                        "source": "GitHub Trending",
                        "published_at": published_at,
                        "engagement_score": repo["stargazers_count"],
                        "is_recent": True
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse GitHub repo: {e}")
                    continue

            return articles
        except Exception as e:
            logger.warning(f"GitHub trending error: {e}")
            return []

    async def fetch_generic_tech_sites(self) -> List[Dict]:
        """Fetch from generic tech news sites using search/scraping"""
        articles = []

        # Common tech news endpoints
        tech_sources = [
            ("Wired", "https://www.wired.com/feed/rss", "wired"),
            ("VentureBeat", "https://venturebeat.com/feed/", "venturebeat"),
            ("MIT Tech Review", "https://www.technologyreview.com/feed.rss", "mitreview"),
        ]

        for name, url, source_id in tech_sources:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    # Basic RSS parsing
                    import re as regex
                    titles = regex.findall(r'<title>([^<]+)</title>', response.text)
                    urls = regex.findall(r'<link>([^<]+)</link>', response.text)

                    for i, title in enumerate(titles[1:11]):  # Skip feed title
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
                logger.debug(f"{name} fetch error: {e}")
                continue

        return articles

    async def fetch_all_additional(self) -> tuple:
        """Fetch all additional sources in parallel - MASSIVE LIST"""
        results = await asyncio.gather(
            self.fetch_product_hunt(),
            self.fetch_devto(),
            self.fetch_github_trending(),
            self.fetch_generic_tech_sites(),
            return_exceptions=True
        )

        all_articles = []
        sources = []

        source_names = ["Product Hunt", "Dev.to", "GitHub Trending", "Tech News Feeds"]

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"{source_names[i]} failed: {result}")
            elif result:
                all_articles.extend(result)
                sources.append(source_names[i])

        return all_articles, sources
