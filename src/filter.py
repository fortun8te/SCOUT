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
            r"GPT-?\d+", r"Claude\s?[\w\-]*", r"Llama\s?\d*", r"Mixtral",
            r"Gemini\s?[\w\.-]*", r"Phi\s?\d*", r"Qwen\s?[\w\.-]*",
            r"DeepSeek\s?[\w\.-]*", r"Kimi", r"Yi\s?\d*", r"Mistral\s?[\w\.-]*",
            r"Grok\s?[\w\.-]*", r"Granite\s?[\w\.-]*", r"ChatGLM",
            r"released", r"launch", r"announce.*available", r"beta", r"alpha",
            r"new model", r"model.*available", r"model drops", r"breaking.*release"
        ],
        "weight": 0.40  # YouTubers LOVE model releases
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

# AI-related required keywords - article MUST match at least one to pass
# Using regex with word boundaries to avoid false positives (e.g. "ai" in "paint")
AI_RELEVANCE_PATTERNS = [
    # Specific AI companies / labs
    r"\bopenai\b", r"\banthropic\b", r"\bdeepmind\b", r"\bhugging ?face\b",
    r"\bmistral\b", r"\bcohere\b", r"\bstability ?ai\b", r"\bxai\b",
    r"\bhiggsfield\b", r"\bperplexity\b", r"\bnvidia\b",
    r"\balibaba\b", r"\bbaidu\b", r"\bdeepseek\b", r"\bqwen\b", r"\bkimi\b",

    # Specific models
    r"\bclaude\b", r"\bchatgpt\b", r"\bgpt-?\d+", r"\bgemini\b", r"\bllama\b",
    r"\bgrok\b", r"\bo[13]\b", r"\bopus\b", r"\bsonnet\b", r"\bhaiku\b",
    r"\bmidjourney\b", r"\bdall-?e\b", r"\bflux\b", r"\bsora\b", r"\bveo\b",
    r"\bgranite\b", r"\bphi-?\d+", r"\bmixtral\b",

    # AI concepts / techniques
    r"\bartificial intelligence\b", r"\bmachine learning\b",
    r"\b(large )?language model\b", r"\bllm\b", r"\brag\b",
    r"\btransformer\b", r"\bdiffusion model\b", r"\breasoning model\b",
    r"\bmultimodal\b", r"\bvision model\b", r"\bfoundation model\b",
    r"\bfine[-\s]?tun", r"\binference\b",
    r"\bAI (agent|model|tool|framework|safety|alignment|breakthrough|startup|company|research|lab)\b",

    # AI products / tools
    r"\bcursor\b", r"\bcopilot\b", r"\bcodex\b", r"\bdevin\b",
    r"\bagentic\b", r"\bAI agent\b",
]


class FilterEngine:
    """Ranks and filters articles by relevance"""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def calculate_score(self, article: Dict) -> float:
        """Calculate relevance score for an article (0-1.0)"""
        title = article.get("title", "").lower()
        source = article.get("source", "")

        # HARD REQUIREMENT: article must match an AI pattern in title
        # Uses regex with word boundaries to avoid false positives
        has_ai_keyword = any(
            re.search(pattern, title, re.IGNORECASE)
            for pattern in AI_RELEVANCE_PATTERNS
        )
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

    # Specialized category patterns (money, controversy, people moves)
    FUNDING_PATTERNS = [
        r"raised \$\d", r"acquisition", r"acquires", r"acquired by",
        r"valued at", r"valuation", r"Series [A-E]\b", r"\bIPO\b",
        r"buyout", r"funding round", r"seed round", r"secures \$\d"
    ]
    DRAMA_PATTERNS = [
        r"lawsuit", r"\bsued\b", r"suing", r"controversy", r"scandal",
        r"fired", r"walked out", r"criticized", r"accused", r"\bbeef\b",
        r"feud", r"backlash"
    ]
    PEOPLE_PATTERNS = [
        r"\bjoins\b", r"\bleaves\b", r"departs", r"\bhired\b",
        r"\bfounded\b", r"co-?founder", r"new CEO", r"stepped down",
        r"resign", r"appointed"
    ]

    BREAKING_PATTERNS = [
        r"GPT-[5-9]", r"Claude [4-9]", r"o1", r"o3", r"gemini [3-9]",
        r"announce.*available", r"just released", r"now available",
        r"launches", r"unveils", r"exclusive", r"official launch",
        r"Anthropic announces", r"OpenAI announces", r"Google announces",
        r"breakthrough", r"game-changing", r"revolutionary",
        r"acquisition", r"funding", r"raised \$"
    ]

    CATEGORY_LABELS = {
        "breaking": "[BREAKING]",
        "models": "[RELEASE]",
        "agents": "[AGENT]",
        "funding": "[FUNDING]",
        "drama": "[DRAMA]",
        "people": "[PEOPLE]",
        "research": "[PAPER]",
        "technical": "[TECH]",
        "other": "",
    }

    def _classify(self, article: Dict) -> str:
        """Return the category key an article belongs to.

        Order of precedence matches the public digest:
        breaking > models > agents > funding > drama > people >
        research > technical > other.
        """
        title = article.get("title", "").lower()
        source = article.get("source", "")
        score = article.get("relevance_score", 0)

        def matches(patterns):
            return any(re.search(p, title, re.IGNORECASE) for p in patterns)

        if score > 0.7 and matches(self.BREAKING_PATTERNS):
            return "breaking"
        if matches(KEYWORDS["model_release"]["patterns"]):
            return "models"
        if matches(KEYWORDS["agents"]["patterns"]):
            return "agents"
        if matches(self.FUNDING_PATTERNS):
            return "funding"
        if matches(self.DRAMA_PATTERNS):
            return "drama"
        if matches(self.PEOPLE_PATTERNS):
            return "people"
        if matches(KEYWORDS["leaks"]["patterns"]):
            return "breaking"
        if matches(KEYWORDS["reasoning"]["patterns"]):
            return "models"
        if "ArXiv" in source or "research" in title or "paper" in title:
            return "research"
        if matches(KEYWORDS["method"]["patterns"]):
            return "technical"
        return "other"

    def categorize(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize articles by content type with smart breaking news detection"""
        categories = {key: [] for key in self.CATEGORY_LABELS}
        for article in articles:
            categories[self._classify(article)].append(article)
        return categories

    def detect_label(self, article: Dict) -> str:
        """Return a bracketed prefix label for an article headline.

        Uses the article's existing ``category`` if set, otherwise classifies
        on the fly. Returns an empty string for 'other' / unclassified.
        """
        category = article.get("category")
        if category not in self.CATEGORY_LABELS:
            category = self._classify(article)
        return self.CATEGORY_LABELS[category]
