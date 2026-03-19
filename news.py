"""
news.py
-------
Handles everything to do with fetching and processing Spurs news headlines.

What it does:
  1. Reads RSS feeds from trusted football news sources (no API key needed)
  2. Classifies each headline as either "confirmed" news or a "rumour"
  3. Compares against a local record (seen_news.json) to skip stories already sent
  4. Returns only new stories, formatted as short bullet points

This file is imported by spurs_assistant.py — you don't run it directly.

What is RSS?
  RSS is a standard format that news websites use to share their latest articles.
  It's like a live list of headlines in a machine-readable format.
  We read it with a library called feedparser, which does the hard work for us.
"""

import json       # For reading and writing the seen_news.json file
import os         # For building file paths that work on any computer
import feedparser # For downloading and parsing RSS feeds


# ---------------------------------------------------------------------------
# NEWS SOURCES
# A list of trusted RSS feeds we read headlines from.
# To add a new source, just add another dictionary to this list.
# ---------------------------------------------------------------------------

NEWS_SOURCES = [
    {
        "name": "BBC Sport",
        "url":  "https://feeds.bbci.co.uk/sport/football/teams/tottenham-hotspur/rss.xml",
    },
    {
        "name": "The Guardian",
        "url":  "https://www.theguardian.com/football/tottenham-hotspur/rss",
    },
    {
        "name": "Sky Sports",
        "url":  "https://www.skysports.com/rss/12040",
    },
    {
        "name": "Football London",
        "url":  "https://www.football.london/tottenham-hotspur-fc/?service=rss",
    },
    {
        "name": "Spurs Official",
        "url":  "https://www.tottenhamhotspur.com/rss/",
    },
]


# ---------------------------------------------------------------------------
# KEYWORD LISTS FOR CLASSIFICATION
# We scan each headline for these words to decide if a story is confirmed
# or just a rumour. Confirmed keywords take priority.
# ---------------------------------------------------------------------------

# These words usually appear in headlines about things that have actually happened
CONFIRMED_KEYWORDS = [
    "signs", "signed", "joins", "joined", "confirms", "confirmed",
    "announces", "announced", "completes", "completed", "done deal",
    "official", "appointed", "sacked", "dismisses", "extends",
    "injured", "injury", "returns", "recalled", "sold", "sold for",
    "agrees", "agreed", "deal done",
]

# These words usually appear in headlines about speculation or transfer gossip
RUMOUR_KEYWORDS = [
    "linked", "target", "interest", "wants", "eyes", "bids",
    "could", "loan move", "set to", "reportedly", "rumour", "rumored",
    "considering", "approaches", "in talks", "on shortlist",
    "monitoring", "pursuit", "would", "might", "may sign",
]


# ---------------------------------------------------------------------------
# SEEN NEWS FILE
# This is the path to the local JSON file that tracks which articles
# we've already sent. os.path.dirname(__file__) means "same folder as this file".
# ---------------------------------------------------------------------------

SEEN_NEWS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_news.json")


# ---------------------------------------------------------------------------
# LOAD / SAVE SEEN NEWS
# These two functions read and write the seen_news.json file.
# ---------------------------------------------------------------------------

def load_seen_news():
    """
    Reads seen_news.json and returns a set of article URLs we've already sent.
    Returns an empty set if the file doesn't exist yet (first run).

    We use a set (not a list) because checking "is this URL in the set?"
    is very fast with a set.
    """
    if not os.path.exists(SEEN_NEWS_FILE):
        return set()  # File doesn't exist yet — no seen articles

    try:
        with open(SEEN_NEWS_FILE, "r") as f:
            data = json.load(f)       # Reads the JSON file into a Python list
            return set(data)          # Convert list → set for fast lookups
    except Exception as e:
        print(f"Warning: could not read seen_news.json: {e}")
        return set()


def save_seen_news(seen_urls):
    """
    Saves the set of seen article URLs to seen_news.json so we remember
    them next time. Converts the set to a list first (JSON can't store sets).
    """
    try:
        with open(SEEN_NEWS_FILE, "w") as f:
            json.dump(list(seen_urls), f, indent=2)
    except Exception as e:
        print(f"Warning: could not save seen_news.json: {e}")


# ---------------------------------------------------------------------------
# CLASSIFY AN ARTICLE
# Looks at the headline and decides: confirmed fact, or rumour?
# ---------------------------------------------------------------------------

def classify_article(title):
    """
    Scans the headline for keyword clues and returns either:
      "CONFIRMED" — something has actually happened
      "RUMOUR"    — speculation, transfer gossip, or unverified reports

    Confirmed keywords take priority. If no keywords match, we default
    to "RUMOUR" to avoid presenting speculation as fact.
    """
    title_lower = title.lower()

    # Check for confirmed keywords first — they override rumour keywords
    for word in CONFIRMED_KEYWORDS:
        if word in title_lower:
            return "CONFIRMED"

    # Default to rumour if nothing confirmed was found
    return "RUMOUR"


# ---------------------------------------------------------------------------
# FETCH ARTICLES FROM ALL SOURCES
# Downloads each RSS feed and collects articles into a list.
# ---------------------------------------------------------------------------

def fetch_articles():
    """
    Loops through NEWS_SOURCES, downloads each RSS feed, and returns
    a flat list of article dictionaries. Each article has:
      - title:    the headline text
      - url:      the link to the full article
      - source:   which outlet published it (e.g. "BBC Sport")
      - category: "CONFIRMED" or "RUMOUR"
    """
    articles = []

    for source in NEWS_SOURCES:
        try:
            # feedparser.parse() downloads the RSS feed and parses it for us
            feed = feedparser.parse(source["url"])

            # feed.entries is a list of articles — we only look at the 10 most recent
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                url   = entry.get("link", "").strip()

                # Skip entries that are missing a title or URL
                if not title or not url:
                    continue

                articles.append({
                    "title":    title,
                    "url":      url,
                    "source":   source["name"],
                    "category": classify_article(title),
                })

        except Exception as e:
            # If one source fails, print a warning but carry on with the others
            print(f"Warning: could not fetch news from {source['name']}: {e}")

    return articles


# ---------------------------------------------------------------------------
# GET ONLY NEW ARTICLES
# This is the main function called by spurs_assistant.py.
# It returns only articles we haven't sent before.
# ---------------------------------------------------------------------------

def get_new_articles():
    """
    Fetches all articles, removes any we've already seen, saves the new
    ones to our record, and returns the new articles as a list.

    Returns an empty list if there is nothing new.
    """
    seen_urls    = load_seen_news()
    all_articles = fetch_articles()

    # Keep only articles whose URL is NOT in our seen record
    new_articles = [a for a in all_articles if a["url"] not in seen_urls]

    if new_articles:
        # Mark all new articles as seen so we don't send them again next time
        for article in new_articles:
            seen_urls.add(article["url"])
        save_seen_news(seen_urls)

    return new_articles


# ---------------------------------------------------------------------------
# FORMAT NEWS INTO A TELEGRAM MESSAGE
# Splits new articles into confirmed and rumours, then builds a message.
# ---------------------------------------------------------------------------

def format_news_message(articles):
    """
    Takes a list of article dicts and formats them into a readable string
    for Telegram. Confirmed news is shown first, then rumours.

    Returns None if the list is empty (nothing new to send).
    """
    if not articles:
        return None  # Signal to the caller that there's nothing to send

    # Split into two separate lists
    confirmed = [a for a in articles if a["category"] == "CONFIRMED"]
    rumours   = [a for a in articles if a["category"] == "RUMOUR"]

    lines = ["📰 Spurs News Update", "─────────────────────────"]

    if confirmed:
        lines.append("✅ Confirmed:")
        for article in confirmed[:5]:  # Cap at 5 bullets to avoid very long messages
            lines.append(f"  • {article['title']}  [{article['source']}]")

    if confirmed and rumours:
        lines.append("")  # Blank line between sections

    if rumours:
        lines.append("🔄 Rumours & Reports:")
        for article in rumours[:5]:
            lines.append(f"  • {article['title']}  [{article['source']}]")

    lines.append("─────────────────────────")

    # "\n".join(...) glues all lines together with a newline between each one
    return "\n".join(lines)
