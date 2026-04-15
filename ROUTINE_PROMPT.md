# Claude Code Routine Setup

Use this when creating the routine at claude.ai/code/routines

---

## Configuration

Name: SCOUT News Monitor
Schedule: 0 */3 * * * (every 3 hours)
Model: Claude 3.5 Sonnet
Repositories: Your SCOUT repo
Network Access: Trusted

---

## Prompt

Run the AI news monitor every 3 hours. Fetch from HackerNews, ArXiv, Reddit, NewsAPI, and Bluesky. Filter for high-quality AI news including new models, Anthropic announcements, OpenAI/OpenClaw news, image models, outages, and technical breakthroughs. Run python src/monitor.py to execute the full pipeline. It will fetch from all sources in parallel, deduplicate articles, rank by relevance, optionally add summaries, send digest to Telegram, and commit state to git. Send error alerts to Telegram if anything fails. Keep logs clear and report success or failure at the end.

---

## Setup Steps

1. Go to claude.ai/code/routines
2. New routine
3. Name: SCOUT News Monitor
4. Schedule: 0 */3 * * * (every 3 hours = 8 times/day)
5. Add env vars:
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_id
6. Create routine
7. Test with Run now

---

## Cost Estimate

Every 3 hours = 8 executions per day = 240 per month

Routine overhead per execution: ~2-5k tokens (rough)
Total: 500k-1.2M tokens per month

If using Gemini for summaries: free (1,500 req/day)
If using Claude for summaries: add ~30k tokens per execution

Bottom line: With Gemini, probably negligible cost. Monitor your usage on your dashboard to confirm.

---

## Adjust Settings

Change frequency: Edit the cron in schedule
- 0 */2 * * * = Every 2 hours (12x/day)
- 0 */6 * * * = Every 6 hours (4x/day)

Change filtering: Edit src/filter.py line 120
```python
threshold=0.5  # Current (moderate)
threshold=0.6  # Stricter (fewer articles)
threshold=0.4  # Looser (more articles)
```

---
