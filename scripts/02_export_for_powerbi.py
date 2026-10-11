"""Step 3: build clean, analysis-ready tables for Power BI.

Run (after 01_load_data.py and sql/03_delivery_analysis.sql):
    python scripts/run_sql.py sql/03_delivery_analysis.sql
    python scripts/02_export_for_powerbi.py

Creates three CSVs in powerbi/exports/:
    orders_fact.csv     one row per delivered order (delivery + review + value)
    items_fact.csv      one row per order item (category, seller, price)
    customers_fact.csv  one row per customer (first order, repeat flag)
"""
import sqlite3

import pandas as pd

from config import DB_PATH, EXPORT_DIR

ORDERS_SQL = """
WITH order_value AS (
    SELECT order_id,
           COUNT(*)                AS n_items,
           SUM(price)              AS items_value,
           SUM(freight_value)      AS freight_value
    FROM order_items
    GROUP BY order_id
),
order_category AS (
    SELECT oi.order_id,
           COALESCE(ct.product_category_name_english, p.product_category_name, 'unknown') AS main_category,
           ROW_NUMBER() OVER (PARTITION BY oi.order_id ORDER BY oi.price DESC) AS rn
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    LEFT JOIN category_translation ct ON ct.product_category_name = p.product_category_name
)
SELECT od.order_id,
       od.customer_unique_id,
       od.customer_state,
       date(od.order_purchase_timestamp)          AS purchase_date,
       date(od.order_delivered_customer_date)     AS delivered_date,
       date(od.order_estimated_delivery_date)     AS estimated_date,
       od.delivery_days,
       od.delay_days,
       od.is_late,
       od.delay_bucket,
       od.review_score,
       ov.n_items,
       ov.items_value,
       ov.freight_value,
       oc.main_category
FROM order_delivery od
LEFT JOIN order_value ov ON ov.order_id = od.order_id
LEFT JOIN order_category oc ON oc.order_id = od.order_id AND oc.rn = 1
"""

ITEMS_SQL = """
SELECT oi.order_id,
       oi.order_item_id,
       oi.product_id,
       COALESCE(ct.product_category_name_english, p.product_category_name, 'unknown') AS category,
       oi.seller_id,
       s.seller_state,
       oi.price,
       oi.freight_value
FROM order_items oi
JOIN order_delivery od ON od.order_id = oi.order_id
LEFT JOIN products p ON p.product_id = oi.product_id
LEFT JOIN category_translation ct ON ct.product_category_name = p.product_category_name
LEFT JOIN sellers s ON s.seller_id = oi.seller_id
"""

CUSTOMERS_SQL = """
WITH ranked AS (
    SELECT customer_unique_id, customer_state, is_late, review_score,
           date(order_purchase_timestamp) AS purchase_date,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY order_purchase_timestamp) AS rn,
           COUNT(*)     OVER (PARTITION BY customer_unique_id) AS n_orders
    FROM order_delivery
)
SELECT customer_unique_id,
       customer_state,
       purchase_date          AS first_order_date,
       is_late                AS first_order_late,
       review_score           AS first_order_score,
       n_orders,
       CASE WHEN n_orders > 1 THEN 1 ELSE 0 END AS is_repeat
FROM ranked
WHERE rn = 1
"""


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        # fail early with a clear message if the view has not been created
        try:
            con.execute("SELECT 1 FROM order_delivery LIMIT 1")
        except sqlite3.OperationalError:
            raise SystemExit("View order_delivery not found. Run: "
                             "python scripts/run_sql.py sql/03_delivery_analysis.sql")
        for name, sql in [("orders_fact", ORDERS_SQL),
                          ("items_fact", ITEMS_SQL),
                          ("customers_fact", CUSTOMERS_SQL)]:
            df = pd.read_sql_query(sql, con)
            df.to_csv(EXPORT_DIR / f"{name}.csv", index=False)
            print(f"{name}.csv  {len(df):>8,} rows  {df.shape[1]} columns")


if __name__ == "__main__":
    main()
