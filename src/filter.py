"""Article filtering and relevance scoring"""

import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

# Keyword weighting for relevance scoring
KEYWORDS = {
    # Model releases (new AI models) - SUPER TRENDING
    "model_release": {
        "patterns": [
            r"GPT-\d+", r"Claude", r"Llama", r"Mixtral", r"Phi", r"Qwen",
            r"released", r"launch", r"announce.*available", r"beta", r"alpha",
            r"new model", r"model.*available", r"model drops", r"breaking.*release"
        ],
        "weight": 0.40  # Increased - YouTubers LOVE model releases
    },
    # Reasoning/Thinking models (o1, o3, Chain of Thought) - HOT TOPIC
    "reasoning": {
        "patterns": [
            r"o1", r"o3", r"reasoning model", r"thinking model", r"extended thinking",
            r"chain.?of.?thought", r"structured reasoning", r"test.?time compute",
            r"inference scaling", r"reasoning.*breakthrough"
        ],
        "weight": 0.38  # Very high - YouTubers talk about this constantly
    },
    # Anthropic specific news
    "anthropic_news": {
        "patterns": [
            r"Anthropic", r"Claude", r"Constitutional AI", r"Chroma",
            r"Contextual Bandits", r"RLHF", r"Mythic", r"Claude.*release"
        ],
        "weight": 0.35
    },
    # OpenAI and major releases
    "openai_news": {
        "patterns": [
            r"OpenAI", r"OpenClaw", r"o1", r"o3", r"GPT",
            r"ChatGPT", r"Sora", r"DALLE", r"GPT-?5", r"OpenAI.*announce"
        ],
        "weight": 0.35
    },
    # Agentic AI and Agents - TRENDING NOW
    "agents": {
        "patterns": [
            r"agent", r"agentic", r"autonomous.*agent", r"AI agent", r"tool.*use",
            r"function calling", r"multi-step", r"agent framework", r"prompt.*agent"
        ],
        "weight": 0.32  # Big topic in AI community
    },
    # Multimodal and vision - BIG DEAL
    "multimodal": {
        "patterns": [
            r"multimodal", r"vision.*model", r"image.*understanding", r"video.*model",
            r"audio.*model", r"voice.*AI", r"visual.*reasoning", r"seeing",
            r"video generation", r"video.*AI"
        ],
        "weight": 0.30
    },
    # Image models and generation
    "image_models": {
        "patterns": [
            r"Midjourney", r"DALL-E", r"Flux", r"Stable Diffusion",
            r"image.*model", r"image generation", r"text-to-image",
            r"image.*breakthrough"
        ],
        "weight": 0.28
    },
    # Leaks and rumors (YouTubers LOVE this)
    "leaks": {
        "patterns": [
            r"leak", r"coming soon", r"rumor", r"alleged", r"unreleased",
            r"codename", r"internal", r"roadmap", r"rumored", r"exclusive"
        ],
        "weight": 0.28  # Increased - very clickable
    },
    # Benchmarks and records
    "benchmark": {
        "patterns": [
            r"SOTA", r"state-of-the-art", r"record", r"beats", r"outperforms",
            r"MMLU", r"HumanEval", r"benchmark", r"evaluation", r"best.*performance"
        ],
        "weight": 0.32
    },
    # Fine-tuning and training
    "training": {
        "patterns": [
            r"fine.?tun", r"training.*AI", r"train.*model", r"LORA", r"LoRA",
            r"custom.*model", r"personali[sz]ed.*AI", r"distillation"
        ],
        "weight": 0.26
    },
    # Technical methods and frameworks
    "method": {
        "patterns": [
            r"RAG", r"retrieval", r"prompt engineering", r"prompting",
            r"scaling laws", r"mixture of experts", r"sparse models",
            r"quantization", r"alignment", r"RLHF", r"Constitutional AI"
        ],
        "weight": 0.22
    },
    # AI Safety and Alignment
    "safety": {
        "patterns": [
            r"safety", r"alignment", r"jailbreak", r"adversarial",
            r"harmful", r"bias", r"fairness", r"trustworthy",
            r"AGI.*safety", r"x-risk"
        ],
        "weight": 0.24
    },
    # Compute and Hardware
    "compute": {
        "patterns": [
            r"GPU", r"TPU", r"computing power", r"inference.*speed",
            r"faster.*AI", r"optimization", r"efficient.*model",
            r"edge.*AI", r"mobile.*AI", r"on.*device"
        ],
        "weight": 0.20
    },
    # Outages and issues
    "outages": {
        "patterns": [
            r"outage", r"down", r"offline", r"issue", r"bug",
            r"error", r"broken", r"failed", r"degradation", r"API.*broken"
        ],
        "weight": 0.18
    },
    # Company announcements
    "company": {
        "patterns": [
            r"OpenAI", r"Anthropic", r"Google", r"DeepMind", r"Meta",
            r"Mistral", r"Stability AI", r"xAI", r"Together AI", r"Hugging Face"
        ],
        "weight": 0.12
    }
}

# Source credibility - AI-focused outlets boosted
CREDIBLE_SOURCES = {
    # Official AI company blogs - MAXIMUM trust
    "OpenAI": 0.30,
    "Anthropic": 0.30,
    "DeepMind": 0.30,
    "Google AI": 0.28,
    "Meta AI": 0.25,
    "Hugging Face": 0.25,
    "Mistral": 0.25,
    "Stability": 0.23,
    "Cohere": 0.23,

    # AI-focused news sections
    "TechCrunch AI": 0.22,
    "VentureBeat AI": 0.22,
    "Verge - AI": 0.22,
    "Ars Technica AI": 0.20,
    "MIT Tech Review AI": 0.22,
    "Wired AI": 0.20,

    # AI newsletters
    "The Batch": 0.22,
    "Ahead of AI": 0.20,
    "Import AI": 0.22,
    "Latent Space": 0.20,
    "Algorithmic Bridge": 0.18,

    # AI YouTubers
    "Two Minute Papers": 0.18,
    "AI Explained": 0.22,
    "Matt Wolfe": 0.18,
    "Wes Roth": 0.16,
    "Yannic Kilcher": 0.20,
    "Fireship": 0.15,

    # Generic tech (lower priority)
    "Hacker News": 0.12,
    "Reddit": 0.08,
    "ArXiv": 0.08,  # Lowered - user doesn't want research papers
}

# AI-related required keywords - article MUST contain at least one to pass
AI_RELEVANCE_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "ml",
    "openai", "anthropic", "claude", "gpt", "chatgpt",
    "google", "deepmind", "gemini", "meta", "llama",
    "mistral", "qwen", "alibaba", "hugging face", "huggingface",
    "grok", "xai", "higgsfield", "stability", "cohere",
    "model", "llm", "language model", "agent", "agentic",
    "neural network", "transformer", "diffusion",
    "reasoning", "multimodal", "vision model", "rag",
    "fine-tun", "training", "inference", "alignment",
    "openclaw", "opus", "sonnet", "haiku", "o1", "o3",
    "midjourney", "dall-e", "flux", "sora", "veo",
    "copilot", "cursor", "codex", "devin",
]


class FilterEngine:
    """Ranks and filters articles by relevance"""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def calculate_score(self, article: Dict) -> float:
        """Calculate relevance score for an article (0-1.0)"""
        title = article.get("title", "").lower()
        source = article.get("source", "")

        # HARD REQUIREMENT: article must mention AI/ML topic in title
        # Otherwise score = 0 (will be filtered out)
        has_ai_keyword = any(kw in title for kw in AI_RELEVANCE_KEYWORDS)
        if not has_ai_keyword:
            return 0.0

        score = 0.0

        # 1. Source credibility (0-0.30)
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

        # 6. Company-specific news boost (0-0.08) - when major companies announce
        major_companies = ["Anthropic", "OpenAI", "Google", "DeepMind", "Meta", "xAI", "Mistral"]
        if any(company in title for company in major_companies):
            score += 0.08

        # 7. Major model announcement boost (0-0.12) - GPT-5, Claude 4, o1, o3, etc.
        major_model_patterns = [
            r"GPT-[5-9]", r"Claude [4-9]", r"Gemini [3-9]", r"Llama [3-9]",
            r"o1", r"o3", r"Claude 4", r"GPT-5", r"Gemini 3", r"Grok",
            r"reasoning model", r"thinking model"
        ]
        if any(re.search(pattern, title, re.IGNORECASE) for pattern in major_model_patterns):
            score += 0.12

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
            "breaking": [],
            "models": [],
            "agents": [],
            "research": [],
            "technical": [],
            "other": []
        }

        # Breaking news patterns (high priority)
        breaking_patterns = [
            r"GPT-[5-9]", r"Claude [4-9]", r"o1", r"o3", r"gemini [3-9]",
            r"announce.*available", r"just released", r"now available",
            r"launches", r"unveils", r"exclusive", r"official launch",
            r"Anthropic announces", r"OpenAI announces", r"Google announces",
            r"breakthrough", r"game-changing", r"revolutionary",
            r"acquisition", r"funding", r"raised \$"
        ]

        for article in articles:
            title = article.get("title", "").lower()
            source = article.get("source", "")
            score = article.get("relevance_score", 0)

            # High-priority breaking news (score + keywords)
            if score > 0.7 and any(re.search(p, title, re.IGNORECASE) for p in breaking_patterns):
                categories["breaking"].append(article)
            # Model releases (Claude, GPT, Gemini, Llama, etc.)
            elif any(re.search(p, title, re.IGNORECASE) for p in KEYWORDS["model_release"]["patterns"]):
                categories["models"].append(article)
            # Agents and agentic AI
            elif any(re.search(p, title, re.IGNORECASE) for p in KEYWORDS["agents"]["patterns"]):
                categories["agents"].append(article)
            # Leaks and rumors → breaking
            elif any(re.search(p, title, re.IGNORECASE) for p in KEYWORDS["leaks"]["patterns"]):
                categories["breaking"].append(article)
            # Reasoning models → models
            elif any(re.search(p, title, re.IGNORECASE) for p in KEYWORDS["reasoning"]["patterns"]):
                categories["models"].append(article)
            # Research papers
            elif "ArXiv" in source or "research" in title or "paper" in title:
                categories["research"].append(article)
            # Technical methods
            elif any(re.search(p, title, re.IGNORECASE) for p in KEYWORDS["method"]["patterns"]):
                categories["technical"].append(article)
            # Everything else
            else:
                categories["other"].append(article)

        return categories
