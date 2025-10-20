import requests
import json
from datetime import datetime

# X API v2 config
BEARER_TOKEN = "YOUR_BEARER_TOKEN"
SEARCH_ENDPOINT = "https://api.twitter.com/2/tweets/search"

# Keywords
KEYWORDS = [
    "$SOL", "$AVAX", "$ETH", "$DOGE", "$LDO", "pump", "moon", "diamond hands", "bagholder"
]

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

        tweets.append({
            "id": tweet["id"],
            "text": tweet["text"],
            "created_at": tweet["created_at"],
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("quote_count", 0),
            "replies": metrics.get("reply_count", 0),
            "author": username,
            "sentiment": classify_sentiment(tweet["text"])
        })

    return tweets

def classify_sentiment(text):
    text = text.lower()
    positive = sum(1 for k in KEYWORDS if k.lower() in text)
    negative = sum(1 for word in ["crash", "dump", "rug", "scam"] if word in text)
    if positive > negative:
        return "positive"
    elif negative > positive:
        return "negative"
    else:
        return "neutral"

# Main
def main():
    for kw in KEYWORDS:
        print(f"\n🔍 Searching for: {kw}")
        tweets = search_tweets(kw, max_results=5)
        for t in tweets:
            print(f"💬 @{t['author']} ({t['sentiment']}): {t['text'][:50]}...")

if __name__ == "__main__":
    main()