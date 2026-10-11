# Resume bullets (fill in AFTER you have run the project - use only your real numbers)

**Olist E-commerce Delivery & Satisfaction Analysis** | SQL, Python, Power BI | [GitHub link]
- Analyzed ~[N]K delivered orders across 8 relational tables using SQL (CTEs, window functions, cohort queries) to measure how delivery delays affect customer reviews and repeat purchases.
- Found that late orders ([X]% of deliveries) scored [Y] points lower on average ([a]-[b] 95% CI), with orders 8+ days late reaching [Z]% 1-2 star reviews; validated with Mann-Whitney U and logistic regression controlling for order value and freight.
- Built a 3-page Power BI dashboard (sales overview, delivery performance, retention) with DAX measures and slicers; recommended [one concrete action, e.g. seller/state-level delivery-estimate fixes].

Rules to keep it defensible:
- Every number must come from your own run (reports/*.csv or the dashboard).
- If the repeat-purchase difference is not significant, say so, or leave that claim out.
- Be ready to explain: why Mann-Whitney, how you handled multiple reviews, why the 2018-01-01 cutoff.
