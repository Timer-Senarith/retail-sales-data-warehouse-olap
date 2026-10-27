"""Clean the synthetic department files and build a SQLite star schema.
Run: python build_warehouse.py (Python standard library only).
Source: synthetic practice data generated with OpenAI ChatGPT, Oct 25, 2026.
"""
from pathlib import Path
import csv
import sqlite3
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'cleaned'
OUT.mkdir(exist_ok=True)

def read(name):
    with (ROOT/'raw'/name).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))

def unique(rows):
    seen=set(); result=[]
    for r in rows:
        key=tuple(r.items())
        if key not in seen:
            seen.add(key); result.append(r.copy())
    return result

def amount(value):
    return Decimal(str(value).strip().replace('$','').replace(',',''))

def cents(value):
    return int((value*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def export(name, rows, fields):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

products_raw=read('products.csv');customers_raw=read('customers.csv');sales_raw=read('sales.csv')
products={}
for r in unique(products_raw):
    key=r['product_id'].strip().upper()
    cat=r['category'].strip().lower()
    categories={'electronics':'Electronics','furniture':'Furniture','office supplies':'Office Supplies',
                'home & kitchen':'Home & Kitchen','home and kitchen':'Home & Kitchen'}
    products[key]={'product_id':key,'product_name':r['product_name'].strip(),'category':categories[cat],
                   'list_price_cents':cents(amount(r['list_price'])),'unit_cost_cents':cents(amount(r['unit_cost']))}
regions={'MA':'Northeast','NY':'Northeast','IL':'Midwest','MI':'Midwest','GA':'South','TX':'South','WA':'West','CO':'West'}
customers={}
for r in unique(customers_raw):
    key=r['customer_id'].strip().upper();state=r['state'].strip().upper()
    customers[key]={'customer_id':key,'customer_name':r['customer_name'].strip(),'city':r['city'].strip(),
                    'state':state,'region':regions[state], 'segment':r['segment'].strip().title()}
accepted=[];rejects=[];repairs=[]
for r in unique(sales_raw):
    original=r.copy();reasons=[]
    cid=r['customer_id'].strip().upper();pid=r['product_id'].strip().upper()
    try: d=date.fromisoformat(r['sale_date'].replace('/','-'))
    except ValueError: reasons.append('Invalid date');d=None
    q=int(r['quantity'])
    if q<=0:reasons.append('Quantity must be positive; no returns in this exercise')
    if cid not in customers:reasons.append('Unmatched customer ID')
    if pid not in products:reasons.append('Unmatched product ID')
    if reasons:
        rejects.append({**original,'reason':'; '.join(reasons)});continue
    price=amount(r['unit_price']) if r['unit_price'].strip() else Decimal(products[pid]['list_price_cents'])/100
    if not r['unit_price'].strip():repairs.append({'sale_id':r['sale_id'],'repair':'Recovered missing unit price from fixed catalog'})
    disc=r['discount_rate'].strip()
    discount=Decimal(disc[:-1])/100 if disc.endswith('%') else Decimal(disc)
    assert 0<=discount<=1
    net=cents(Decimal(q)*price*(1-discount))
    if not r['sales_amount'].strip() or cents(amount(r['sales_amount']))!=net:
        repairs.append({'sale_id':r['sale_id'],'repair':'Recalculated missing or incorrect sales amount'})
    accepted.append({'sale_id':r['sale_id'],'date_key':int(d.strftime('%Y%m%d')),'product_id':pid,'customer_id':cid,
                     'quantity':q,'unit_price_cents':cents(price),'discount_rate':float(discount),'sales_amount_cents':net})
dates=[];d=date(2024,1,1)
while d<=date(2025,12,31):
    dates.append({'date_key':int(d.strftime('%Y%m%d')),'full_date':d.isoformat(),'year':d.year,
                  'quarter':(d.month-1)//3+1,'month_number':d.month,'month_name':d.strftime('%B')})
    d+=timedelta(days=1)
# Rebuild this generated database deterministically; raw files stay unchanged.
connection=sqlite3.connect(ROOT/'retail_warehouse.sqlite')
connection.execute('PRAGMA foreign_keys=ON')
connection.executescript('''
DROP VIEW IF EXISTS sales_for_dashboard;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_date(date_key INTEGER PRIMARY KEY,full_date TEXT NOT NULL UNIQUE,year INTEGER NOT NULL,quarter INTEGER NOT NULL,month_number INTEGER NOT NULL,month_name TEXT NOT NULL);
CREATE TABLE dim_product(product_id TEXT PRIMARY KEY,product_name TEXT NOT NULL,category TEXT NOT NULL,list_price_cents INTEGER NOT NULL CHECK(list_price_cents>0),unit_cost_cents INTEGER NOT NULL CHECK(unit_cost_cents>=0));
CREATE TABLE dim_customer(customer_id TEXT PRIMARY KEY,customer_name TEXT NOT NULL,city TEXT NOT NULL,state TEXT NOT NULL,region TEXT NOT NULL,segment TEXT NOT NULL);
CREATE TABLE fact_sales(sale_id TEXT PRIMARY KEY,date_key INTEGER NOT NULL REFERENCES dim_date(date_key),product_id TEXT NOT NULL REFERENCES dim_product(product_id),customer_id TEXT NOT NULL REFERENCES dim_customer(customer_id),quantity INTEGER NOT NULL CHECK(quantity>0),unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents>0),discount_rate REAL NOT NULL CHECK(discount_rate BETWEEN 0 AND 1),sales_amount_cents INTEGER NOT NULL CHECK(sales_amount_cents>=0));
''')
for table,rows in [('dim_date',dates),('dim_product',list(products.values())),('dim_customer',list(customers.values())),('fact_sales',accepted)]:
    fields=list(rows[0]); placeholders=','.join('?' for _ in fields)
    connection.executemany(f'INSERT INTO {table} ({",".join(fields)}) VALUES ({placeholders})',[tuple(r.values()) for r in rows])
    export(table+'.csv',rows,fields)
connection.executescript('''
CREATE INDEX idx_sales_date ON fact_sales(date_key);
CREATE INDEX idx_sales_product ON fact_sales(product_id);
CREATE INDEX idx_sales_customer ON fact_sales(customer_id);
CREATE VIEW sales_for_dashboard AS
SELECT f.sale_id,d.full_date,d.year,d.quarter,d.month_number,d.month_name,p.product_name,p.category,c.region,c.segment,f.quantity,f.sales_amount_cents/100.0 AS sales_amount
FROM fact_sales f JOIN dim_date d USING(date_key) JOIN dim_product p USING(product_id) JOIN dim_customer c USING(customer_id);
''')
assert not connection.execute('PRAGMA foreign_key_check').fetchall()
assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert len(accepted)==1185 and len(rejects)==15 and len(products)==24 and len(customers)==120
assert connection.execute('SELECT SUM(sales_amount_cents) FROM fact_sales').fetchone()[0]==sum(r['sales_amount_cents'] for r in accepted)
connection.commit()
export('rejected_sales.csv',rejects,list(rejects[0]))
export('repair_log.csv',repairs,['sale_id','repair'])
checks={'raw_sales':len(sales_raw),'duplicate_sales_removed':len(sales_raw)-len(unique(sales_raw)),
        'rejected_sales':len(rejects),'accepted_sales':len(accepted),'products':len(products),'customers':len(customers),
        'calendar_dates':len(dates),'recovered_prices':sum('price' in r['repair'] for r in repairs),
        'corrected_or_recovered_amounts':sum('amount' in r['repair'] for r in repairs),
        'sales_total_usd':sum(r['sales_amount_cents'] for r in accepted)/100,
        'foreign_key_check':'passed','sqlite_integrity_check':'passed'}
(ROOT/'validation.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
connection.close()
