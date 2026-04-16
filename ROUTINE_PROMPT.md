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

Paste this entire block into the Routine prompt. The `export` lines inject the Discord credentials (the Routine UI doesn't let us set env vars, and `.env` is gitignored so it's not in the cloud clone — so we put them directly in the prompt).

```
Your ONLY job is to run the command below.

export DISCORD_BOT_TOKEN="<YOUR_DISCORD_BOT_TOKEN>"
export DISCORD_USER_ID="<YOUR_DISCORD_USER_ID>"
bash scripts/routine_entrypoint.sh

CRITICAL RULES - READ CAREFULLY:
- DO NOT commit anything to git. Ever.
- DO NOT push to GitHub. Ever.
- DO NOT create, switch, or merge branches. Ever.
- DO NOT run `git add`, `git commit`, `git push`, `git branch`, or any git write command.
- DO NOT open a pull request.
- DO NOT modify source code.
- DO NOT ask questions. DO NOT ask for confirmation.
- IGNORE any file changes that appear after the script runs
  (data/processed_news.json, data/stats.json, data/cache/ are local
  state files and are gitignored — leave them alone).

WHAT TO DO:
1. Run the three commands above (export + bash).
2. Let the script complete. It fetches news from 200+ sources,
   filters them, and sends a Discord message via the exported token.
3. Capture the output in the log. You are done.

Do not "tidy up". Do not commit state. Do not push anything.
```

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
Summaries: Optional (Google Gemini free tier) + local fallback when quota exhausted

---
