"""Semantic deduplication using string similarity"""

import logging
from difflib import SequenceMatcher
from typing import List, Dict

logger = logging.getLogger(__name__)


class DeduplicatorEngine:
    """Detect and remove semantically similar articles"""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize deduplicator

        Args:
            similarity_threshold: 0-1.0, articles above this are duplicates
        """
        self.threshold = similarity_threshold

    def find_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove semantically similar articles from the same run

        Args:
            articles: List of articles to deduplicate

        Returns:
            List with near-duplicates removed
        """
        if len(articles) < 2:
            return articles

        unique = []
        skipped = 0

        for article in articles:
            is_duplicate = False
            article_title = article.get("title", "").lower()

            # Check against all articles we've kept
            for kept in unique:
                kept_title = kept.get("title", "").lower()
                similarity = self._calculate_similarity(article_title, kept_title)

                if similarity >= self.threshold:
                    logger.debug(
                        f"[DEDUP] Skipped duplicate "
                        f"({similarity:.1%}): {article_title[:50]}..."
                    )
                    is_duplicate = True
                    skipped += 1
                    break

            if not is_duplicate:
                unique.append(article)

        if skipped > 0:
            logger.info(f"[DEDUP] Removed {skipped} near-duplicate articles")

        return unique

    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """Calculate string similarity using SequenceMatcher"""
        return SequenceMatcher(None, text1, text2).ratio()

    @staticmethod
    def simple_hash(title: str) -> str:
        """Create simple hash of title for fast comparison"""
        # Extract first letters of each word for quick duplicate detection
        words = title.lower().split()[:5]  # First 5 words
        return "".join(w[0] if w else "" for w in words)
