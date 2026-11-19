"""
load.py
-------
Load layer: writes cleaned DataFrames into the centralized PostgreSQL
database defined in schema.sql, using idempotent upserts so the pipeline
can be re-run safely (e.g. on a daily schedule) without creating dupes.
"""

import logging

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import DB

logger = logging.getLogger(__name__)


def get_engine() -> Engine:
    return create_engine(DB.sqlalchemy_url, pool_pre_ping=True)


def _upsert(engine: Engine, df: pd.DataFrame, table: str, pk: str, update_cols: list[str]) -> None:
    """
    Generic upsert helper: stage rows into a temp table, then
    INSERT ... ON CONFLICT (pk) DO UPDATE against the target table.
    """
    if df.empty:
        logger.info("Skipping load for %s: no rows to write", table)
        return

    staging_table = f"staging_{table}"
    with engine.begin() as conn:
        df.to_sql(staging_table, conn, if_exists="replace", index=False)

        set_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)
        cols = ", ".join(df.columns)
        sql = text(
            f"""
            INSERT INTO {table} ({cols})
            SELECT {cols} FROM {staging_table}
            ON CONFLICT ({pk}) DO UPDATE SET {set_clause};
            """
        )
        conn.execute(sql)
        conn.execute(text(f"DROP TABLE {staging_table};"))
    logger.info("Upserted %d rows into %s", len(df), table)


def load_products(engine: Engine, products: pd.DataFrame) -> None:
    _upsert(engine, products, "products", "product_id", ["product_name", "category", "price"])


def load_customers(engine: Engine, customers: pd.DataFrame) -> None:
    _upsert(engine, customers, "customers", "customer_id", ["customer_email"])


def load_orders(engine: Engine, orders: pd.DataFrame) -> None:
    cols = [
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
    _upsert(engine, orders[cols], "orders", "order_id",
            ["customer_email", "product_sku", "quantity", "unit_price",
             "total_amount", "order_date", "status", "missing_customer_info"])
