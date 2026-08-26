"""
Synthetic e-commerce source data generator.

Simulates a realistic operational system dropping daily batches into a
landing zone: new/updated customers, new products, new orders, order items,
and payments. Deliberately injects the kind of messiness real DE pipelines
have to handle:

  - duplicate rows (upstream system re-sends records)
  - late-arriving payment records (payment lands a day or two after the order)
  - customer profile updates over time (for SCD2 dimension modeling)
  - inconsistent casing / whitespace in categorical fields
  - a handful of nulls and orphaned foreign keys (bad product_id on an order item)

Run: python generate_source_data.py
Output: data/landing/<entity>/<date>/*.csv  (one folder per simulated day)
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

ROOT = Path(__file__).resolve().parent.parent
LANDING = ROOT / "data" / "landing"

N_DAYS = 21
START_DATE = datetime(2026, 6, 1)
NEW_CUSTOMERS_PER_DAY = (5, 20)
NEW_ORDERS_PER_DAY = (30, 90)
CATEGORIES = ["Electronics", "Home & Kitchen", "Apparel", "Beauty", "Sports", "Books", "Toys"]
COUNTRIES = ["United States", "Canada", "United Kingdom", "Germany", "France", "Australia"]
CHANNELS = ["web", "mobile_app", "marketplace"]
PAYMENT_METHODS = ["credit_card", "paypal", "gift_card", "bank_transfer"]

customers = {}
products = {}
order_id_counter = 1
customer_id_counter = 1
product_id_counter = 1


def messy_country(country):
    """Occasionally corrupt casing/whitespace to simulate dirty source data."""
    r = random.random()
    if r < 0.08:
        return country.upper()
    if r < 0.14:
        return f" {country.lower()} "
    return country


def new_customer(day):
    global customer_id_counter
    cid = customer_id_counter
    customer_id_counter += 1
    rec = {
        "customer_id": cid,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email() if random.random() > 0.03 else None,  # ~3% missing email
        "country": messy_country(random.choice(COUNTRIES)),
        "signup_date": day.strftime("%Y-%m-%d"),
        "is_active": True,
        "_updated_at": day.strftime("%Y-%m-%d %H:%M:%S"),
    }
    customers[cid] = rec
    return rec


def maybe_update_customer(day):
    """Simulate a profile update (address/email change) for SCD2 testing."""
    if not customers or random.random() > 0.05:
        return None
    cid = random.choice(list(customers.keys()))
    rec = dict(customers[cid])
    rec["country"] = messy_country(random.choice(COUNTRIES))
    rec["_updated_at"] = day.strftime("%Y-%m-%d %H:%M:%S")
    customers[cid] = rec
    return rec


def seed_products():
    global product_id_counter
    n_products = 120
    rows = []
    for _ in range(n_products):
        pid = product_id_counter
        product_id_counter += 1
        category = random.choice(CATEGORIES)
        cost = round(random.uniform(3, 200), 2)
        price = round(cost * random.uniform(1.3, 2.5), 2)
        rec = {
            "product_id": pid,
            "product_name": fake.catch_phrase(),
            "category": category,
            "unit_cost": cost,
            "unit_price": price,
            "created_at": START_DATE.strftime("%Y-%m-%d"),
        }
        products[pid] = rec
        rows.append(rec)
    return pd.DataFrame(rows)


def make_order(day):
    global order_id_counter
    if not customers:
        return None, [], []
    oid = order_id_counter
    order_id_counter += 1
    customer_id = random.choice(list(customers.keys()))
    order_ts = day + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
    status = random.choices(
        ["completed", "completed", "completed", "cancelled", "returned"],
        weights=[70, 10, 10, 5, 5],
    )[0]
    channel = random.choice(CHANNELS)

    order = {
        "order_id": oid,
        "customer_id": customer_id,
        "order_timestamp": order_ts.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "channel": channel,
    }

    n_items = random.randint(1, 5)
    items = []
    chosen_products = random.sample(list(products.keys()), k=min(n_items, len(products)))
    for pid in chosen_products:
        qty = random.randint(1, 4)
        # inject a rare data quality bug: occasional bad product_id (orphaned FK)
        use_pid = pid if random.random() > 0.01 else 999999
        items.append({
            "order_item_id": str(uuid.uuid4())[:8],
            "order_id": oid,
            "product_id": use_pid,
            "quantity": qty,
            "unit_price": products[pid]["unit_price"],
        })

    payments = []
    if status != "cancelled":
        pay_delay_days = random.choices([0, 1, 2], weights=[85, 10, 5])[0]  # late-arriving payments
        pay_day = day + timedelta(days=pay_delay_days)
        payments.append({
            "payment_id": str(uuid.uuid4())[:8],
            "order_id": oid,
            "payment_method": random.choice(PAYMENT_METHODS),
            "amount": round(sum(i["quantity"] * i["unit_price"] for i in items), 2),
            "payment_status": "success" if random.random() > 0.04 else "failed",
            "payment_timestamp": pay_day.strftime("%Y-%m-%d %H:%M:%S"),
            "_landing_date": pay_day.strftime("%Y-%m-%d"),  # which day file this lands in
        })

    return order, items, payments


def write_csv(df, entity, day):
    if df is None or len(df) == 0:
        return
    folder = LANDING / entity / day.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    fname = folder / f"{entity}_{uuid.uuid4().hex[:6]}.csv"
    df.to_csv(fname, index=False)


def main():
    LANDING.mkdir(parents=True, exist_ok=True)
    print("Seeding product catalog...")
    products_df = seed_products()
    write_csv(products_df, "products", START_DATE)

    pending_payments_by_day = {}

    for d in range(N_DAYS):
        day = START_DATE + timedelta(days=d)
        print(f"Simulating day {day.date()}...")

        # customers
        new_custs = [new_customer(day) for _ in range(random.randint(*NEW_CUSTOMERS_PER_DAY))]
        updated = [maybe_update_customer(day) for _ in range(3)]
        cust_rows = [c for c in new_custs + updated if c]
        if cust_rows:
            df = pd.DataFrame(cust_rows)
            # occasionally duplicate a row, simulating upstream re-send
            if random.random() < 0.2 and len(df) > 1:
                df = pd.concat([df, df.sample(1)], ignore_index=True)
            write_csv(df, "customers", day)

        # orders / order_items / payments
        orders, all_items, all_payments = [], [], []
        for _ in range(random.randint(*NEW_ORDERS_PER_DAY)):
            order, items, payments = make_order(day)
            if order:
                orders.append(order)
                all_items.extend(items)
                for p in payments:
                    pending_payments_by_day.setdefault(p["_landing_date"], []).append(p)

        if orders:
            write_csv(pd.DataFrame(orders), "orders", day)
        if all_items:
            write_csv(pd.DataFrame(all_items), "order_items", day)

        # flush any payments scheduled to land today (including late arrivals from prior days)
        today_str = day.strftime("%Y-%m-%d")
        todays_payments = pending_payments_by_day.pop(today_str, [])
        if todays_payments:
            pay_df = pd.DataFrame(todays_payments).drop(columns=["_landing_date"])
            write_csv(pay_df, "payments", day)

    print("\nDone. Landing zone populated at data/landing/")
    print(f"Customers: {len(customers)} | Products: {len(products)} | Orders: {order_id_counter - 1}")


if __name__ == "__main__":
    main()
