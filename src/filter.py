"""Article filtering and relevance scoring"""

import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

# Keyword weighting for relevance scoring
KEYWORDS = {
    # Model releases (new AI models)
    "model_release": {
        "patterns": [
            r"GPT-\d+", r"Claude", r"Llama", r"Mixtral", r"Phi", r"Qwen",
            r"released", r"launch", r"announce.*available", r"beta", r"alpha",
            r"new model", r"model.*available"
        ],
        "weight": 0.35
    },
    # Anthropic specific news
    "anthropic_news": {
        "patterns": [
            r"Anthropic", r"Claude", r"Constitutional AI", r"Chroma",
            r"Contextual Bandits", r"RLHF", r"Mythic"
        ],
        "weight": 0.32
    },
    # OpenAI and OpenClaw
    "openai_news": {
        "patterns": [
            r"OpenAI", r"OpenClaw", r"o1", r"o3", r"GPT",
            r"ChatGPT", r"Sora", r"DALLE"
        ],
        "weight": 0.32
    },
    # Image models and generation
    "image_models": {
        "patterns": [
            r"Midjourney", r"DALL-E", r"Flux", r"Stable Diffusion",
            r"image.*model", r"image generation", r"text-to-image",
            r"vision.*model", r"multimodal"
        ],
        "weight": 0.28
    },
    # Leaks and rumors
    "leaks": {
        "patterns": [
            r"leak", r"coming soon", r"rumor", r"alleged", r"unreleased",
            r"codename", r"internal", r"roadmap", r"rumored"
        ],
        "weight": 0.25
    },
    # Benchmarks and records
    "benchmark": {
        "patterns": [
            r"SOTA", r"state-of-the-art", r"record", r"beats", r"outperforms",
            r"MMLU", r"HumanEval", r"benchmark", r"evaluation"
        ],
        "weight": 0.30
    },
    # Technical methods and frameworks
    "method": {
        "patterns": [
            r"fine-tun", r"LORA", r"RAG", r"prompt engineering", r"multimodal",
            r"chain-of-thought", r"scaling laws", r"mixture of experts", r"sparse",
            r"quantization", r"distillation", r"alignment", r"RLHF"
        ],
        "weight": 0.20
    },
    # Outages and issues
    "outages": {
        "patterns": [
            r"outage", r"down", r"offline", r"issue", r"bug",
            r"error", r"broken", r"failed", r"degradation"
        ],
        "weight": 0.22
    },
    # Company announcements
    "company": {
        "patterns": [
            r"OpenAI", r"Anthropic", r"Google", r"DeepMind", r"Meta",
            r"Mistral", r"Stability AI", r"xAI", r"Together AI"
        ],
        "weight": 0.10
    }
}

# Source credibility
CREDIBLE_SOURCES = {
    "OpenAI": 0.25,
    "Anthropic": 0.25,
    "Google DeepMind": 0.25,
    "Google": 0.23,
    "Meta AI": 0.20,
    "ArXiv": 0.20,
    "Hugging Face": 0.20,
    "TechCrunch": 0.15,
    "The Verge": 0.14,
    "HackerNews": 0.15,
    "Medium": 0.10,
    "Reddit": 0.08
}


class FilterEngine:
    """Ranks and filters articles by relevance"""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def calculate_score(self, article: Dict) -> float:
        """Calculate relevance score for an article (0-1.0)"""
        score = 0.0
        title = article.get("title", "").lower()
        source = article.get("source", "")

        # 1. Source credibility (0-0.25)
        for credible_source, weight in CREDIBLE_SOURCES.items():
            if credible_source.lower() in source.lower():
                score += weight
                break
        else:
            # Default for unknown sources
            score += 0.05

        # 2. Content type keywords (0-0.35)
        max_keyword_score = 0
        for category, config in KEYWORDS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, title, re.IGNORECASE):
                    keyword_score = config["weight"] / len(config["patterns"])
                    max_keyword_score = max(max_keyword_score, keyword_score)
                    break
        score += max_keyword_score

        # 3. Recency bonus (0-0.15)
        if article.get("is_recent"):
            score += 0.15

        # 4. Engagement metric if available (0-0.15)
        engagement = article.get("engagement_score", 0)
        if engagement > 1000:
            score += 0.15
        elif engagement > 100:
            score += 0.10
        elif engagement > 10:
            score += 0.05

        # 5. Title length bonus (0-0.05) - longer titles often contain more info
        title_len = len(article.get("title", ""))
        if title_len > 80:
            score += 0.05
        elif title_len > 60:
            score += 0.03

        # 6. Company-specific news boost (0-0.05) - when major companies announce
        major_companies = ["Anthropic", "OpenAI", "Google", "DeepMind", "Meta"]
        if any(company in title for company in major_companies):
            score += 0.05

        # 7. Major model announcement boost (0-0.10) - GPT-5, Claude 4, Gemini 3, etc.
        major_model_patterns = [
            r"GPT-[5-9]", r"Claude [4-9]", r"Gemini [3-9]", r"Llama [3-9]",
            r"o1", r"o3", r"Claude 4", r"GPT-5", r"Gemini 3"
        ]
        if any(re.search(pattern, title, re.IGNORECASE) for pattern in major_model_patterns):
            score += 0.10

        return min(1.0, score)

    def filter_and_rank(self, articles: List[Dict]) -> List[Dict]:
        """Filter articles by threshold and rank by score"""
        # Score all articles
        scored = []
        for article in articles:
            score = self.calculate_score(article)
            article["relevance_score"] = score
            scored.append((article, score))

        # Filter by threshold
        filtered = [a for a, score in scored if score >= self.threshold]

        # Sort by score (highest first)
        filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        logger.info(
            f"Filtered {len(articles)} articles → {len(filtered)} above threshold {self.threshold}"
        )
        return filtered

    def categorize(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize articles by content type with smart breaking news detection"""
        categories = {
            "models": [],
            "breaking": [],
            "research": [],
            "technical": [],
            "other": []
        }

        # Breaking news patterns (high priority)
        breaking_patterns = [
            r"GPT-[5-9]", r"Claude [4-9]", r"o1", r"o3", r"gemini [3-9]",
            r"announce.*available", r"just released", r"now available",
            r"exclusive.*announcement", r"official.*launch",
            r"Anthropic announces", r"OpenAI announces", r"Google announces",
            r"breakthrough", r"game-changing", r"revolutionary"
        ]

        for article in articles:
            title = article.get("title", "").lower()
            score = article.get("relevance_score", 0)

            # High-priority breaking news (score + keywords)
            if score > 0.85 and any(re.search(p, title, re.IGNORECASE) for p in breaking_patterns):
                categories["breaking"].append(article)
            # Model releases
            elif any(re.search(p, title, re.IGNORECASE) for p in KEYWORDS["model_release"]["patterns"]):
                categories["models"].append(article)
            # Leaks and rumors
            elif any(re.search(p, title, re.IGNORECASE) for p in KEYWORDS["leaks"]["patterns"]):
                categories["breaking"].append(article)
            # Research papers
            elif article.get("source") == "ArXiv":
                categories["research"].append(article)
            # Technical methods
            elif any(re.search(p, title, re.IGNORECASE) for p in KEYWORDS["method"]["patterns"]):
                categories["technical"].append(article)
            # Everything else
            else:
                categories["other"].append(article)

        return categories
