"""Step 1: load the raw Olist CSVs into a local SQLite database.

Run from the project root:  python scripts/01_load_data.py
"""
import sqlite3
import sys

import pandas as pd

from config import DATE_COLUMNS, DB_PATH, RAW_DIR, TABLES


def main() -> None:
    missing = [f for f in TABLES if not (RAW_DIR / f).exists()]
    if missing:
        print(f"Missing files in {RAW_DIR}:")
        for f in missing:
            print(f"  - {f}")
        print("\nDownload the dataset from Kaggle (olistbr/brazilian-ecommerce) "
              "and unzip the CSVs into data/raw/.")
        sys.exit(1)

    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as con:
        for filename, table in TABLES.items():
            df = pd.read_csv(RAW_DIR / filename)
            for col in DATE_COLUMNS.get(table, []):
                # store as ISO text so SQLite date functions work
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
            df.to_sql(table, con, index=False)
            print(f"{table:<22} {len(df):>8,} rows")

        con.executescript(
            """
            CREATE INDEX idx_orders_id        ON orders(order_id);
            CREATE INDEX idx_orders_customer  ON orders(customer_id);
            CREATE INDEX idx_items_order      ON order_items(order_id);
            CREATE INDEX idx_reviews_order    ON order_reviews(order_id);
            CREATE INDEX idx_customers_id     ON customers(customer_id);
            """
        )
    print(f"\nDatabase written to {DB_PATH}")


if __name__ == "__main__":
    main()
