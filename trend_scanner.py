import os
import json
import time
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

HEADERS = {"User-Agent": "Mozilla/5.0 (trend-scanner-bot/1.0)"}


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Telegram messages max ~4096 chars, split if needed
    chunks = [text[i:i + 3800] for i in range(0, len(text), 3800)] or [text]
    for chunk in chunks:
        resp = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        })
        if not resp.ok:
            print("Telegram send failed:", resp.text)
        time.sleep(1)


def get_google_trends_iraq():
    """Pull trending searches for Iraq via pytrends."""
    results = []
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=180)
        # Iraq realtime/daily trending searches
        df = pytrends.trending_searches(pn='iraq')
        for term in df[0].tolist()[:15]:
            results.append({"term": term, "source": "Google Trends (Iraq)", "score": 3})
    except Exception as e:
        print("Google Trends Iraq failed:", e)
    return results


def get_google_trends_related(seed_terms):
    """For a handful of seed business categories, check interest_over_time trend direction."""
    results = []
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=180)
        for term in seed_terms:
            try:
                pytrends.build_payload([term], timeframe='today 3-m', geo='IQ')
                df = pytrends.interest_over_time()
                if df is not None and not df.empty and len(df) > 4:
                    recent = df[term].tail(4).mean()
                    older = df[term].head(4).mean()
                    if older > 0 and recent > older * 1.2:
                        growth = round((recent - older) / older * 100)
                        results.append({
                            "term": term,
                            "source": "Google Trends (growth)",
                            "score": min(5, 2 + growth // 25),
                            "note": f"+{growth}% search growth (Iraq, 3mo)"
                        })
                time.sleep(1)
            except Exception as e:
                print(f"Trend check failed for {term}:", e)
    except Exception as e:
        print("Google Trends related failed:", e)
    return results


def get_reddit_trending(subreddits):
    """Pull hot posts from relevant subreddits as demand/interest signals."""
    results = []
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.ok:
                data = resp.json()
                for post in data["data"]["children"][:8]:
                    p = post["data"]
                    if p.get("score", 0) > 20:
                        results.append({
                            "term": p["title"][:100],
                            "source": f"Reddit r/{sub}",
                            "score": min(5, 1 + p["score"] // 200),
                            "url": f"https://reddit.com{p['permalink']}"
                        })
        except Exception as e:
            print(f"Reddit fetch failed for r/{sub}:", e)
        time.sleep(1)
    return results


def dedupe_and_rank(items, top_n=8):
    seen = set()
    unique = []
    for item in sorted(items, key=lambda x: -x.get("score", 0)):
        key = item["term"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:top_n]


def format_digest(items):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"<b>📊 Daily Trends Digest — {today}</b>", ""]
    if not items:
        lines.append("No strong signals found today. Will try again tomorrow.")
        return "\n".join(lines)

    for i, item in enumerate(items, 1):
        lines.append(f"<b>{i}. {item['term']}</b>")
        lines.append(f"   Source: {item['source']}")
        if item.get("note"):
            lines.append(f"   {item['note']}")
        if item.get("url"):
            lines.append(f"   {item['url']}")
        lines.append("")

    lines.append("Reply with the number you like and I'll start building it as a SaaS.")
    return "\n".join(lines)


def main():
    all_items = []

    print("Fetching Google Trends Iraq trending searches...")
    all_items += get_google_trends_iraq()

    seed_business_terms = [
        "delivery app", "online booking", "inventory software",
        "invoice app", "restaurant management", "online store"
    ]
    print("Checking growth trends for seed business terms...")
    all_items += get_google_trends_related(seed_business_terms)

    print("Fetching Reddit signals...")
    all_items += get_reddit_trending(["Iraq", "smallbusiness", "Entrepreneur", "SaaS"])

    ranked = dedupe_and_rank(all_items, top_n=8)
    digest = format_digest(ranked)

    print(digest)
    send_telegram_message(digest)

    # Save history for later review
    os.makedirs("history", exist_ok=True)
    fname = f"history/{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(ranked, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
