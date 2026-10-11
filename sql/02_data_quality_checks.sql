-- Data quality checks. Run: python scripts/run_sql.py sql/02_data_quality_checks.sql
-- Write down what you find and how you handle it (this goes in the README).

-- Q1 Row counts per table
SELECT 'customers' AS tbl, COUNT(*) AS n FROM customers
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers;

-- Q2 Order status breakdown (only 'delivered' orders have a delivery date)
SELECT order_status, COUNT(*) AS orders,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct
FROM orders
GROUP BY order_status
ORDER BY orders DESC;

-- Q3 Delivered orders missing a delivery date (should be a tiny number)
SELECT COUNT(*) AS delivered_without_date
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;

-- Q4 Duplicate order_ids (should be 0)
SELECT COUNT(*) AS duplicate_order_ids
FROM (SELECT order_id FROM orders GROUP BY order_id HAVING COUNT(*) > 1);

-- Q5 Orders with more than one review (needs a de-duplication rule)
SELECT COUNT(*) AS orders_with_multiple_reviews
FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*) > 1);

-- Q6 Delivered orders with no review at all
SELECT COUNT(*) AS delivered_orders_without_review
FROM orders o
WHERE o.order_status = 'delivered'
  AND NOT EXISTS (SELECT 1 FROM order_reviews r WHERE r.order_id = o.order_id);

-- Q7 Delivery date earlier than purchase date (impossible; check for bad rows)
SELECT COUNT(*) AS delivered_before_purchase
FROM orders
WHERE order_delivered_customer_date < order_purchase_timestamp;

-- Q8 Products with no category
SELECT COUNT(*) AS products_without_category
FROM products
WHERE product_category_name IS NULL;

-- Q9 Date range of the data
SELECT MIN(order_purchase_timestamp) AS first_order,
       MAX(order_purchase_timestamp) AS last_order
FROM orders;
