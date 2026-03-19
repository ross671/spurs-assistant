# Spurs Assistant 🤍

A simple Python script that fetches Tottenham Hotspur fixture and score data,
then sends you a plain-English summary on Telegram.

---

## What each file does

| File | Purpose |
|------|---------|
| `spurs_assistant.py` | The main script — all the logic lives here |
| `.env` | Stores your secret API keys (never share this file) |
| `requirements.txt` | Lists the Python packages the project needs |
| `README.md` | This file — setup instructions |

---

## Requirements

- Python 3.8 or newer
- A free account at [football-data.org](https://www.football-data.org/client/register)
- A Telegram bot (takes 2 minutes to create — see below)

---

## Setup — step by step

### 1. Install Python packages

Open your terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

### 2. Get your football-data.org API key

1. Go to [football-data.org/client/register](https://www.football-data.org/client/register)
2. Sign up for the free tier (no credit card needed)
3. After registering, your API key will be emailed to you
4. Copy it — you'll need it in the next step

### 3. Create a Telegram bot

1. Open Telegram and search for **@BotFather**
2. Send it the message `/newbot`
3. Follow the prompts — give your bot a name and a username
4. BotFather will give you a **bot token** that looks like `123456:ABC-DEF...`
5. Copy it

### 4. Find your Telegram Chat ID

> Your Chat ID tells the bot where to send messages.
> It is a number like `123456789`, not a username.

**Easiest method:**
1. Start a chat with your bot by searching for its username in Telegram and pressing Start
2. Open this URL in your browser (replace `YOUR_BOT_TOKEN` with your actual token):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. Send any message to your bot in Telegram, then refresh the URL
4. Look for `"chat":{"id":` in the JSON — that number is your Chat ID

### 5. Fill in the .env file

Open `.env` and replace the placeholder values:

```
FOOTBALL_DATA_API_KEY=paste_your_football_data_key_here
TELEGRAM_BOT_TOKEN=paste_your_bot_token_here
TELEGRAM_CHAT_ID=paste_your_numeric_chat_id_here
```

> **Important:** Use your numeric Chat ID (e.g. `123456789`), not a username.

### 6. Run the script

```bash
python spurs_assistant.py
```

You should see the summary printed in your terminal **and** receive it on Telegram.

---

## Example output

```
⚽ Spurs Assistant Update
─────────────────────────
Last result (Premier League):
  Tottenham Hotspur 3 - 1 Chelsea FC
  Played: Sun 14 Apr 2025, 16:30 UTC
  Spurs won this game.

Next fixture (Premier League):
  Arsenal FC vs Tottenham Hotspur
  Kick-off: Sun 21 Apr 2025, 14:00 UTC
─────────────────────────
Come on you Spurs! 🤍
```

---

## Troubleshooting

**"Could not fetch last result"**
- Check that your `FOOTBALL_DATA_API_KEY` is correct in the .env file
- The free tier of football-data.org has rate limits — wait a minute and try again

**Telegram message not arriving**
- Make sure you started a chat with your bot in Telegram first (press Start)
- Double-check that `TELEGRAM_CHAT_ID` is your numeric ID, not a username
- Verify your `TELEGRAM_BOT_TOKEN` is correct

**ModuleNotFoundError**
- Run `pip install -r requirements.txt` again

---

## Deploying to GitHub Actions (always-on, no Mac required)

This is the recommended way to run the assistant long-term.
GitHub's servers run the cron jobs whether your Mac is on or off — completely free.

### How it works
- Your API keys are stored as **GitHub Secrets** (encrypted, never visible in the code)
- After each run, the bot commits `seen_news.json` and `seen_lineups.json` back to the repo so duplicates are avoided across runs
- Three scheduled workflows handle the different cadences automatically

### One-time setup

**Step 1 — Install GitHub Desktop**
Download it from [desktop.github.com](https://desktop.github.com) and sign in with a GitHub account (free).

**Step 2 — Create a new repo**
1. Open GitHub Desktop → File → New Repository
2. Name it `spurs-assistant`
3. Set the Local Path to your Desktop
4. Click **Create Repository**
5. Click **Publish Repository** → keep it **Public** (public repos get unlimited free Actions minutes)

**Step 3 — Add your secrets to GitHub**
1. Go to your repo on github.com
2. Click **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
3. Add these three secrets one by one (exact names matter):

| Name | Value |
|------|-------|
| `FOOTBALL_DATA_API_KEY` | your football-data.org key |
| `TELEGRAM_BOT_TOKEN` | your bot token |
| `TELEGRAM_CHAT_ID` | your numeric chat ID |

**Step 4 — Push the code**
Back in GitHub Desktop, you should see all the project files listed as changes.
Write a commit message like `Initial commit` and click **Commit to main**, then **Push origin**.

**Step 5 — Enable Actions**
1. Go to your repo on github.com → click the **Actions** tab
2. If prompted, click **I understand my workflows, go ahead and enable them**
3. To test immediately: click a workflow → **Run workflow** → **Run workflow**

The workflows will now run on GitHub's servers automatically. ✅

---

## Running it automatically every day (local Mac only)

Once everything works, you can schedule it to run daily.

**On Mac/Linux — using cron:**
1. Open your terminal and type `crontab -e`
2. Add this line (adjust the path to match where your project lives):
   ```
   0 8 * * * /usr/bin/python3 /Users/yourname/Desktop/spurs-assistant/spurs_assistant.py
   ```
   This runs the script every day at 8:00 AM.

**On Windows — using Task Scheduler:**
1. Open Task Scheduler
2. Create a Basic Task, set it to Daily
3. Action: Start a Program → `python.exe`
4. Add argument: the full path to `spurs_assistant.py`

---

## What's coming next

- Transfer news
- Player injury updates
- League table position
