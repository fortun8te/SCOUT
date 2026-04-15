# SCOUT - Complete Cloud Deployment Guide

**TL;DR:** One-time 5-minute setup. Bot runs autonomously in the cloud forever. Zero maintenance.

---

## 🎯 **WHAT IT DOES (Complete Flow)**

### **Every 6 Hours, Automatically:**

```
1. FETCH (Parallel, ~5 seconds)
   ├─ HackerNews API          (top tech discussions)
   ├─ ArXiv HTTP API          (latest AI research papers)
   ├─ Reddit API              (community reactions)
   ├─ NewsAPI.org             (global news aggregation)
   └─ Bluesky Jetstream       (real-time AI posts)
   [All 5 run in parallel simultaneously]

2. DEDUPLICATE (Semantic, ~2 seconds)
   ├─ Remove near-duplicates within the batch
   │  (catches "GPT-5 Released" = "OpenAI launches GPT-5")
   └─ Remove articles seen before (git-tracked state)

3. FILTER & RANK (~3 seconds)
   ├─ Score each article: 0.0 - 1.0 relevance
   │  • Keywords: GPT, Claude, LLM, model, research
   │  • Source credibility: OpenAI/Anthropic > TechCrunch > general
   │  • Engagement: likes, upvotes, retweets
   │  • Recency: newer articles ranked higher
   └─ Keep only: score > 0.5 (high quality)

4. SUMMARIZE (Optional, ~6 seconds)
   ├─ Top 10 articles get AI summaries (if enabled)
   │  • Google Gemini API (free: 1,500 req/day)
   │  • OR Groq (free: 30 req/min)
   └─ Falls back to title if summarization fails

5. SEND (Telegram, ~2 seconds)
   ├─ Format articles into clean digest
   ├─ Categorize: Models | Breaking | Research | Technical | Other
   ├─ Send to your Telegram chat
   └─ Weekly analytics summary (every 2 weeks)

6. SAVE STATE (Git, ~1 second)
   ├─ Update processed_news.json with what was sent
   └─ Commit to GitHub (prevents duplicates next run)

TOTAL TIME: ~20-30 seconds (well under 6-hour window)
COST: $0/month (beyond Claude Pro)
```

---

## ⚙️ **HOW TO SET UP (5 minutes)**

### **Step 1: Create Telegram Bot** (2 minutes)

```
1. Open Telegram
2. Search for @BotFather
3. Send: /newbot
4. Enter bot name: "SCOUT News Bot"
5. Enter bot username: "scout_news_bot_<random>"
6. Copy the token: looks like "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
7. Send /start to your new bot
8. Note your chat ID (appears in logs or use @userinfobot)
```

### **Step 2: Set Up Claude Code Routine** (3 minutes)

1. **Go to:** [claude.ai/code/routines](https://claude.ai/code/routines)
2. **Click:** "New routine"
3. **Fill in:**
   - **Name:** `SCOUT News Monitor`
   - **Model:** Claude 3.5 Sonnet
   - **Schedule:** `0 */6 * * *` (every 6 hours)
   - **Repository:** Select `SCOUT` (or your repo name)

4. **Add Environment Variables:**
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234...
   TELEGRAM_CHAT_ID=987654321
   ```

5. **Paste this prompt in the Routine:**

```
You are SCOUT, an autonomous news monitoring bot. Every 6 hours:

1. RUN: python src/monitor.py
   This orchestrates the entire pipeline:
   - Fetches from 5 sources in parallel
   - Deduplicates articles (semantic + state-based)
   - Ranks by relevance (keyword, source, engagement, recency)
   - Filters to high-quality articles (score > 0.5)
   - Optional: AI summaries (Google Gemini free tier)
   - Sends digest to Telegram
   - Commits state to git

2. MONITOR: Check the output
   - Look for "✓ Monitor completed successfully" 
   - If error: "💥 CRITICAL ERROR" will appear
   - Error alert automatically sent to Telegram

3. GIT COMMIT: The script auto-commits
   - Run: git add data/ && git commit -m "SCOUT update"
   - Push: git push origin claude/ai-news-bot-G4TDW

4. TELEGRAM DELIVERY:
   - Message arrives in your chat ~20-30 seconds after routine starts
   - Contains: Top 5-10 articles, categorized, with links
   - Weekly analytics summary every 2 weeks

Expected behavior:
- Success: "✓ Telegram notification sent with X articles"
- No news: "ℹ️ No new articles to send this run"
- Failure: Error alert + detailed logs

The pipeline is fully resilient:
- Parallel API fetches (if one fails, others continue)
- Exponential backoff retry (up to 3 attempts per source)
- Graceful degradation (missing sources don't block digest)
- Comprehensive error tracking (all errors logged + alerted)

You are completely autonomous. Just execute and report status.
```

6. **Click:** "Create routine"

---

## ✅ **VERIFY IT WORKS**

1. Click **"Run now"** on the routine (don't wait 6 hours)
2. Watch execution in real-time
3. You should receive **first Telegram digest in 20-30 seconds**
4. Check message contains:
   - 📰 Article titles
   - 🔗 Links to source
   - ⭐ Relevance score
   - 📰 Source name

---

## 🎛️ **CUSTOMIZE (Optional)**

### **Change Schedule**
Edit schedule in routine settings:
- `0 */3 * * *` = Every 3 hours (4x/day)
- `0 */1 * * *` = Every hour (24x/day)
- `0 8,20 * * *` = Twice daily (8am, 8pm)
- `0 0 * * MON-FRI` = Weekdays only

### **Add Summaries** (Free, Optional)
```
1. Get free API key:
   - Google Gemini: https://aistudio.google.com/app/apikey
   - OR Groq: https://console.groq.com

2. Add environment variable to routine:
   GEMINI_API_KEY=your_key
   (or GROQ_API_KEY=your_key)

3. That's it! Auto-enabled on next run
```

### **Adjust Filtering Strictness**
Edit `src/filter.py` line 120:
```python
# Current (moderate)
filter_engine = FilterEngine(threshold=0.5)

# Stricter (fewer articles, higher quality)
filter_engine = FilterEngine(threshold=0.6)

# Looser (more articles, may include noise)
filter_engine = FilterEngine(threshold=0.4)
```

Then commit and push to trigger update.

### **Add/Remove News Sources**
Edit `src/news_sources.py`:
```python
# Add custom keywords to Bluesky
bluesky = BlueskyJetstreamMonitor(
    keywords=["GPT", "Claude", "custom_topic", ...]
)

# Disable Bluesky
bluesky_articles = []  # Comment out line that fetches Bluesky
```

---

## 📊 **WHAT YOU GET**

### **Daily Digest Format**
```
📰 AI News Daily Digest | Tue, Apr 15, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4 min read

🤖 AI & MACHINE LEARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. OpenAI releases GPT-5 (3 min)
   Brief summary of breakthrough...
   🔗 OpenAI Blog | ⭐ 9.8/10

2. DeepSeek launches open-source model (5 min)
   Summary here...
   🔗 HackerNews | ⭐ 9.2/10

⚡ BREAKING NEWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. Claude 3.2 Leaked Features (4 min)
   ...
   🔗 Reddit | ⭐ 8.9/10

[More categories...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 4 stories | ~13 min reading time
Next digest in 6 hours
```

### **Weekly Analytics** (Automatic every 2 weeks)
```
📊 SCOUT Analytics Summary
═════════════════════════════
Runs: 42
Articles sent: 127
Avg per run: 3.0
Top source: HackerNews
Trending: gpt(42) claude(38) llm(35)
```

---

## 🔧 **MONITORING & DEBUGGING**

### **View Execution Logs**
1. Go to [claude.ai/code/routines](https://claude.ai/code/routines)
2. Click routine → "Past runs"
3. Click any execution to see full transcript
4. Logs show exact flow: [FETCH] → [DEDUP] → [FILTER] → [TELEGRAM] → [GIT]

### **Check for Errors**
- Look for `💥 CRITICAL ERROR` in logs
- Or check Telegram for error alert message
- All errors include stack trace for debugging

### **Manual Testing**
```bash
# Clone repo locally
git clone <your_repo>
cd SCOUT

# Set env vars
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_id

# Run manually
pip install -q -r requirements.txt
python -m src.monitor

# Check logs
tail -f monitor.log
```

---

## 🚀 **THAT'S IT!**

Your bot is now:
- ✅ **Running in the cloud** (Claude Code Routines)
- ✅ **Autonomous** (no manual intervention needed)
- ✅ **Reliable** (retry logic, error handling, graceful degradation)
- ✅ **Fast** (parallel API calls, ~30 seconds per cycle)
- ✅ **Smart** (semantic dedup, relevance scoring, summarization)
- ✅ **Free** ($0/month beyond Claude Pro)
- ✅ **Scalable** (can handle 1000+ articles/day with same code)

**Enjoy your AI news feed!** 📰🤖

---

## 📞 **TROUBLESHOOTING**

| Issue | Solution |
|-------|----------|
| No Telegram messages | Check token & chat ID. Try "Run now". |
| Too many articles | Increase threshold: 0.5 → 0.6 in filter.py |
| Too few articles | Decrease threshold: 0.5 → 0.4 in filter.py |
| Summaries not appearing | Set GEMINI_API_KEY. Check API key is valid. |
| Missing Bluesky articles | Bluesky API may be down. Check logs. |
| Git commit failing | Ensure branch is `claude/ai-news-bot-G4TDW` |
| Routine errors | Click execution > View logs > Search "ERROR" |

---

## 📝 **VERSION**

- **SCOUT Version:** 2.0 (Cloud Optimized)
- **Last Updated:** April 2026
- **Status:** Production Ready
- **Cost:** $20/month (Claude Pro subscription)
