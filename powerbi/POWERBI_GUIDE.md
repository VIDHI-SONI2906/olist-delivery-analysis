# Power BI build guide (for a first-time user)

You cannot skip this part: the dashboard has to be built in Power BI Desktop.
Everything it needs is already prepared in `powerbi/exports/`.

## 0. Prepare the data (once)
```
python scripts/run_sql.py sql/03_delivery_analysis.sql
python scripts/02_export_for_powerbi.py
```

## 1. Import
Power BI Desktop -> **Get data -> Text/CSV**, and load all three files:
`orders_fact.csv`, `items_fact.csv`, `customers_fact.csv`.
In Power Query check the types: dates = Date, `is_late`/`is_repeat` = Whole number,
`price`/`items_value` = Fixed decimal. Then **Close & Apply**.

## 2. Create a calendar table
Modeling -> New table:
```
Calendar = CALENDAR ( MIN ( orders_fact[purchase_date] ), MAX ( orders_fact[purchase_date] ) )
```
Add columns: `Year = YEAR('Calendar'[Date])`, `Month = FORMAT('Calendar'[Date], "YYYY-MM")`.
Mark it as a date table (Table tools -> Mark as date table).

## 3. Relationships (Model view)
- `Calendar[Date]` 1 -> * `orders_fact[purchase_date]`
- `orders_fact[order_id]` 1 -> * `items_fact[order_id]` (single direction, orders filters items)
- `customers_fact` stays standalone (it is already one row per customer)

## 4. Measures (Modeling -> New measure)
```
Orders = DISTINCTCOUNT ( orders_fact[order_id] )
Revenue = SUM ( items_fact[price] )
Avg Order Value = DIVIDE ( [Revenue], [Orders] )
Freight Share = DIVIDE ( SUM ( items_fact[freight_value] ), [Revenue] )

Late Orders = CALCULATE ( [Orders], orders_fact[is_late] = 1 )
Late Delivery % = DIVIDE ( [Late Orders], [Orders] )
Avg Review Score = AVERAGE ( orders_fact[review_score] )
% 1-Star = DIVIDE ( CALCULATE ( [Orders], orders_fact[review_score] = 1 ),
                    CALCULATE ( [Orders], NOT ISBLANK ( orders_fact[review_score] ) ) )
Avg Delivery Days = AVERAGE ( orders_fact[delivery_days] )

Revenue Last Month = CALCULATE ( [Revenue], DATEADD ( 'Calendar'[Date], -1, MONTH ) )
Revenue MoM % = DIVIDE ( [Revenue] - [Revenue Last Month], [Revenue Last Month] )

Customers = DISTINCTCOUNT ( customers_fact[customer_unique_id] )
Repeat Customer % = DIVIDE ( CALCULATE ( [Customers], customers_fact[is_repeat] = 1 ), [Customers] )
```
Put all measures in a table called `_Measures` to keep the model tidy.

## 5. Pages to build

**Page 1 - Sales overview**
- Cards: Revenue, Orders, Avg Order Value, Avg Review Score
- Line chart: Revenue by `Calendar[Month]`
- Bar chart: Revenue by `items_fact[category]` (Top N = 10)
- Bar/map: Revenue or Orders by `orders_fact[customer_state]`
- Slicers: Year, State

**Page 2 - Delivery and satisfaction (the main story)**
- Cards: Late Delivery %, Avg Delivery Days, Avg Review Score
- Column chart: Avg Review Score by `orders_fact[delay_bucket]` (sorting works because buckets start with 1-6)
- Bar chart: Late Delivery % by `customer_state`
- Line chart: Late Delivery % by Month
- Table: sellers or categories with the highest Late Delivery % (add a visual-level filter: Orders >= 50)
- Text box with 2-3 sentence takeaway written from your own results

**Page 3 - Customer retention**
- Cards: Customers, Repeat Customer %
- Column chart: Repeat Customer % by `customers_fact[first_order_late]`
- Column chart: Repeat Customer % by `customers_fact[first_order_score]`
- Add a note on the page about the limitation (most customers order once)

## 6. Polish checklist
- One colour for "good", one for "bad" (for example blue and red) used consistently
- Titles that state the insight ("Orders 8+ days late score 1.3 points lower") rather than the field names
- Align and size visuals on the grid; turn off unneeded gridlines; format numbers ($, %, 1 decimal)
- Sync the Year and State slicers across pages (View -> Sync slicers)
- Rename pages and visuals; hide helper columns

## 7. Deliver
- Save as `powerbi/olist_dashboard.pbix`
- Export each page as PNG (File -> Export, or screenshot) into `reports/figures/`
- Optional: publish to Power BI Service and add the link in the README
