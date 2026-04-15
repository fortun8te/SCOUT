# SCOUT - AI News Monitoring Bot

A cloud-based news monitoring bot that aggregates AI/ML news and sends daily digests to Telegram. Runs autonomously on Claude Code Routines (no server required).

## Features

- 📰 **Multi-source aggregation**: HackerNews, ArXiv, Reddit, NewsAPI
- 🤖 **Intelligent filtering**: Relevance-scored articles with categorization
- ⚡ **Real-time monitoring**: Sources checked every 6 hours
- 💬 **Telegram integration**: Clean, formatted daily digests
- ☁️ **Serverless**: Runs on Claude Code Routines (always on, no maintenance)
- 🔄 **Smart deduplication**: Tracks processed articles in git

## Phase 2 Features (Enhanced)

### Core Features
- 📰 **Multi-source aggregation**: HN, ArXiv, Reddit, NewsAPI, **Bluesky** (real-time!)
- 🤖 **Intelligent filtering**: 100+ keyword patterns, relevance scoring
- ⚡ **Real-time monitoring**: Sub-second Bluesky + 6-hour batch cycle
- 💬 **Telegram integration**: Clean, formatted daily digests
- ☁️ **Serverless**: Runs on Claude Code Routines
- 🔄 **Smart deduplication**: Git-based state tracking
- ✨ **Optional AI summaries**: Google Gemini free tier (1,500 req/day)
- 📊 **Analytics & trending**: Track top sources and trending keywords

## Supported News Categories

- **Model Releases**: New AI models, announcements
- **Breaking News**: Leaks, rumors, major announcements (Bluesky real-time)
- **Research**: Academic papers, technical breakthroughs
- **Technical Methods**: Fine-tuning, RAG, prompt engineering, etc.
- **Other**: General AI news and discussions

## News Sources

### Tier 1: Real-Time, Free, No Auth Required
- **Bluesky Jetstream** (WebSocket, sub-second) ⭐ NEW - Real-time AI posts
- **HackerNews** (Algolia API) - Top tech discussions
- **ArXiv** - Latest AI/ML research papers
- **Reddit** - Community discussions (MachineLearning, OpenAI, LocalLLaMA)

### Tier 2: News Aggregation (Optional, FREE)
- **NewsAPI.org** - General tech news (100 req/day)
- **GitHub Trending** - Popular AI/ML repositories

## Quick Setup

### Create Telegram Bot
- Open Telegram, find @BotFather
- Create new bot: `/newbot`
- Copy the bot token

### Deploy Routine
1. Visit [claude.ai/code/routines](https://claude.ai/code/routines)
2. Create new routine with:
   - **Name**: AI News Monitor
   - **Schedule**: `0 */6 * * *`
   - **Repository**: This repo
   - **Environment vars**: 
     ```
     TELEGRAM_BOT_TOKEN=your_token
     TELEGRAM_CHAT_ID=your_chat_id
     ```
3. Use prompt from `ROUTINE_PROMPT.md`
4. Click "Run now" to test

### Local Testing
```bash
cp .env.example .env
# Edit .env with your tokens
pip install -r requirements.txt
python src/monitor.py
```

## File Structure

```
scout/
├── src/
│   ├── monitor.py          # Main orchestrator
│   ├── news_sources.py     # Multi-source fetching
│   ├── filter.py           # Scoring & ranking
│   ├── state.py            # State management
│   ├── telegram_client.py  # Telegram integration
│   └── __init__.py
├── data/
│   └── processed_news.json # Processed articles tracking
├── .claude/
│   └── settings.json       # SessionStart hooks
├── requirements.txt        # Python dependencies
├── ROUTINE_PROMPT.md       # Routine setup guide
└── README.md               # This file
```

## Customization

### Change Schedule
Edit schedule in routine: `0 */6 * * *`
- `0 */3 * * *` = Every 3 hours
- `0 */1 * * *` = Every hour
- `0 8 * * *` = Daily at 8am

### Adjust Filtering
Edit `src/filter.py`:
```python
filter_engine = FilterEngine(threshold=0.6)  # Higher = fewer articles
```

### Add News Sources
Edit `src/news_sources.py` and add new methods

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No Telegram messages | Check bot token and chat ID |
| Too many/few articles | Adjust threshold in filter.py |
| Rate limit errors | Wait for next run |
| Missing chat ID | Message your bot, check logs |

## Monitoring

View routine executions:
1. Go to [claude.ai/code/routines](https://claude.ai/code/routines)
2. Click routine name → "Past runs"
3. Click any run to see full transcript

## Version
1.0.0 - April 2026