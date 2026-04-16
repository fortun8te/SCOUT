# Claude Code Routine Setup

Use this when creating the routine at claude.ai/code/routines

---

## Configuration

Name: SCOUT News Monitor
Schedule: 0 */6 * * * (every 6 hours)
Model: Claude 3.5 Sonnet
Repositories: Your SCOUT repo
Network Access: Trusted

---

## Entrypoint

Point the Routine command at `bash scripts/routine_entrypoint.sh` instead of `python src/monitor.py` — it guarantees no git operations occur. The wrapper sets `GIT_TERMINAL_PROMPT=0`, `cd`s into the repo root, and `exec`s the monitor so no post-run shell steps fire.

---

## Prompt

Execute the SCOUT AI news monitor autonomously. Run: `bash scripts/routine_entrypoint.sh`

The script will:
1. Fetch news from 8+ sources in parallel (HackerNews, ArXiv, Reddit, Bluesky, Product Hunt, Dev.to, GitHub, NewsAPI)
2. Filter articles by relevance (0.25 threshold minimum)
3. Remove spam/clickbait/low-quality content
4. Categorize: models, breaking news, research, technical, other
5. Send high-priority breaking news immediately via Discord DM
6. Send full batch digest with rich embeds every 6 hours
7. Track analytics, trending keywords, and discovery rates
8. Auto-deduplicate using semantic similarity + git state
9. Send error alerts to Discord if anything fails

Do NOT ask for confirmation. Execute the script, capture all output, and let it complete. Environment variables (DISCORD_BOT_TOKEN, DISCORD_USER_ID) are loaded from .env file automatically.

---

## Setup Steps

1. Go to claude.ai/code/routines
2. Create new routine
3. Name: SCOUT
4. Command: `bash scripts/routine_entrypoint.sh`
5. Schedule: `0 */6 * * * ` (every 6 hours UTC = 4 times/day)
6. Add environment variables (if using routine UI):
   - DISCORD_BOT_TOKEN=your_new_token
   - DISCORD_USER_ID=your_user_id
7. OR use .env file in repo (already configured)
8. Network: Trusted (needs internet access)
9. Create and test with "Run now"

---

## Copy This Into Routine Prompt

```
Execute the SCOUT AI news monitor autonomously. Run: python src/monitor.py

The script will:
1. Fetch news from 8+ sources in parallel (HackerNews, ArXiv, Reddit, Bluesky, Product Hunt, Dev.to, GitHub, NewsAPI)
2. Filter articles by relevance (0.25 threshold minimum)
3. Remove spam/clickbait/low-quality content
4. Categorize: models, breaking news, research, technical, other
5. Send high-priority breaking news immediately via Discord DM
6. Send full batch digest with rich embeds every 6 hours
7. Track analytics, trending keywords, and discovery rates
8. Auto-deduplicate using semantic similarity + git state
9. Send error alerts to Discord if anything fails

Do NOT ask for confirmation. Execute the script, capture all output, and let it complete. Environment variables are loaded from .env file automatically.
```

---

## Cost Analysis

Every 6 hours = 4 executions per day = 120 per month

Routine overhead per execution: ~2-5k tokens
Total: 240k-600k tokens per month

With Gemini for summaries: free (1,500 req/day)

This is roughly 50% of the 3-hour schedule cost but gets more comprehensive research.

---

## Features

Sources: 8+ news APIs
Coverage: Models, Anthropic news, OpenAI, image generation, outages, technical articles
Deduplication: Semantic + state-based
Caching: Smart ETags to reduce API calls
Filtering: Relevance scoring 0-1.0
Summaries: Optional (Google Gemini free tier)

---
