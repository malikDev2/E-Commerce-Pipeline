"""
extract.py
----------
Extraction layer: pulls raw, messy e-commerce data from two sources, the
same way a real pipeline would sit in front of a live store + platform
exports:

1. `fetch_products()`      -> scrapes a live product-catalog API (JSON)
2. `load_raw_orders()`     -> reads a raw orders/transactions export (CSV)
                               dumped by the storefront (Shopify/Amazon/
                               WooCommerce style export), which is typically
                               inconsistent: mixed date formats, currency
                               strings, duplicate rows, missing fields.

Both return pandas DataFrames "as-is" (uncleaned) so that all cleaning
logic lives in transform.py and stays testable/isolated.
"""

import logging
import time

import pandas as pd
import requests

from config import PIPELINE

logger = logging.getLogger(__name__)


def fetch_products(url: str = PIPELINE.products_api_url, retries: int = 3, timeout: int = 10) -> pd.DataFrame:
    """
    Scrape the live product catalog API.

    Retries on transient network failures (common when scraping external
    endpoints) and returns the raw JSON payload as a DataFrame.
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logger.info("Fetching product catalog from %s (attempt %d/%d)", url, attempt, retries)
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            df = pd.DataFrame(data)
            logger.info("Fetched %d raw product records", len(df))
            return df
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            logger.warning("Fetch attempt %d failed: %s", attempt, exc)
            time.sleep(1.5 * attempt)  # simple backoff
    raise RuntimeError(f"Failed to fetch products after {retries} attempts") from last_exc


def load_raw_orders(path: str = PIPELINE.raw_orders_csv) -> pd.DataFrame:
    """
    Load the raw orders export exactly as the platform produces it -
    no cleaning here. Expected (messy) columns:

        order_id, customer_email, product_sku, quantity,
        unit_price, order_date, status
    """
    logger.info("Loading raw orders export from %s", path)
    df = pd.read_csv(path, dtype=str)  # read everything as string; transform.py handles typing
    logger.info("Loaded %d raw order rows", len(df))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=PIPELINE.log_level)
    products = fetch_products()
    print(products.head())
    orders = load_raw_orders()
    print(orders.head())
