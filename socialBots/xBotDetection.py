import requests
import json
from datetime import datetime

# X API v2 config
BEARER_TOKEN = "YOUR_BEARER_TOKEN"
SEARCH_ENDPOINT = "https://api.twitter.com/2/tweets/search"

# Keywords - using sets for O(1) lookup
KEYWORDS = [
    "$SOL", "$AVAX", "$ETH", "$DOGE", "$LDO", "pump", "moon", "diamond hands", "bagholder"
]
KEYWORDS_LOWER = {k.lower() for k in KEYWORDS}
NEGATIVE_WORDS = {"crash", "dump", "rug", "scam"}
BOT_INDICATORS = {"follow back", "dm for promo", "check my link", "airdrop", "giveaway"}
SUSPICIOUS_PATTERNS = {"buy now", "guaranteed", "100x", "easy money", "risk free"}

def search_tweets(query, max_results=10):
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }

    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name,verified"
    }

    response = requests.get(SEARCH_ENDPOINT, headers=headers, params=params)
    data = response.json()

    tweets = []
    for tweet in data.get("data", []):
        metrics = tweet.get("public_metrics", {})
        author = next((u for u in data.get("includes", {}).get("users", []) if u["id"] == tweet["author_id"]), None)
        username = author.get("username") if author else "unknown"

        tweet_data = {
            "id": tweet["id"],
            "text": tweet["text"],
            "created_at": tweet["created_at"],
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("quote_count", 0),
            "replies": metrics.get("reply_count", 0),
            "author": username,
            "sentiment": classify_sentiment(tweet["text"])
        }
        tweet_data["is_bot"] = is_likely_bot(tweet_data)
        tweets.append(tweet_data)

    return tweets

def classify_sentiment(text):
    text_lower = text.lower()
    # Use set comprehension for efficient lookup
    positive = sum(1 for k in KEYWORDS_LOWER if k in text_lower)
    negative = sum(1 for word in NEGATIVE_WORDS if word in text_lower)
    if positive > negative:
        return "positive"
    elif negative > positive:
        return "negative"
    else:
        return "neutral"

def detect_bot_indicators(text):
    """Check if text contains bot-like patterns using set-based lookup"""
    text_lower = text.lower()
    # Use any() with generator expression for early exit on first match
    has_bot_indicators = any(pattern in text_lower for pattern in BOT_INDICATORS)
    has_suspicious = any(pattern in text_lower for pattern in SUSPICIOUS_PATTERNS)
    return has_bot_indicators or has_suspicious

def is_likely_bot(tweet_data):
    """
    Determine if a tweet is likely from a bot using efficient set-based checks
    """
    text = tweet_data.get("text", "").lower()
    author = tweet_data.get("author", "")

    # Check multiple bot indicators efficiently using list comprehension
    checks = [
        detect_bot_indicators(text),
        tweet_data.get("likes", 0) == 0 and tweet_data.get("retweets", 0) > 10,  # Suspicious engagement
        len([k for k in KEYWORDS_LOWER if k in text]) > 3,  # Keyword stuffing
        author.lower().startswith(("bot", "promo", "nft", "crypto")) if author else False
    ]

    # Return True if 2 or more indicators are present
    return sum(checks) >= 2

# Main
def main():
    for kw in KEYWORDS:
        print(f"\n🔍 Searching for: {kw}")
        tweets = search_tweets(kw, max_results=5)

        # Filter bots using list comprehension
        likely_bots = [t for t in tweets if t.get('is_bot', False)]
        likely_humans = [t for t in tweets if not t.get('is_bot', False)]

        print(f"📊 Found {len(likely_bots)} likely bots, {len(likely_humans)} likely humans")

        for t in tweets:
            bot_tag = "🤖 BOT" if t.get('is_bot', False) else "👤"
            print(f"{bot_tag} @{t['author']} ({t['sentiment']}): {t['text'][:50]}...")

if __name__ == "__main__":
    main()