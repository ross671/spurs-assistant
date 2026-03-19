"""
spurs_assistant.py
------------------
This is the main file for the Spurs Assistant project.

What it does, step by step:
  1. Loads your API keys from the .env file
  2. Asks football-data.org for Tottenham's last result and next fixture
  3. Fetches the latest Spurs news headlines (via news.py)
  4. Sends fixture summary + any new headlines to you on Telegram

How to run it:
  python spurs_assistant.py
"""

# ---------------------------------------------------------------------------
# IMPORTS
# These are libraries we need. They are all installed via requirements.txt.
# ---------------------------------------------------------------------------

import os                      # Lets us read environment variables (from .env)
import sys                     # Lets us read command-line arguments (sys.argv)
import requests                # Lets us make HTTP calls to APIs
from dotenv import load_dotenv # Reads the .env file and loads the keys into os.environ
from datetime import datetime  # Helps us format dates nicely

# news.py is our own file in this project — it handles fetching headlines
from news import get_new_articles, format_news_message

# lineups.py is our own file — it checks for today's lineup
from lineups import check_and_get_lineup_alert


# ---------------------------------------------------------------------------
# STEP 1 — LOAD API KEYS
# load_dotenv() reads the .env file in the same folder and makes each key
# available via os.getenv("KEY_NAME").
# ---------------------------------------------------------------------------

load_dotenv()

FOOTBALL_API_KEY  = os.getenv("FOOTBALL_DATA_API_KEY")
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID")

# Tottenham Hotspur's ID on football-data.org (this never changes)
SPURS_TEAM_ID = 73


# ---------------------------------------------------------------------------
# HELPER: FORMAT A DATE STRING
# football-data.org returns dates like "2025-04-05T14:00:00Z".
# This function turns that into something readable like "Sat 5 Apr 2025, 14:00"
# ---------------------------------------------------------------------------

def format_date(date_string):
    """
    Takes a raw ISO date string from the API and returns a friendly string.
    If anything goes wrong, it just returns the raw string unchanged.
    """
    try:
        dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%a %d %b %Y, %H:%M UTC")
    except Exception:
        return date_string  # Fall back to the raw value if parsing fails


# ---------------------------------------------------------------------------
# STEP 2A — FETCH LAST RESULT
# We ask the API for Tottenham's most recent finished match.
# ---------------------------------------------------------------------------

def get_last_result():
    """
    Calls football-data.org and returns a short summary string of the
    last completed Spurs match, or an error message if it fails.
    """

    # The URL asks for the 1 most recent FINISHED Spurs match
    url = f"https://api.football-data.org/v4/teams/{SPURS_TEAM_ID}/matches"
    params = {
        "status": "FINISHED",  # Only completed games
        "limit": 1,            # We only want the most recent one
    }
    headers = {
        "X-Auth-Token": FOOTBALL_API_KEY  # Our API key goes in the header
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an error if the request failed (e.g. 403, 500)

        data = response.json()
        matches = data.get("matches", [])

        # If there are no matches returned, say so
        if not matches:
            return "No recent result found."

        # Pull out the details of the last match
        match      = matches[-1]  # The last item in the list is the most recent
        home_team  = match["homeTeam"]["name"]
        away_team  = match["awayTeam"]["name"]
        home_score = match["score"]["fullTime"]["home"]
        away_score = match["score"]["fullTime"]["away"]
        date       = format_date(match["utcDate"])
        competition = match["competition"]["name"]

        # Figure out if Spurs won, drew, or lost
        spurs_were_home = "Tottenham" in home_team

        if home_score == away_score:
            outcome = "drew"
        elif spurs_were_home and home_score > away_score:
            outcome = "won"
        elif not spurs_were_home and away_score > home_score:
            outcome = "won"
        else:
            outcome = "lost"

        return (
            f"Last result ({competition}):\n"
            f"  {home_team} {home_score} - {away_score} {away_team}\n"
            f"  Played: {date}\n"
            f"  Spurs {outcome} this game."
        )

    except requests.exceptions.RequestException as e:
        # This catches network errors, bad status codes, timeouts, etc.
        return f"Could not fetch last result: {e}"


# ---------------------------------------------------------------------------
# STEP 2B — FETCH NEXT FIXTURE
# We ask the API for Tottenham's next scheduled match.
# ---------------------------------------------------------------------------

def get_next_fixture():
    """
    Calls football-data.org and returns a short summary string of the
    next scheduled Spurs match, or an error message if it fails.
    """

    url = f"https://api.football-data.org/v4/teams/{SPURS_TEAM_ID}/matches"
    params = {
        "status": "SCHEDULED",  # Only upcoming games
        "limit": 1,             # Just the very next one
    }
    headers = {
        "X-Auth-Token": FOOTBALL_API_KEY
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        matches = data.get("matches", [])

        if not matches:
            return "No upcoming fixture found."

        match       = matches[0]  # The first item is the soonest upcoming game
        home_team   = match["homeTeam"]["name"]
        away_team   = match["awayTeam"]["name"]
        date        = format_date(match["utcDate"])
        competition = match["competition"]["name"]

        return (
            f"Next fixture ({competition}):\n"
            f"  {home_team} vs {away_team}\n"
            f"  Kick-off: {date}"
        )

    except requests.exceptions.RequestException as e:
        return f"Could not fetch next fixture: {e}"


# ---------------------------------------------------------------------------
# STEP 3 — BUILD THE SUMMARY MESSAGE
# We combine the last result and next fixture into one readable message.
# ---------------------------------------------------------------------------

def build_summary():
    """
    Calls both data functions and combines them into a single message string.
    """

    last_result  = get_last_result()
    next_fixture = get_next_fixture()

    # The \n characters are newlines — they create line breaks in the message
    summary = (
        "⚽ Spurs Assistant Update\n"
        "─────────────────────────\n"
        f"{last_result}\n"
        "\n"
        f"{next_fixture}\n"
        "─────────────────────────\n"
        "Come on you Spurs! 🤍"
    )

    return summary


# ---------------------------------------------------------------------------
# STEP 4 — SEND TO TELEGRAM
# We use the Telegram Bot API to send the summary to your chat.
# ---------------------------------------------------------------------------

def send_telegram_message(message):
    """
    Sends `message` to your Telegram chat using the bot token and chat ID
    from the .env file. Returns True if it worked, False if not.
    """

    # This is the Telegram API endpoint for sending a message
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        print("Message sent to Telegram successfully!")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram message: {e}")
        # Print the response body if available — often contains a helpful error from Telegram
        if hasattr(e, "response") and e.response is not None:
            print("Telegram API response:", e.response.text)
        return False


# ---------------------------------------------------------------------------
# STEP 5 — CHECK CONFIG
# Before doing anything, make sure the required .env values are set.
# ---------------------------------------------------------------------------

def check_config():
    """
    Checks that all required environment variables are present and filled in.
    Prints a clear error if anything is missing and returns False.
    """

    missing = []

    if not FOOTBALL_API_KEY or FOOTBALL_API_KEY == "your_football_data_api_key_here":
        missing.append("FOOTBALL_DATA_API_KEY (get one free at football-data.org)")

    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")

    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        print("ERROR: The following values are missing from your .env file:")
        for item in missing:
            print(f"  - {item}")
        print("\nPlease edit the .env file and fill them in, then run again.")
        return False

    return True


# ---------------------------------------------------------------------------
# INDIVIDUAL TASKS
# Each function below runs one part of the assistant.
# They are called by the main block depending on which mode was requested.
# ---------------------------------------------------------------------------

def run_fixtures():
    """Fetches and sends the fixture/result summary."""
    print("Fetching fixture data...")
    summary = build_summary()
    print("\n--- FIXTURE PREVIEW ---")
    print(summary)
    print("----------------------\n")
    send_telegram_message(summary)


def run_news():
    """Checks for new headlines and sends them if found."""
    print("Fetching latest Spurs news...")
    new_articles = get_new_articles()
    news_message = format_news_message(new_articles)
    if news_message:
        print(f"Found {len(new_articles)} new article(s). Sending...")
        send_telegram_message(news_message)
    else:
        print("No new articles since last run.")


def run_lineup():
    """Checks if today's lineup is out and sends it if so."""
    print("Checking for today's lineup...")
    lineup_message = check_and_get_lineup_alert()
    if lineup_message:
        print("\n--- LINEUP PREVIEW ---")
        print(lineup_message)
        print("---------------------\n")
        send_telegram_message(lineup_message)


# ---------------------------------------------------------------------------
# MAIN — ENTRY POINT
#
# Accepts an optional mode argument so cron can call specific parts:
#
#   python spurs_assistant.py            → full run (fixtures + news + lineup)
#   python spurs_assistant.py full       → same as above
#   python spurs_assistant.py news       → news check only
#   python spurs_assistant.py lineup     → lineup check only
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # sys.argv is the list of words typed on the command line.
    # sys.argv[0] is always the script name itself.
    # sys.argv[1] is the first extra word, if provided.
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    print(f"Starting Spurs Assistant (mode: {mode})...")

    if not check_config():
        exit(1)

    if mode == "news":
        run_news()

    elif mode == "lineup":
        run_lineup()

    elif mode in ("full", ""):
        run_fixtures()
        run_news()
        run_lineup()

    else:
        print(f"Unknown mode '{mode}'. Use: full, news, or lineup.")
        exit(1)

    print("Done.")


# ---------------------------------------------------------------------------
# FUTURE IDEAS (coming in later versions)
# ---------------------------------------------------------------------------
# To add more news sources:
#   - Add another dictionary to the NEWS_SOURCES list in news.py
#
# To improve rumour detection:
#   - Add more keywords to CONFIRMED_KEYWORDS / RUMOUR_KEYWORDS in news.py
#
# To run this automatically every day:
#   - Use a cron job (Mac/Linux) or Task Scheduler (Windows)
#   - Or use a free service like GitHub Actions or Railway
