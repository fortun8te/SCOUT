"""Quality assurance - filter out BS garbage"""

import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


class QualityChecker:
    """Detect and filter low-quality, spam, clickbait articles"""

    # Spam/garbage patterns
    SPAM_PATTERNS = [
        r"click here",
        r"you won't believe",
        r"doctors hate",
        r"one weird trick",
        r"this will blow your mind",
        r"shocking.*revealed",
        r"leaked footage",
        r"\[ad\]",
        r"sponsored",
        r"affiliate",
    ]

    # Clickbait title patterns
    CLICKBAIT_PATTERNS = [
        r"^(what|why|how).{0,50}(\?|will shock you)",
        r"\d+\s+(secret|trick|hack|tip)s?",
        r"(destroyed|slammed|savages?|destroys?|blasts?)",
        r"absolutely.*must.*see",
    ]

    # Low-quality source patterns
    LOW_QUALITY_SOURCES = [
        "medium.com/tag",
        "linkedin.com/pulse",
        "dev.to/feed",
        "substack.com",
        "patreon",
        "kickstarter",
    ]

    # Minimum quality thresholds
    MIN_TITLE_LENGTH = 20
    MAX_TITLE_LENGTH = 200
    MIN_RELEVANCE_SCORE = 0.60  # Increased from 0.50

    def check_quality(self, article: Dict) -> tuple[bool, str]:
        """
        Check if article passes quality checks

        Returns:
            (is_quality: bool, reason: str)
        """
        title = article.get("title", "").lower()
        url = article.get("url", "").lower()
        source = article.get("source", "").lower()
        score = article.get("relevance_score", 0)

        # Check 1: Relevance score
        if score < self.MIN_RELEVANCE_SCORE:
            return False, f"Low relevance score: {score:.2f}"

        # Check 2: Title quality
        if len(title) < self.MIN_TITLE_LENGTH:
            return False, "Title too short"
        if len(title) > self.MAX_TITLE_LENGTH:
            return False, "Title too long"

        # Check 3: Spam patterns
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return False, f"Spam pattern detected: {pattern}"

        # Check 4: Clickbait patterns
        for pattern in self.CLICKBAIT_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return False, "Clickbait title detected"

        # Check 5: Low-quality sources
        for bad_source in self.LOW_QUALITY_SOURCES:
            if bad_source in url:
                return False, f"Low-quality source: {bad_source}"

        # Check 6: Content exists
        content = article.get("content", "") or article.get("summary", "")
        if not content or len(content) < 50:
            return False, "Insufficient content"

        # Check 7: Duplicate/near-duplicate with previous
        # (already handled by deduplicator)

        return True, "Passed quality checks"

    def filter_articles(self, articles: List[Dict]) -> List[Dict]:
        """Filter articles, removing low-quality ones"""
        quality_articles = []
        rejected = 0

        for article in articles:
            is_quality, reason = self.check_quality(article)

            if is_quality:
                quality_articles.append(article)
            else:
                rejected += 1
                logger.debug(f"[QUALITY] Rejected: {article.get('title', '')[:60]}... ({reason})")

        if rejected > 0:
            logger.info(f"[QUALITY] Rejected {rejected} low-quality articles")

        return quality_articles
