"""
generate_sample_orders.py
--------------------------
Generates a deliberately messy `raw_orders_export.csv` (inconsistent date
formats, currency symbols, duplicate rows, missing emails) so the pipeline
can be tested end-to-end without needing a live store export.

Run once:
    python sample_data/generate_sample_orders.py
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"]
STATUSES = ["completed", "Completed", "cancelled", "refunded", "COMPLETED"]
SKUS = [f"SKU-{i:03d}" for i in range(1, 21)]


def random_date():
    d = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 300))
    fmt = random.choice(DATE_FORMATS)
    return d.strftime(fmt)


def random_price():
    price = round(random.uniform(5, 250), 2)
    return f"${price:,.2f}" if random.random() < 0.5 else str(price)


rows = []
for i in range(1, 501):
    order_id = f"ORD-{i:05d}"
    email = f"customer{i}@example.com" if random.random() > 0.05 else ""
    rows.append(
        {
            "order_id": order_id,
            "customer_email": email,
            "product_sku": random.choice(SKUS),
            "quantity": random.randint(1, 5),
            "unit_price": random_price(),
            "order_date": random_date(),
            "status": random.choice(STATUSES),
        }
    )

# inject some exact duplicate rows to simulate double-exports
rows += random.sample(rows, 15)

with open("sample_data/raw_orders_export.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to sample_data/raw_orders_export.csv")
