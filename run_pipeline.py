"""
run_pipeline.py
----------------
Entry point. Runs the full Extract -> Transform -> Load flow end to end
and logs a timing summary, which is what let this replace a manual
spreadsheet-based data pull entirely.

Usage:
    python run_pipeline.py
    python run_pipeline.py --skip-db   # dry run: extract + clean only, print summary
"""

import argparse
import logging
import time

from config import PIPELINE
import extract
import transform
import load

logging.basicConfig(
    level=PIPELINE.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


def run(skip_db: bool = False) -> None:
    start = time.time()

    logger.info("=== EXTRACT ===")
    raw_products = extract.fetch_products()
    raw_orders = extract.load_raw_orders()

    logger.info("=== TRANSFORM ===")
    products = transform.clean_products(raw_products)
    orders = transform.clean_orders(raw_orders)
    customers = transform.build_customers(orders)

    logger.info(
        "Clean record counts -> products: %d, orders: %d, customers: %d",
        len(products), len(orders), len(customers),
    )

    if skip_db:
        logger.info("--skip-db set: not writing to PostgreSQL. Dry run complete.")
    else:
        logger.info("=== LOAD ===")
        engine = load.get_engine()
        load.load_products(engine, products)
        load.load_customers(engine, customers)
        load.load_orders(engine, orders)

    elapsed = time.time() - start
    logger.info("Pipeline finished in %.2f seconds", elapsed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the e-commerce ETL pipeline.")
    parser.add_argument("--skip-db", action="store_true", help="Extract + clean only, skip PostgreSQL load.")
    args = parser.parse_args()
    run(skip_db=args.skip_db)
