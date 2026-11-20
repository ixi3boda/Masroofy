"""Fetch CBE exchange rates and save them to SQLite (run once a day).

Usage:
    python update_fx.py              # last 7 days
    python update_fx.py 30           # last 30 days
    python update_fx.py --debug      # print what the server returns

Needs: pip install requests beautifulsoup4 pandas lxml
"""
import io
import re
import sqlite3
import sys
from datetime import date, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup

DB = "finance.db"
BASE = "https://www.cbe.org.eg"
PAGE = BASE + "/en/economic-research/statistics/cbe-exchange-rates/historical-data"
API = BASE + "/api/statistics/GetHistoricalData"
CURRENCIES = ["US Dollar", "Euro", "Pound Sterling", "Canadian Dollar",
              "Swedish Krona", "Swiss Franc", "Japanese Yen 100"]
HEADERS = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
    "accept-language": "en-US,en;q=0.8",
}


def hidden_fields(html: str) -> dict:
    """Read the token, uid and data source id the page puts in its form."""
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    for name in ("__RequestVerificationToken", "uid", "DataSourceId"):
        tag = soup.find("input", {"name": name})
        if tag and tag.get("value"):
            out[name] = tag["value"]
    missing = [n for n in ("__RequestVerificationToken", "uid", "DataSourceId")
               if n not in out]
    if missing:
        raise RuntimeError(f"Could not find {missing} on the page. "
                           "The site may have changed, or it blocked the request.")
    return out


def fetch_cbe(start: date, end: date, debug: bool = False) -> pd.DataFrame:
    s = requests.Session()
    s.headers.update(HEADERS)

    # 1) Open the page first to get cookies and the hidden form values.
    r = s.get(PAGE, timeout=30)
    r.raise_for_status()
    fields = hidden_fields(r.text)

    # 2) Send the same form the "Show Data" button sends.
    data = [
        ("__RequestVerificationToken", fields["__RequestVerificationToken"]),
        ("uid", fields["uid"]),
        ("DataSourceId", fields["DataSourceId"]),
        ("FallbackUrl", "/en/economic-research/statistics/cbe-exchange-rates/historical-data"),
        ("LanguageName", "en"),
        ("FromDateRaw", start.strftime("%d/%m/%Y")),
        ("ToDateRaw", end.strftime("%d/%m/%Y")),
        ("SubmitAction", "1"),
    ]
    for c in CURRENCIES:
        data.append(("SelectedSelectOptions", c))
        data.append(("multiselect_multipleSelectID", c))

    r = s.post(API, data=data, timeout=30, headers={
        "origin": BASE, "referer": PAGE,
        "x-requested-with": "XMLHttpRequest",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    })
    r.raise_for_status()
    if debug:
        print(r.text[:1500])

    # 3) The answer is probably an HTML table. If it is JSON, adjust here.
    tables = pd.read_html(io.StringIO(r.text))
    df = max(tables, key=len)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df[["date", "currency", "buy", "sell"]]
    df["date"] = pd.to_datetime(df["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
    df["currency"] = df["currency"].astype(str).str.strip()
    df["buy"] = pd.to_numeric(df["buy"], errors="coerce")
    df["sell"] = pd.to_numeric(df["sell"], errors="coerce")
    return df.dropna()


def save(df: pd.DataFrame) -> None:
    df = df.copy()
    df["source"] = "CBE"
    df["fetched_at"] = pd.Timestamp.now().isoformat()
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS fx_rates (
        date TEXT, currency TEXT, buy REAL, sell REAL,
        source TEXT, fetched_at TEXT,
        PRIMARY KEY (date, currency))""")
    con.executemany("""INSERT INTO fx_rates VALUES (?,?,?,?,?,?)
        ON CONFLICT(date, currency) DO UPDATE SET
            buy=excluded.buy, sell=excluded.sell, fetched_at=excluded.fetched_at""",
        df[["date", "currency", "buy", "sell", "source", "fetched_at"]].values.tolist())
    con.commit()
    con.close()


if __name__ == "__main__":
    debug = "--debug" in sys.argv
    nums = [a for a in sys.argv[1:] if a.isdigit()]
    days = int(nums[0]) if nums else 7
    today = date.today()
    df = fetch_cbe(today - timedelta(days=days), today, debug=debug)
    if df.empty:
        raise SystemExit("No rows fetched; keeping existing data")
    save(df)
    print(len(df), "rows saved")
