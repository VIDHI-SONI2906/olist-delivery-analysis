-- Main question: do late deliveries hurt customer satisfaction?
-- SQLite dialect. Run: python scripts/run_sql.py sql/03_delivery_analysis.sql
-- (Postgres port: replace julianday(a)-julianday(b) with (a::date - b::date)
--  and strftime('%Y-%m', x) with to_char(x, 'YYYY-MM').)

-- Build one clean row per delivered order. Rules:
--  * only delivered orders with a delivery date (and not delivered before purchase)
--  * if an order has several reviews, keep the most recent one
--  * delay_days = delivery date minus estimated date (positive = late)
DROP VIEW IF EXISTS order_delivery;
CREATE VIEW order_delivery AS
WITH latest_review AS (
    SELECT order_id, review_score,
           ROW_NUMBER() OVER (
               PARTITION BY order_id
               ORDER BY review_answer_timestamp DESC, review_creation_date DESC
           ) AS rn
    FROM order_reviews
),
base AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        c.customer_state,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        CAST(julianday(date(o.order_delivered_customer_date))
           - julianday(date(o.order_estimated_delivery_date)) AS INTEGER) AS delay_days,
        CAST(julianday(date(o.order_delivered_customer_date))
           - julianday(date(o.order_purchase_timestamp)) AS INTEGER) AS delivery_days,
        r.review_score
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    LEFT JOIN latest_review r ON r.order_id = o.order_id AND r.rn = 1
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
      AND o.order_delivered_customer_date >= o.order_purchase_timestamp
)
SELECT *,
       CASE WHEN delay_days > 0 THEN 1 ELSE 0 END AS is_late,
       CASE
           WHEN delay_days <= -8 THEN '1. Early 8+ days'
           WHEN delay_days <= -1 THEN '2. Early 1-7 days'
           WHEN delay_days = 0   THEN '3. On the day'
           WHEN delay_days <= 3  THEN '4. Late 1-3 days'
           WHEN delay_days <= 7  THEN '5. Late 4-7 days'
           ELSE                       '6. Late 8+ days'
       END AS delay_bucket
FROM base;

-- Q1 How many delivered orders arrive late?
SELECT COUNT(*) AS delivered_orders,
       SUM(is_late) AS late_orders,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS late_pct
FROM order_delivery;

-- Q2 Review score: late vs not late
SELECT is_late,
       COUNT(review_score) AS reviewed_orders,
       ROUND(AVG(review_score), 2) AS avg_score,
       ROUND(100.0 * SUM(review_score = 1) / COUNT(review_score), 1) AS pct_1_star,
       ROUND(100.0 * SUM(review_score = 5) / COUNT(review_score), 1) AS pct_5_star
FROM order_delivery
WHERE review_score IS NOT NULL
GROUP BY is_late;

-- Q3 Review score by how late/early the order was
SELECT delay_bucket,
       COUNT(review_score) AS reviewed_orders,
       ROUND(AVG(review_score), 2) AS avg_score,
       ROUND(100.0 * SUM(review_score = 1) / COUNT(review_score), 1) AS pct_1_star
FROM order_delivery
WHERE review_score IS NOT NULL
GROUP BY delay_bucket
ORDER BY delay_bucket;

-- Q4 Late rate by customer state (states with 500+ orders)
SELECT customer_state,
       COUNT(*) AS orders,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS late_pct,
       ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
       ROUND(AVG(review_score), 2) AS avg_score
FROM order_delivery
GROUP BY customer_state
HAVING COUNT(*) >= 500
ORDER BY late_pct DESC;

-- Q5 Monthly trend of late rate and average score
SELECT strftime('%Y-%m', order_purchase_timestamp) AS purchase_month,
       COUNT(*) AS orders,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS late_pct,
       ROUND(AVG(review_score), 2) AS avg_score
FROM order_delivery
GROUP BY purchase_month
HAVING COUNT(*) >= 100
ORDER BY purchase_month;

-- Q6 Sellers with the highest late rate (sellers with 50+ delivered orders)
WITH seller_orders AS (
    SELECT DISTINCT oi.seller_id, oi.order_id
    FROM order_items oi
)
SELECT so.seller_id,
       s.seller_state,
       COUNT(*) AS orders,
       ROUND(100.0 * SUM(od.is_late) / COUNT(*), 1) AS late_pct,
       ROUND(AVG(od.review_score), 2) AS avg_score
FROM seller_orders so
JOIN order_delivery od ON od.order_id = so.order_id
JOIN sellers s ON s.seller_id = so.seller_id
GROUP BY so.seller_id, s.seller_state
HAVING COUNT(*) >= 50
ORDER BY late_pct DESC
LIMIT 15;

-- Q7 Product categories: volume, late rate and score (categories with 300+ orders)
WITH order_category AS (
    SELECT oi.order_id,
           COALESCE(ct.product_category_name_english, p.product_category_name, 'unknown') AS category,
           ROW_NUMBER() OVER (PARTITION BY oi.order_id ORDER BY oi.price DESC) AS rn
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    LEFT JOIN category_translation ct ON ct.product_category_name = p.product_category_name
)
SELECT oc.category,
       COUNT(*) AS orders,
       ROUND(100.0 * SUM(od.is_late) / COUNT(*), 2) AS late_pct,
       ROUND(AVG(od.review_score), 2) AS avg_score
FROM order_category oc
JOIN order_delivery od ON od.order_id = oc.order_id
WHERE oc.rn = 1
GROUP BY oc.category
HAVING COUNT(*) >= 300
ORDER BY avg_score ASC
LIMIT 15;
