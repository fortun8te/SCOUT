"""Full article content extraction from article URLs.

RSS descriptions are often truncated or just titles. Fetching the actual
article HTML and extracting the main text produces much richer summaries.
"""

import asyncio
import logging
import re
from typing import Dict

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (compatible; SCOUT-NewsBot/1.0; "
    "+https://github.com/fortun8te/scout)"
)

_STRIP_TAGS = ("script", "style", "nav", "footer", "header", "aside", "form")
_AD_SELECTOR = ",".join((
    '[class*="ad-"]', '[class*="-ad"]', '[id*="ad-"]', '[id*="-ad"]',
    '[class*="advert"]', '[class*="promo"]', '[class*="sponsor"]',
    '[class*="newsletter"]', '[class*="subscribe"]', '[class*="popup"]',
))
_MAX_OUTPUT = 2000
_WS_RE = re.compile(r"\s+")


class ContentExtractor:
    """Fetch an article page and extract its main text."""

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}

    async def extract(self, url: str, timeout: int = 10) -> str:
        """Fetch `url` and return up to 2000 chars of main article text.

        Returns empty string on any error. Results are cached per URL.
        `timeout` is capped at 5 seconds — we prefer to abandon slow pages.
        """
        if not url:
            return ""
        if url in self._cache:
            return self._cache[url]

        effective_timeout = min(timeout, 5)
        try:
            html = await self._fetch(url, effective_timeout)
            if not html:
                self._cache[url] = ""
                return ""
            text = self._extract_text(html)
            self._cache[url] = text
            return text
        except Exception as e:
            logger.debug(f"[EXTRACT] Failed for {url}: {e}")
            self._cache[url] = ""
            return ""

    async def _fetch(self, url: str, timeout: int) -> str:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,*/*"}
        async with aiohttp.ClientSession(timeout=client_timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    logger.debug(f"[EXTRACT] HTTP {resp.status} for {url}")
                    return ""
                return await resp.text(errors="ignore")

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        # Strip unwanted tags entirely
        for tag in soup(list(_STRIP_TAGS)):
            tag.decompose()

        # Strip ad-like elements
        for el in soup.select(_AD_SELECTOR):
            el.decompose()

        # Priority order: article, main, .post*, .content*, body
        container = (
            soup.find("article")
            or soup.find("main")
            or soup.select_one('div[class*="post"]')
            or soup.select_one('div[class*="content"]')
            or soup.body
        )
        if container is None:
            return ""

        text = container.get_text(separator=" ", strip=True)
        text = _WS_RE.sub(" ", text).strip()
        if len(text) > _MAX_OUTPUT:
            text = text[:_MAX_OUTPUT].rsplit(" ", 1)[0]
        return text


# Module-level singleton
content_extractor = ContentExtractor()
