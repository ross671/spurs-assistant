"""
lineups.py
----------
Checks if Spurs have a match today and, if so, whether the lineup has been
announced. Sends one Telegram alert per match — never the same match twice.

What it does:
  1. Asks football-data.org if Spurs play today
  2. If yes, fetches the full match detail (which includes lineup data)
  3. If the lineup is available (not empty), formats it into a short message
  4. Saves the match ID to seen_lineups.json so the alert is only sent once

This file is imported by spurs_assistant.py — you don't run it directly.
"""

import json       # For reading and writing seen_lineups.json
import os         # For building file paths
import requests   # For calling the football-data.org API
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
SPURS_TEAM_ID    = 73

# Shared headers used in every API request
HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY}

# Path to the file that remembers which match lineup alerts have been sent
SEEN_LINEUPS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "seen_lineups.json"
)


# ---------------------------------------------------------------------------
# LOAD / SAVE SEEN LINEUPS
# Tracks match IDs we've already sent lineup alerts for, so we never
# send the same lineup twice (even if the script is run multiple times).
# ---------------------------------------------------------------------------

def load_seen_lineups():
    """
    Reads seen_lineups.json and returns a set of match IDs already alerted.
    Returns an empty set if the file doesn't exist yet.
    """
    if not os.path.exists(SEEN_LINEUPS_FILE):
        return set()
    try:
        with open(SEEN_LINEUPS_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen_lineups(seen_ids):
    """
    Saves the set of alerted match IDs to seen_lineups.json.
    Converts the set to a list first (JSON can't store sets directly).
    """
    try:
        with open(SEEN_LINEUPS_FILE, "w") as f:
            json.dump(list(seen_ids), f, indent=2)
    except Exception as e:
        print(f"Warning: could not save seen_lineups.json: {e}")


# ---------------------------------------------------------------------------
# STEP 1 — CHECK FOR A MATCH TODAY
# ---------------------------------------------------------------------------

def get_todays_match():
    """
    Asks football-data.org if Spurs have any match scheduled today (UTC).
    Returns the first match found as a dict, or None if no match today.
    """
    # Get today's date in the format the API expects: YYYY-MM-DD
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url    = f"https://api.football-data.org/v4/teams/{SPURS_TEAM_ID}/matches"
    params = {"dateFrom": today, "dateTo": today}

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        matches = response.json().get("matches", [])
        return matches[0] if matches else None
    except requests.exceptions.RequestException as e:
        print(f"Could not check for today's match: {e}")
        return None


# ---------------------------------------------------------------------------
# STEP 2 — FETCH FULL MATCH DETAIL (INCLUDES LINEUP)
# ---------------------------------------------------------------------------

def get_match_detail(match_id):
    """
    Fetches full details for a single match by its ID.
    This response includes lineup arrays when the data is available.
    Returns the match dict, or None if the request failed.
    """
    url = f"https://api.football-data.org/v4/matches/{match_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch match detail: {e}")
        return None


# ---------------------------------------------------------------------------
# STEP 3 — FORMAT THE LINEUP INTO A TELEGRAM MESSAGE
# ---------------------------------------------------------------------------

def format_lineup_message(match):
    """
    Builds a short, mobile-friendly lineup message from the match data.
    Returns None if lineup data isn't available yet (list is empty).

    The message shows:
      - Opponent, venue (H/A), competition, kick-off time
      - Formation
      - Starting XI grouped by position (GK / DEF / MID / FWD)
      - Bench (first 7 names to keep it short)
    """
    home_team = match.get("homeTeam", {})
    away_team = match.get("awayTeam", {})

    # Work out which side is Spurs
    spurs_is_home = "Tottenham" in home_team.get("name", "")
    spurs    = home_team if spurs_is_home else away_team
    opponent = away_team if spurs_is_home else home_team

    lineup    = spurs.get("lineup", [])   # Starting XI — empty list if not out yet
    bench     = spurs.get("bench", [])
    formation = spurs.get("formation") or ""

    # If lineup is empty, the data isn't available yet — do nothing
    if not lineup:
        return None

    # --- Header ---
    competition  = match.get("competition", {}).get("name", "")
    opponent_name = opponent.get("shortName") or opponent.get("name", "?")
    venue        = "H" if spurs_is_home else "A"

    try:
        dt      = datetime.strptime(match["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
        kickoff = dt.strftime("%H:%M UTC")
    except Exception:
        kickoff = ""

    lines = [
        "📋 Spurs Starting Lineup",
        f"vs {opponent_name} ({venue}) · {competition}",
        f"KO: {kickoff}",
        "─────────────────",
    ]

    if formation:
        lines.append(f"Formation: {formation}")
        lines.append("")

    # --- Group players by position ---
    # We want them in this order: GK first, then defenders, midfielders, forwards
    position_labels = {
        "Goalkeeper": "GK",
        "Defender":   "DEF",
        "Midfielder": "MID",
        "Forward":    "FWD",
        "Attacker":   "FWD",
    }
    position_order = ["Goalkeeper", "Defender", "Midfielder", "Forward", "Attacker"]

    grouped = {}
    for player in lineup:
        pos = player.get("position", "Unknown")
        grouped.setdefault(pos, []).append(player.get("name", "?"))

    for pos in position_order:
        if pos in grouped:
            label = position_labels.get(pos, pos[:3].upper())
            # Each position on its own line, names separated by commas
            lines.append(f"{label}  {', '.join(grouped[pos])}")

    # --- Bench (capped at 7 to keep the message short on mobile) ---
    if bench:
        bench_names = [p.get("name", "?") for p in bench[:7]]
        lines.append("")
        lines.append(f"Bench: {', '.join(bench_names)}")

    lines.append("─────────────────")
    lines.append("Come on you Spurs! 🤍")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN FUNCTION — called by spurs_assistant.py
# ---------------------------------------------------------------------------

def check_and_get_lineup_alert():
    """
    Runs through the full lineup check flow and returns a message string
    ready to send to Telegram, or None if there's nothing to send.

    Returns None when:
      - There is no Spurs match today
      - Lineups haven't been published yet
      - We already sent the alert for this match
    """
    # 1. Is there a match today?
    match = get_todays_match()
    if not match:
        print("No Spurs match today — skipping lineup check.")
        return None

    match_id   = match["id"]
    home_name  = match["homeTeam"]["name"]
    away_name  = match["awayTeam"]["name"]
    print(f"Match today: {home_name} vs {away_name}")

    # 2. Have we already sent the lineup for this match?
    seen_ids = load_seen_lineups()
    if match_id in seen_ids:
        print("Lineup alert already sent for today's match.")
        return None

    # 3. Fetch the full match detail to get lineup data
    full_match = get_match_detail(match_id)
    if not full_match:
        return None

    # 4. Try to build the message (returns None if lineup not out yet)
    message = format_lineup_message(full_match)

    if message:
        # Mark as sent so it won't be sent again even if script runs again today
        seen_ids.add(match_id)
        save_seen_lineups(seen_ids)
        print("Lineup is available — alert ready to send.")
    else:
        print("Lineup not published yet — nothing to send.")

    return message
