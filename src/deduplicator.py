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

    def detect_trending(
        self, articles: List[Dict], threshold: float = 0.75
    ) -> Dict[int, int]:
        """
        Detect trending stories covered by multiple sources.

        Groups articles by title similarity and annotates the
        highest-scoring representative of each cluster with
        ``trending_source_count`` — how many distinct sources
        covered the story.

        Args:
            articles: List of articles (typically already deduplicated)
            threshold: 0-1.0, title similarity above this means
                articles cover the same story

        Returns:
            Dict mapping id(article) -> source_count for the
            representative article of each cluster.
        """
        if len(articles) < 2:
            return {id(a): 1 for a in articles}

        clusters: List[List[Dict]] = []

        for article in articles:
            title = article.get("title", "").lower()
            placed = False

            for cluster in clusters:
                rep_title = cluster[0].get("title", "").lower()
                similarity = self._calculate_similarity(title, rep_title)
                if similarity >= threshold:
                    cluster.append(article)
                    placed = True
                    break

            if not placed:
                clusters.append([article])

        trending: Dict[int, int] = {}

        for cluster in clusters:
            # Count distinct sources in cluster
            sources = {a.get("source", "") for a in cluster if a.get("source")}
            source_count = len(sources)

            # Representative = highest relevance_score (fallback 0)
            representative = max(
                cluster,
                key=lambda a: a.get("relevance_score", 0) or 0,
            )
            representative["trending_source_count"] = source_count
            trending[id(representative)] = source_count

            if source_count > 1:
                logger.debug(
                    f"[TRENDING] {source_count} sources: "
                    f"{representative.get('title', '')[:60]}..."
                )

        return trending

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
