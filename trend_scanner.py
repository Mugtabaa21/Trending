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


def get_google_trends_related(seed_terms):
    """For a list of seed business categories, check interest_over_time trend direction
    for Iraq. Always keeps the top raw-interest terms too, even without strong growth,
    so the digest isn't empty on quiet days."""
    results = []
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(
            hl='en-US', tz=180,
            retries=2, backoff_factor=0.5,
            requests_args={'headers': {'User-Agent': 'Mozilla/5.0'}}
        )
        for term in seed_terms:
            try:
                pytrends.build_payload([term], timeframe='today 3-m', geo='IQ')
                df = pytrends.interest_over_time()
                if df is not None and not df.empty and len(df) > 4:
                    recent = df[term].tail(4).mean()
                    older = df[term].head(4).mean()
                    avg_interest = df[term].mean()
                    if older > 0 and recent > older * 1.05:
                        growth = round((recent - older) / older * 100)
                        results.append({
                            "term": term,
                            "source": "Google Trends (growth)",
                            "score": min(5, 2 + growth // 15),
                            "note": f"+{growth}% search growth (Iraq, 3mo)"
                        })
                    elif avg_interest > 5:
                        # No strong growth, but there's meaningful baseline search volume
                        results.append({
                            "term": term,
                            "source": "Google Trends (interest)",
                            "score": min(3, 1 + int(avg_interest // 20)),
                            "note": f"Avg interest level: {round(avg_interest)}/100 (Iraq, 3mo)"
                        })
                time.sleep(1)
            except Exception as e:
                print(f"Trend check failed for {term}:", e)
    except Exception as e:
        print("Google Trends related failed:", e)
    return results


def get_news_signals(seed_terms):
    """Search Google News RSS for each seed term + Iraq context. No auth needed,
    not blocked by cloud IPs. Recent article count = a rough 'buzz' signal."""
    import xml.etree.ElementTree as ET
    from urllib.parse import quote

    results = []
    for term in seed_terms:
        try:
            query = quote(f'"{term}" Iraq')
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=IQ&ceid=IQ:en"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.ok:
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                count = len(items)
                if count >= 1:
                    top_title = items[0].find("title").text if items else term
                    top_link = items[0].find("link").text if items else ""
                    results.append({
                        "term": term,
                        "source": "News signal (Iraq)",
                        "score": min(5, 1 + count),
                        "note": f"{count} recent articles — latest: {top_title[:80]}",
                        "url": top_link
                    })
            else:
                print(f"News RSS fetch for '{term}' returned status {resp.status_code}")
        except Exception as e:
            print(f"News RSS fetch failed for '{term}':", e)
        time.sleep(0.5)
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

    seed_business_terms = [
        "delivery app", "online booking", "inventory software",
        "invoice app", "restaurant management", "online store",
        "pos system", "loyalty app", "appointment scheduling",
        "car rental software", "clinic management", "pharmacy software",
        "e-commerce Iraq", "digital marketing agency", "gym management app",
        "real estate app", "food ordering app", "salon booking app"
    ]
    print("Checking growth/interest trends for seed business terms...")
    all_items += get_google_trends_related(seed_business_terms)

    print("Fetching news signals...")
    all_items += get_news_signals(seed_business_terms)

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
