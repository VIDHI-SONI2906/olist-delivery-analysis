-- Does a bad first delivery make customers less likely to come back?
-- Requires the order_delivery view from 03_delivery_analysis.sql
-- Run: python scripts/run_sql.py sql/04_repeat_customers.sql

-- Q1 How many customers order more than once?
WITH per_customer AS (
    SELECT customer_unique_id, COUNT(*) AS n_orders
    FROM order_delivery
    GROUP BY customer_unique_id
)
SELECT COUNT(*) AS customers,
       SUM(n_orders > 1) AS repeat_customers,
       ROUND(100.0 * SUM(n_orders > 1) / COUNT(*), 2) AS repeat_pct
FROM per_customer;

-- Q2 Repeat rate by whether the FIRST order arrived late
-- Only customers whose first order was before 2018-01-01 are used, so every
-- customer had at least ~8 months to place a second order (avoids bias from
-- recent customers who simply haven't had time yet).
WITH ranked AS (
    SELECT customer_unique_id, is_late, review_score,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY order_purchase_timestamp) AS rn,
           COUNT(*)     OVER (PARTITION BY customer_unique_id) AS n_orders,
           MIN(order_purchase_timestamp) OVER (PARTITION BY customer_unique_id) AS first_order_ts
    FROM order_delivery
)
SELECT is_late AS first_order_late,
       COUNT(*) AS customers,
       SUM(n_orders > 1) AS repeaters,
       ROUND(100.0 * SUM(n_orders > 1) / COUNT(*), 2) AS repeat_pct
FROM ranked
WHERE rn = 1 AND first_order_ts < '2018-01-01'
GROUP BY is_late;

-- Q3 Repeat rate by the review score given on the first order
WITH ranked AS (
    SELECT customer_unique_id, review_score,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY order_purchase_timestamp) AS rn,
           COUNT(*)     OVER (PARTITION BY customer_unique_id) AS n_orders,
           MIN(order_purchase_timestamp) OVER (PARTITION BY customer_unique_id) AS first_order_ts
    FROM order_delivery
)
SELECT review_score AS first_order_score,
       COUNT(*) AS customers,
       ROUND(100.0 * SUM(n_orders > 1) / COUNT(*), 2) AS repeat_pct
FROM ranked
WHERE rn = 1 AND first_order_ts < '2018-01-01' AND review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;

-- Q4 Monthly cohort retention: of customers acquired in a month, how many
-- ordered again 1, 2, 3 ... months later? (cohorts with 300+ customers)
WITH first_orders AS (
    SELECT customer_unique_id,
           MIN(order_purchase_timestamp) AS first_ts
    FROM order_delivery
    GROUP BY customer_unique_id
),
activity AS (
    SELECT od.customer_unique_id,
           strftime('%Y-%m', fo.first_ts) AS cohort_month,
           (CAST(strftime('%Y', od.order_purchase_timestamp) AS INTEGER) * 12
            + CAST(strftime('%m', od.order_purchase_timestamp) AS INTEGER))
         - (CAST(strftime('%Y', fo.first_ts) AS INTEGER) * 12
            + CAST(strftime('%m', fo.first_ts) AS INTEGER)) AS months_since_first
    FROM order_delivery od
    JOIN first_orders fo ON fo.customer_unique_id = od.customer_unique_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_customers
    FROM activity
    WHERE months_since_first = 0
    GROUP BY cohort_month
)
SELECT a.cohort_month,
       cs.cohort_customers,
       a.months_since_first,
       COUNT(DISTINCT a.customer_unique_id) AS active_customers,
       ROUND(100.0 * COUNT(DISTINCT a.customer_unique_id) / cs.cohort_customers, 2) AS retention_pct
FROM activity a
JOIN cohort_size cs ON cs.cohort_month = a.cohort_month
WHERE a.months_since_first BETWEEN 1 AND 6
  AND cs.cohort_customers >= 300
GROUP BY a.cohort_month, cs.cohort_customers, a.months_since_first
ORDER BY a.cohort_month, a.months_since_first;
