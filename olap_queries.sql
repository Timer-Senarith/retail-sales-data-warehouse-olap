-- 1. SLICE: hold year fixed at 2025, compare categories.
SELECT p.category, ROUND(SUM(f.sales_amount_cents)/100.0,2) AS sales_usd
FROM fact_sales f
JOIN dim_product p USING(product_id)
JOIN dim_date d USING(date_key)
WHERE d.year=2025
GROUP BY p.category ORDER BY sales_usd DESC;

-- 2. DICE: select values across year, category and region.
SELECT p.category,c.region,ROUND(SUM(f.sales_amount_cents)/100.0,2) AS sales_usd
FROM fact_sales f
JOIN dim_product p USING(product_id)
JOIN dim_customer c USING(customer_id)
JOIN dim_date d USING(date_key)
WHERE d.year=2025 AND p.category IN ('Electronics','Furniture')
AND c.region IN ('Northeast','West')
GROUP BY p.category,c.region ORDER BY p.category,c.region;

-- 3. DRILL-DOWN: year totals, then quarters, then months.
-- UNION ALL displays the three aggregation levels in one query.
-- Compare within a level; never sum totals across levels.
SELECT 'Year' AS level,d.year,NULL AS quarter,NULL AS month_number,
       ROUND(SUM(f.sales_amount_cents)/100.0,2) AS sales_usd
FROM fact_sales f JOIN dim_date d USING(date_key) GROUP BY d.year
UNION ALL
SELECT 'Quarter',d.year,d.quarter,NULL,ROUND(SUM(f.sales_amount_cents)/100.0,2)
FROM fact_sales f JOIN dim_date d USING(date_key) GROUP BY d.year,d.quarter
UNION ALL
SELECT 'Month',d.year,d.quarter,d.month_number,ROUND(SUM(f.sales_amount_cents)/100.0,2)
FROM fact_sales f JOIN dim_date d USING(date_key) GROUP BY d.year,d.quarter,d.month_number
ORDER BY year,quarter,month_number;
