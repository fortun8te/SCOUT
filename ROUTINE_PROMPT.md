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

## Prompt

Run the comprehensive AI news monitor every 6 hours. Fetch from 8+ sources in parallel: HackerNews, ArXiv, Reddit, NewsAPI, Bluesky, Product Hunt, Dev.to, and GitHub trending. Filter for high-quality news on new models, Anthropic/OpenAI announcements, image generation models, outages, and technical breakthroughs. Run python src/monitor.py to execute the full pipeline. Fetches all sources in parallel, deduplicates articles, ranks by relevance, adds optional summaries, sends digest to Telegram, and commits state to git. Send error alerts to Telegram if anything fails.

---

## Setup Steps

1. Go to claude.ai/code/routines
2. New routine
3. Name: SCOUT News Monitor
4. Schedule: 0 */6 * * * (every 6 hours = 4 times/day)
5. Add env vars:
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_id
6. Create routine
7. Test with Run now

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
