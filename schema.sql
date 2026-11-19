-- ============================================================================
-- schema.sql
-- Centralized e-commerce database schema (PostgreSQL)
--
-- Feeds:
--   - Power BI / Tableau  -> query the vw_* views directly (or via a
--     scheduled extract) for real-time dashboards
--   - Excel               -> vw_sales_summary / vw_monthly_revenue are
--     designed to be pulled straight into Power Query / dynamic models
-- ============================================================================

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT        NOT NULL,
    category     TEXT,
    price        NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id    SERIAL PRIMARY KEY,
    customer_email TEXT UNIQUE NOT NULL,
    created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
    order_id              TEXT PRIMARY KEY,
    customer_email        TEXT REFERENCES customers(customer_email),
    product_sku           TEXT NOT NULL,
    quantity              INTEGER NOT NULL CHECK (quantity >= 0),
    unit_price            NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    total_amount          NUMERIC(12, 2) NOT NULL,
    order_date            TIMESTAMPTZ NOT NULL,
    status                TEXT,
    missing_customer_info BOOLEAN DEFAULT FALSE,
    loaded_at             TIMESTAMPTZ DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- Indexes to keep dashboard queries fast as order volume grows
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_orders_order_date     ON orders (order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_email ON orders (customer_email);
CREATE INDEX IF NOT EXISTS idx_orders_product_sku    ON orders (product_sku);
CREATE INDEX IF NOT EXISTS idx_orders_status         ON orders (status);

-- ----------------------------------------------------------------------------
-- BI / Excel-facing views
-- ----------------------------------------------------------------------------

-- One row per order line, joined with product + customer context.
-- This is the main feed for Power BI / Tableau dashboards.
CREATE OR REPLACE VIEW vw_sales_summary AS
SELECT
    o.order_id,
    o.order_date,
    o.customer_email,
    o.product_sku,
    p.product_name,
    p.category,
    o.quantity,
    o.unit_price,
    o.total_amount,
    o.status
FROM orders o
LEFT JOIN products p
    ON o.product_sku::text = p.product_id::text;

-- Monthly revenue rollup by category - well suited to a dynamic Excel model
-- (pivot-friendly: one row per month/category).
CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT
    date_trunc('month', o.order_date)::date AS month,
    p.category,
    COUNT(DISTINCT o.order_id)              AS order_count,
    SUM(o.total_amount)                     AS revenue
FROM orders o
LEFT JOIN products p
    ON o.product_sku::text = p.product_id::text
WHERE o.status <> 'cancelled'
GROUP BY 1, 2
ORDER BY 1, 2;

-- Top customers by lifetime spend
CREATE OR REPLACE VIEW vw_customer_ltv AS
SELECT
    c.customer_email,
    COUNT(o.order_id)      AS total_orders,
    SUM(o.total_amount)    AS lifetime_value,
    MIN(o.order_date)      AS first_order_date,
    MAX(o.order_date)      AS last_order_date
FROM customers c
JOIN orders o ON o.customer_email = c.customer_email
WHERE o.status <> 'cancelled'
GROUP BY c.customer_email
ORDER BY lifetime_value DESC;

-- Data-quality flag view: surfaces rows that need manual review instead of
-- silently losing them, e.g. for a "needs attention" tab in Excel/BI.
CREATE OR REPLACE VIEW vw_orders_needing_review AS
SELECT *
FROM orders
WHERE missing_customer_info = TRUE
   OR total_amount <= 0;
