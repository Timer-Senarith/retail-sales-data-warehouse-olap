# Power BI model and dashboard guide

The Power BI workflow used cleaned CSV exports from the SQLite warehouse, with relationships recreated in the Power BI semantic model. It did not use a direct SQLite connection. This workflow description was supplied by the project owner; no PBIX, PBIP, screenshots, or recording were present in the supplied folder, so report layout and interactions could not be independently inspected.

Import `cleaned/fact_sales.csv`, `cleaned/dim_date.csv`, `cleaned/dim_product.csv`, and `cleaned/dim_customer.csv` through Get Data > Text/CSV. Use whole numbers for keys, quantities, and cents, text for product/customer IDs, decimal for discount_rate, and Date for full_date.

Create one-to-many relationships from each dimension to fact_sales, using date_key, product_id, and customer_id respectively. Use single-direction dimension-to-fact filtering. Mark dim_date as the date table using full_date. Create a Year > Quarter > Month hierarchy; sort month_name by month_number. Quarter and month are separate numeric columns, not automatically generated date levels.

Create each measure in `measures.dax` separately. Format Total Sales, Gross Profit, and Average Line Value as USD; Units Sold and Sales Lines as whole numbers. Gross profit subtracts catalog unit cost times quantity from discounted revenue; it excludes operating expenses.

## Visual configuration for reproduction

Use cards for Total Sales, Gross Profit, and Units Sold; a column chart with the calendar hierarchy for sales drill-down; category bars; a category-by-region sales matrix; and a product sales ranking. Add year, quarter, category, region, and segment slicers. These are recommended configurations, not independently verified report artifacts.

Validate an unfiltered model against $295,490.58 Total Sales, $115,089.25 Gross Profit, and 4,131 Units Sold. Select 2025 to compare category values with `query_results/slice.csv`; additionally select Electronics/Furniture and Northeast/West for `dice.csv`. Compare each calendar aggregation level separately with `drill_down.csv`—do not sum across levels.
