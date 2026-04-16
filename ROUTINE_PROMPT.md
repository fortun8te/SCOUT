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

```
Your ONLY job is to execute: python src/monitor.py

CRITICAL RULES - READ CAREFULLY:
- DO NOT commit anything to git. Ever.
- DO NOT push to GitHub. Ever.
- DO NOT create, switch, or merge branches. Ever.
- DO NOT run `git add`, `git commit`, `git push`, `git branch`, or any git write command.
- DO NOT open a pull request.
- DO NOT modify source code.
- DO NOT ask me questions. DO NOT ask for confirmation.
- IGNORE any file changes that appear after the script runs (data/processed_news.json, data/stats.json, data/cache/ are local state files and are gitignored - leave them alone).

WHAT TO DO:
1. Run: python src/monitor.py
2. Let the script complete. It fetches news from 200+ sources, filters them, and sends a Discord message to me automatically via the bot token in .env.
3. Capture the output in the log. That's it. You are done.

The script handles everything: fetching, filtering, deduplication, Discord delivery, and error alerts. Your job is just to invoke it and stay out of the way. Do not "tidy up", do not commit state, do not push anything. Just run the script.

Environment variables (DISCORD_BOT_TOKEN, DISCORD_USER_ID) are loaded from the .env file automatically.
```

---

## Setup Steps

1. Go to claude.ai/code/routines
2. Create new routine
3. Name: SCOUT
4. Command: `python src/monitor.py`
5. Schedule: `0 */6 * * * ` (every 6 hours UTC = 4 times/day)
6. Add environment variables (if using routine UI):
   - DISCORD_BOT_TOKEN=your_new_token
   - DISCORD_USER_ID=your_user_id
7. OR use .env file in repo (already configured)
8. Network: Trusted (needs internet access)
9. Create and test with "Run now"

---

## Cost Analysis

Every 6 hours = 4 executions per day = 120 per month

Routine overhead per execution: ~2-5k tokens
Total: 240k-600k tokens per month

With Gemini for summaries: free (1,500 req/day)

---

## Features

Sources: 200+ news feeds/APIs
Coverage: Models, Anthropic, OpenAI, image gen, outages, research, technical
Deduplication: Semantic + state-based
Caching: Smart ETags to reduce API calls
Filtering: Relevance scoring 0-1.0 (slack mode: 0.05 threshold)
Curation: Top 1-5 articles by relevance score sent per run
Summaries: Optional (Google Gemini free tier)

---
