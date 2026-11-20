
import os
import sqlite3

import pandas as pd

DB = "finance.db"
OUT = "data"
TABLES = {  # table name -> columns that identify a row
    "fx_rates": ["date", "currency"],
    "stock_prices": ["date", "ticker"],
    "gold_official": ["date"],
}

os.makedirs(OUT, exist_ok=True)
con = sqlite3.connect(DB)
for table, key in TABLES.items():
    try:
        new = pd.read_sql(f"SELECT * FROM {table}", con)
    except Exception:
        print("skip (no table):", table)
        continue
    path = f"{OUT}/{table}.csv"
    if os.path.exists(path):
        old = pd.read_csv(path)
        new = pd.concat([old, new], ignore_index=True)
    new = new.drop_duplicates(subset=key, keep="last").sort_values(key)
    new.to_csv(path, index=False)
    print(table, len(new), "rows")
con.close()
