"""Save the General Division for Gold and Jewelry prices reported by Egypt Independent.

Reads the site's RSS feed, opens articles about gold prices, takes the numbers
(24K, 21K, 18K per gram, gold pound, global ounce) and saves them to SQLite.

Usage:
    python update_gold_official.py                 # read the RSS feed and save
    python update_gold_official.py <article url>   # test one article, saves nothing
    python update_gold_official.py <article url> --save [--date YYYY-MM-DD]

Needs: pip install requests beautifulsoup4
Check the site's terms before using this in a public app.
"""
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

DB = "finance.db"
FEED = "https://www.egyptindependent.com/feed/"
HEADERS = {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/156.0 Safari/537.36"}


def num(text: str) -> float:
    return float(text.replace(",", ""))


def _find(patterns: list[str], text: str):
    """Return the first number found by the patterns, tried in order."""
    for pat in patterns:
        found = re.findall(pat, text, re.I)
        if found:
            return num(found[-1])
    return None


def parse_prices(text: str) -> dict | None:
    """Pull the numbers out of the article text. Returns None if they look wrong.

    The articles have a heading ("24-karat gold price") followed by a sentence
    ("The price of 24-karat gold reached approximately LE 6,857."), so we look
    for that heading first. If the layout changes we fall back to looser patterns.
    """
    n = r"([\d,]+(?:\.\d+)?)"
    out = {}
    for k in (24, 21, 18):
        out[f"k{k}"] = _find([
            rf"{k}-karat gold price\s+The price of[^.]*?LE\s?{n}",
            rf"{k}-karat gold[^.]*?LE\s?{n}",
        ], text)
    out["gold_pound"] = _find([
        rf"Gold pound price\s+The price of[^.]*?LE\s?{n}",
        rf"gold pound[^.]*?LE\s?{n}",
    ], text)
    out["ounce_usd"] = _find([
        rf"Global gold price\s+The price of[^.]*?\$\s?{n}",
        rf"ounce[^.]*?\$\s?{n}",
    ], text)
    out = {k: v for k, v in out.items() if v is not None}

    if "k21" not in out:
        return None
    # Sanity check: 21K should be about 21/24 of 24K.
    if "k24" in out and abs(out["k21"] - out["k24"] * 21 / 24) > 0.03 * out["k21"]:
        print("Skipped: karat prices do not match each other", out)
        return None
    return out


def article_text(html: str) -> str:
    """Text of the article only, so side boxes and related posts are ignored."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("article") or soup.find(class_=re.compile("entry-content|post-content|article-content"))
    return (body or soup).get_text(" ", strip=True)


def article_date(html: str) -> str | None:
    """Publication date (YYYY-MM-DD) from the page's meta tag, if present."""
    tag = BeautifulSoup(html, "html.parser").find("meta", property="article:published_time")
    if tag and tag.get("content"):
        return tag["content"][:10]
    return None


def latest_gold_articles():
    r = requests.get(FEED, headers=HEADERS, timeout=30)
    r.raise_for_status()
    items = []
    all_items = list(ET.fromstring(r.content).iter("item"))
    for it in all_items:
        title = (it.findtext("title") or "")
        if "gold" in title.lower():
            items.append((parsedate_to_datetime(it.findtext("pubDate")),
                          it.findtext("link"), title))
    print(f"Feed has {len(all_items)} articles, {len(items)} with 'gold' in the title")
    return sorted(items)  # oldest first, so the newest article wins per day


def save(row: dict) -> None:
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS gold_official (
        date TEXT PRIMARY KEY, k24 REAL, k21 REAL, k18 REAL,
        gold_pound REAL, ounce_usd REAL, source_url TEXT, fetched_at TEXT)""")
    con.execute("""INSERT INTO gold_official VALUES
        (:date,:k24,:k21,:k18,:gold_pound,:ounce_usd,:source_url,:fetched_at)
        ON CONFLICT(date) DO UPDATE SET k24=excluded.k24, k21=excluded.k21,
        k18=excluded.k18, gold_pound=excluded.gold_pound,
        ounce_usd=excluded.ounce_usd, source_url=excluded.source_url,
        fetched_at=excluded.fetched_at""", row)
    con.commit()
    con.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        # One article:  python update_gold_official.py <url>                 (test only)
        #               python update_gold_official.py <url> --save          (save it)
        #               python update_gold_official.py <url> --save --date 2026-07-26
        url = sys.argv[1]
        html = requests.get(url, headers=HEADERS, timeout=30).text
        prices = parse_prices(article_text(html))
        print(prices)
        if prices and "--save" in sys.argv:
            day = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else article_date(html)
            if not day:
                raise SystemExit("Could not find the article date. Add: --date YYYY-MM-DD")
            save({"date": day, "k24": prices.get("k24"), "k21": prices.get("k21"),
                  "k18": prices.get("k18"), "gold_pound": prices.get("gold_pound"),
                  "ounce_usd": prices.get("ounce_usd"), "source_url": url,
                  "fetched_at": datetime.now(timezone.utc).isoformat()})
            print("saved for", day)
        raise SystemExit
    saved = 0
    for pub, link, title in latest_gold_articles():
        html = requests.get(link, headers=HEADERS, timeout=30).text
        text = article_text(html)
        prices = parse_prices(text)
        if not prices:
            print("No prices found in:", title)
            continue
        save({"date": pub.strftime("%Y-%m-%d"),
              "k24": prices.get("k24"), "k21": prices.get("k21"),
              "k18": prices.get("k18"), "gold_pound": prices.get("gold_pound"),
              "ounce_usd": prices.get("ounce_usd"), "source_url": link,
              "fetched_at": datetime.now(timezone.utc).isoformat()})
        saved += 1
    print(saved, "days saved")
    if saved == 0:
        print("Nothing saved. To add an article by hand, run:\n"
              "  python scripts/update_gold_official.py <article url> --save")