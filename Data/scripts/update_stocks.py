"""Save daily stock prices (EGX stocks via Yahoo Finance, EGX indices via egx).

Usage:
    python update_stocks.py          # last 30 days
    python update_stocks.py 365      # last 365 days

Needs: pip install yfinance egx pandas
Yahoo Finance data is unofficial. Compare a few prices with the EGX website.
"""
import sqlite3
import sys

import pandas as pd

DB = "finance.db"
# Check each ticker on Yahoo Finance before relying on it.
TICKERS = ["COMI.CA", "TMGH.CA", "EAST.CA", "SWDY.CA", "HRHO.CA", "ETEL.CA"]
INDICES = ["EGX30"]


def normalize(df: pd.DataFrame, ticker: str, source: str) -> pd.DataFrame:
    """Turn a downloaded table into rows: date, ticker, open, high, low, close, volume."""
    if isinstance(df.columns, pd.MultiIndex):  # newer yfinance versions
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.columns = [str(c).strip().lower() for c in df.columns]
    out = pd.DataFrame({
        "date": pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d"),
        "ticker": ticker,
        "open": pd.to_numeric(df.get("open"), errors="coerce"),
        "high": pd.to_numeric(df.get("high"), errors="coerce"),
        "low": pd.to_numeric(df.get("low"), errors="coerce"),
        "close": pd.to_numeric(df.get("close"), errors="coerce"),
        "volume": pd.to_numeric(df.get("volume"), errors="coerce"),
        "source": source,
    })
    return out.dropna(subset=["date", "close"])


def fetch_stocks(days: int) -> list:
    import yfinance as yf
    frames = []
    for t in TICKERS:
        df = yf.download(t, period=f"{days}d", auto_adjust=False, progress=False)
        if df.empty:
            print("No data for", t)
            continue
        frames.append(normalize(df, t, "yahoo"))
    return frames


def fetch_indices(days: int) -> list:
    import egx
    frames = []
    for name in INDICES:
        try:
            df = egx.get_index_data(name, period=days)
            frames.append(normalize(df, name, "egx"))
        except Exception as e:  # the index feed is unofficial and can change
            print("Index", name, "failed:", e)
    return frames


def save(df: pd.DataFrame) -> None:
    df = df.copy()
    df["fetched_at"] = pd.Timestamp.now().isoformat()
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS stock_prices (
        date TEXT, ticker TEXT, open REAL, high REAL, low REAL, close REAL,
        volume REAL, source TEXT, fetched_at TEXT,
        PRIMARY KEY (date, ticker))""")
    con.executemany("""INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(date, ticker) DO UPDATE SET
            open=excluded.open, high=excluded.high, low=excluded.low,
            close=excluded.close, volume=excluded.volume,
            source=excluded.source, fetched_at=excluded.fetched_at""",
        df[["date", "ticker", "open", "high", "low", "close", "volume",
            "source", "fetched_at"]].astype(object).where(df.notna(), None).values.tolist())
    con.commit()
    con.close()


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 30
    frames = fetch_stocks(days) + fetch_indices(days)
    if not frames:
        raise SystemExit("Nothing fetched; keeping existing data")
    all_rows = pd.concat(frames, ignore_index=True)
    save(all_rows)
    print(len(all_rows), "rows saved for", all_rows["ticker"].nunique(), "tickers")
