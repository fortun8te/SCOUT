"""AI-powered summarization using free LLM APIs"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SummarizerEngine:
    """Generate article summaries using free LLM APIs"""

    def __init__(self, provider: str = "gemini", api_key: Optional[str] = None):
        """
        Initialize summarizer

        Args:
            provider: 'gemini' (Google), 'groq', or None (disabled)
            api_key: API key for the provider (if not in environment)
        """
        self.provider = provider
        self.api_key = api_key
        self.enabled = provider is not None and api_key is not None

    def summarize(self, text: str, max_length: int = 150) -> Optional[str]:
        """
        Summarize article text to 1-2 sentences

        Args:
            text: Full article text to summarize
            max_length: Maximum summary length in chars

        Returns:
            Summary string or None if summarization disabled
        """
        if not self.enabled:
            return None

        if not text or len(text) < 100:
            return None  # Too short to summarize

        try:
            if self.provider == "gemini":
                return self._summarize_gemini(text, max_length)
            elif self.provider == "groq":
                return self._summarize_groq(text, max_length)
            elif self.provider == "claude":
                return self._summarize_claude(text, max_length)
        except Exception as e:
            logger.warning(f"Summarization failed: {e}")
            return None

    def _summarize_gemini(self, text: str, max_length: int) -> Optional[str]:
        """Summarize using Google Gemini API (free tier: 1,500 req/day)"""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            response = model.generate_content(
                f"""Summarize this news article in 1-2 sentences ({max_length} chars max),
                focusing on key facts and impact:

{text[:2000]}""",
                generation_config={"max_output_tokens": 100}
            )

            summary = response.text.strip()
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."

            return summary
        except Exception as e:
            logger.error(f"Gemini summarization error: {e}")
            return None

    def _summarize_groq(self, text: str, max_length: int) -> Optional[str]:
        """Summarize using Groq API (free tier: 30 req/min)"""
        try:
            from groq import Groq

            client = Groq(api_key=self.api_key)

            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"""Summarize this news article in 1-2 sentences
                        ({max_length} chars max):

{text[:2000]}"""
                    }
                ],
                model="mixtral-8x7b-32768",
                max_tokens=100,
                temperature=0.3
            )

            summary = chat_completion.choices[0].message.content.strip()
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."

            return summary
        except Exception as e:
            logger.error(f"Groq summarization error: {e}")
            return None

    def _summarize_claude(self, text: str, max_length: int) -> Optional[str]:
        """Summarize using Claude Haiku API (cheapest paid option)"""
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.api_key)

            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Summarize this news article in 1-2 sentences ({max_length} chars max),
                        focusing on key facts and impact:

{text[:2000]}"""
                    }
                ]
            )

            summary = message.content[0].text.strip()
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."

            return summary
        except Exception as e:
            logger.error(f"Claude summarization error: {e}")
            return None

    @staticmethod
    def extract_snippet(text: str, length: int = 200) -> str:
        """Extract first N chars as fallback snippet"""
        if len(text) > length:
            return text[:length] + "..."
        return text
