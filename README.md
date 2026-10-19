# Do Late Deliveries Hurt Customer Satisfaction? An End-to-End Analysis of 99K E-commerce Orders

**Tools:** SQL (SQLite), Python (pandas, SciPy, statsmodels, seaborn), Power BI
**Dataset:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (about 100K orders, 2016-2018, 9 linked tables)

## Business question
Olist connects small sellers with customers across Brazil. Delivery is the part of the
experience the marketplace controls least. This project asks:

1. How often do orders arrive after the estimated date, and where (states, sellers, categories)?
2. How much do late deliveries lower review scores?
3. Do customers whose first order was late come back less often?

## Key findings
- **Late delivery rate:** 6.8% of 96,470 delivered orders arrived after the estimated date.
- **Review gap:** late orders averaged 2.27 stars vs 4.29 for on-time orders (gap 2.02, 95% CI 1.98-2.06, p < 0.001).
- **Dose-response:** the share of 1-2 star reviews rose from 9% for orders delivered 8+ days early to 79% for orders 8+ days late.
- **Adjusted effect:** controlling for order value, freight share and delivery time, late orders had 8.7x the odds of a 1-2 star review (95% CI 8.1-9.4).
- **Geography:** late rates were highest in MA (17%), CE (14%), BA and RJ (12%), and lowest in SP (4.5%) and PR (4%). Late rates also spiked in Nov 2017, Feb 2018 and Mar 2018.
- **Repeat purchases:** only 3% of customers ordered twice. Customers whose first order arrived late repeated 2.80% of the time vs 4.24% for on-time first orders (p = 0.0007).

## Recommendations
- About 74% of reviewed orders arrive 8+ days before the estimated date, so the estimates are padded and a missed date feels like a broken promise. Set more realistic estimates for high-late states (MA, CE, BA, RJ).
- Review sellers with the highest late rates (some are late on 20-30% of orders).
- Warn customers early when an order will be late.

## Method
| Step | What | Where |
|---|---|---|
| 1 | Load 8 CSVs into SQLite | `scripts/01_load_data.py` |
| 2 | Data quality checks (duplicates, missing delivery dates, multiple reviews per order) | `sql/02_data_quality_checks.sql` |
| 3 | Build one clean row per delivered order; delay metrics; slice by state, seller, category, month | `sql/03_delivery_analysis.sql` |
| 4 | Repeat-purchase analysis and monthly cohort retention | `sql/04_repeat_customers.sql` |
| 5 | Statistical tests, bootstrap CI, logistic regression, charts | `analysis/analysis.py` |
| 6 | Export tables and build a 3-page dashboard | `scripts/02_export_for_powerbi.py`, `powerbi/POWERBI_GUIDE.md` |

**Data cleaning decisions**
- Kept only delivered orders that have a delivery date, and removed rows where the delivery date is before the purchase date.
- When an order had several reviews, kept the most recent one.
- Delay = delivery date minus estimated delivery date (positive means late).
- Repeat-purchase analysis only uses customers whose first order was before 2018-01-01, so each had time to buy again.

## How to run
```bash
pip install -r requirements.txt
# 1. Download the dataset from Kaggle and unzip the CSVs into data/raw/
python scripts/01_load_data.py
python scripts/run_sql.py sql/02_data_quality_checks.sql
python scripts/run_sql.py sql/03_delivery_analysis.sql
python scripts/run_sql.py sql/04_repeat_customers.sql
python scripts/02_export_for_powerbi.py
python analysis/analysis.py          # results go to reports/ and reports/figures/
```
Then follow `powerbi/POWERBI_GUIDE.md` to build the dashboard.

## Dashboard
![Delivery & Satisfaction dashboard](reports/figures/delivery_dashboard.png)
![Sales Overview dashboard](reports/figures/sales_dashboard.png)

## Limitations
- Observational data: results show association, not proof that lateness causes lower scores.
- Only orders with a review are in the score analysis, and reviewers are a self-selected group.
- Most customers buy once, so repeat-rate differences have wide uncertainty; check the group sizes.
- The dataset ends in 2018, so findings describe that period.

## Project structure
```
data/raw/        Kaggle CSVs (not committed)
sql/             quality checks, delivery analysis, repeat customers
scripts/         loader, SQL runner, Power BI export
analysis/        Python statistical analysis (notebook-style script)
reports/         result tables and figures
powerbi/         build guide, exports, .pbix file
```
