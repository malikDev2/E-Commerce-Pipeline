"""
config.py
---------
Centralized configuration for the e-commerce pipeline.

All values are read from environment variables so credentials are never
hard-coded. Copy `.env.example` to `.env` and fill in real values, or export
these vars in your shell / CI system before running the pipeline.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DBConfig:
    host: str = os.getenv("ECOM_DB_HOST", "localhost")
    port: int = int(os.getenv("ECOM_DB_PORT", "5432"))
    name: str = os.getenv("ECOM_DB_NAME", "ecommerce")
    user: str = os.getenv("ECOM_DB_USER", "postgres")
    password: str = os.getenv("ECOM_DB_PASSWORD", "")

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass(frozen=True)
class PipelineConfig:
    # Public demo product API used to simulate "scraping" a live storefront catalog
    products_api_url: str = os.getenv(
        "ECOM_PRODUCTS_API_URL", "https://fakestoreapi.com/products"
    )
    # Raw, messy export dropped by the e-commerce platform (Shopify/Amazon/etc.)
    raw_orders_csv: str = os.getenv(
        "ECOM_RAW_ORDERS_CSV", "sample_data/raw_orders_export.csv"
    )
    log_level: str = os.getenv("ECOM_LOG_LEVEL", "INFO")


DB = DBConfig()
PIPELINE = PipelineConfig()
