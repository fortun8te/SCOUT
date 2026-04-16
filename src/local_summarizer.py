"""Zero-API extractive summarizer used when Gemini/Groq quotas are exhausted.

Implements a simple TextRank-lite using only the Python standard library,
so the bot can always produce a usable summary even when every external
LLM provider is rate-limited or offline.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "while", "of", "at", "by",
    "for", "with", "about", "against", "between", "into", "through", "to",
    "from", "in", "on", "off", "over", "under", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "can", "may", "might", "this", "that", "these",
    "those", "it", "its", "as", "than", "then", "so", "such", "also",
}

_BOOST_KEYWORDS = {
    "ai", "model", "gpt", "claude", "gemini", "anthropic", "openai",
    "launch", "release", "announce", "breakthrough",
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_WORD_RE = re.compile(r"[a-z0-9]+")


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences using a simple regex heuristic."""
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _tokenize(sentence: str) -> List[str]:
    """Lowercase + strip punctuation; stdlib only."""
    return _WORD_RE.findall(sentence.lower())


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


class LocalSummarizer:
    """Extractive summarizer with no external dependencies."""

    def summarize(
        self,
        text: str,
        max_sentences: int = 2,
        max_chars: int = 280,
    ) -> str:
        """Return an extractive summary of ``text``.

        Args:
            text: Input text to summarize.
            max_sentences: Maximum sentences to keep in original order.
            max_chars: Hard character cap on the returned summary.
        """
        if not text:
            return ""

        text = text.strip()
        if not text:
            return ""

        if len(text) <= max_chars:
            return text

        sentences = _split_sentences(text)
        if not sentences:
            return _truncate(text, max_chars)

        if len(sentences) <= max_sentences:
            return _truncate(" ".join(sentences), max_chars)

        # Build word frequency table over non-stopword tokens.
        freq: dict[str, int] = {}
        sentence_tokens: List[List[str]] = []
        for sent in sentences:
            tokens = [t for t in _tokenize(sent) if t not in _STOPWORDS]
            sentence_tokens.append(tokens)
            for tok in tokens:
                freq[tok] = freq.get(tok, 0) + 1

        if not freq:
            # Nothing meaningful — fall back to first sentences.
            return _truncate(" ".join(sentences[:max_sentences]), max_chars)

        # Score each sentence: sum of token freqs, length-normalized, with keyword boost.
        scored: List[tuple[int, float]] = []
        for idx, tokens in enumerate(sentence_tokens):
            if not tokens:
                scored.append((idx, 0.0))
                continue
            base = sum(freq[t] for t in tokens) / len(tokens)
            boost = 1.0 + 0.5 * sum(1 for t in tokens if t in _BOOST_KEYWORDS)
            scored.append((idx, base * boost))

        # Pick top N by score, then restore original order.
        top = sorted(scored, key=lambda x: x[1], reverse=True)[:max_sentences]
        top_indices = sorted(i for i, _ in top)
        summary = _truncate(" ".join(sentences[i] for i in top_indices), max_chars)
        logger.debug("LocalSummarizer picked sentences %s (len=%d)", top_indices, len(summary))
        return summary


def summarize_locally(
    text: str,
    max_sentences: int = 2,
    max_chars: int = 280,
) -> str:
    """Module-level convenience wrapper around ``LocalSummarizer``."""
    return LocalSummarizer().summarize(text, max_sentences=max_sentences, max_chars=max_chars)


class FallbackSummarizer:
    """Drop-in replacement for ``SummarizerEngine`` with no API calls.

    Mirrors the public interface used by the rest of SCOUT so it can be
    swapped in when every remote provider is exhausted.
    """

    def __init__(self) -> None:
        self.provider = "local"
        self.enabled = True
        self._impl = LocalSummarizer()

    def summarize(self, text: str, max_length: int = 150) -> Optional[str]:
        """Summarize ``text`` using the local extractive algorithm."""
        if not text or len(text) < 100:
            return None
        try:
            return self._impl.summarize(text, max_sentences=2, max_chars=max_length)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Local summarization failed: {e}")
            return None

    @staticmethod
    def extract_snippet(text: str, length: int = 200) -> str:
        """Extract first N chars as fallback snippet."""
        if len(text) > length:
            return text[:length] + "..."
        return text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    sample = (
        "OpenAI announced the release of GPT-5 today, calling it a major breakthrough "
        "in reasoning. The new model outperforms GPT-4 on math, coding, and scientific "
        "benchmarks. Anthropic and Google are expected to respond with updates to Claude "
        "and Gemini in the coming weeks. Industry analysts say the launch intensifies the "
        "AI race and could push enterprise adoption higher. Shares of several chipmakers "
        "rose on the news."
    )
    print("=== LocalSummarizer ===")
    print(summarize_locally(sample))
    print("=== FallbackSummarizer ===")
    print(FallbackSummarizer().summarize(sample))
