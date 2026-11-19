"""
transform.py
------------
Cleaning / normalization layer. Takes the raw DataFrames from extract.py
and returns tidy, typed DataFrames ready to load into PostgreSQL.

This is where most of the "manual data collection/cleanup time" gets
eliminated: parsing inconsistent dates, stripping currency symbols,
de-duplicating, flagging bad rows instead of silently dropping them, etc.
"""

import logging
import re

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_CURRENCY_RE = re.compile(r"[^\d.\-]")


def _parse_currency(value) -> float:
    """Convert strings like '$1,299.00' or '1299' into a float."""
    if pd.isna(value):
        return np.nan
    cleaned = _CURRENCY_RE.sub("", str(value))
    return float(cleaned) if cleaned else np.nan


def clean_products(raw_products: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the product catalog:
      - standardize column names
      - coerce price to float
      - split out category
      - drop exact duplicate SKUs, keep the first
    """
    df = raw_products.copy()
    df = df.rename(columns={"id": "product_id", "title": "product_name"})

    df["price"] = df["price"].apply(_parse_currency)
    df["category"] = df["category"].astype(str).str.strip().str.title()
    df["product_name"] = df["product_name"].astype(str).str.strip()

    before = len(df)
    df = df.drop_duplicates(subset="product_id", keep="first")
    logger.info("clean_products: dropped %d duplicate product rows", before - len(df))

    df = df.dropna(subset=["product_id", "product_name", "price"])
    return df[["product_id", "product_name", "category", "price"]]


def clean_orders(raw_orders: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the raw orders export:
      - parse inconsistent date formats
      - strip currency symbols from unit_price
      - coerce quantity to int
      - compute total_amount
      - drop duplicate order_id rows
      - flag rows missing a customer_email rather than silently dropping them
    """
    df = raw_orders.copy()

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce", format="mixed")
    df["unit_price"] = df["unit_price"].apply(_parse_currency)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["total_amount"] = (df["unit_price"] * df["quantity"]).round(2)

    df["customer_email"] = df["customer_email"].str.strip().str.lower()
    df["missing_customer_info"] = df["customer_email"].isna() | (df["customer_email"] == "")

    df["status"] = df["status"].str.strip().str.lower()

    before = len(df)
    df = df.drop_duplicates(subset="order_id", keep="last")
    logger.info("clean_orders: dropped %d duplicate order rows", before - len(df))

    invalid_dates = df["order_date"].isna().sum()
    if invalid_dates:
        logger.warning("clean_orders: %d rows had unparseable order_date", invalid_dates)
    df = df.dropna(subset=["order_date", "order_id", "product_sku"])

    return df[
        [
            "order_id",
            "customer_email",
            "product_sku",
            "quantity",
            "unit_price",
            "total_amount",
            "order_date",
            "status",
            "missing_customer_info",
        ]
    ]


def build_customers(clean_order_df: pd.DataFrame) -> pd.DataFrame:
    """Derive a deduplicated customers dimension from cleaned order data."""
    customers = (
        clean_order_df.loc[~clean_order_df["missing_customer_info"], ["customer_email"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    customers["customer_id"] = customers.index + 1
    return customers[["customer_id", "customer_email"]]
