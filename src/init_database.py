import os
import time

import psycopg2
from dotenv import load_dotenv


load_dotenv()


POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "crypto_market"),
    "user": os.getenv("POSTGRES_USER", "crypto_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "12345"),
}


DDL = """
CREATE TABLE IF NOT EXISTS market_symbols (
    source VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    status VARCHAR(50),
    base_asset VARCHAR(50),
    quote_asset VARCHAR(50),
    base_asset_precision INTEGER,
    quote_asset_precision INTEGER,
    quote_precision INTEGER,
    order_types JSONB,
    iceberg_allowed BOOLEAN,
    oco_allowed BOOLEAN,
    oto_allowed BOOLEAN,
    quote_order_qty_market_allowed BOOLEAN,
    allow_trailing_stop BOOLEAN,
    cancel_replace_allowed BOOLEAN,
    is_spot_trading_allowed BOOLEAN,
    is_margin_trading_allowed BOOLEAN,
    permissions JSONB,
    filters JSONB,
    onboard_date BIGINT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source, symbol)
);

CREATE INDEX IF NOT EXISTS idx_market_symbols_quote_asset
    ON market_symbols(quote_asset);

CREATE TABLE IF NOT EXISTS market_ticker_history (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    price_change NUMERIC,
    price_change_percent NUMERIC,
    price_change_percentage NUMERIC,
    weighted_avg_price NUMERIC,
    prev_close_price NUMERIC,
    last_price NUMERIC,
    last_qty NUMERIC,
    bid_price NUMERIC,
    bid_qty NUMERIC,
    ask_price NUMERIC,
    ask_qty NUMERIC,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    volume NUMERIC,
    quote_volume NUMERIC,
    open_time TIMESTAMPTZ,
    close_time TIMESTAMPTZ,
    first_trade_id BIGINT,
    last_trade_id BIGINT,
    trade_count BIGINT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_ticker_history_symbol_time
    ON market_ticker_history(symbol, fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_market_ticker_history_fetched_at
    ON market_ticker_history(fetched_at DESC);

CREATE TABLE IF NOT EXISTS market_ticker_latest (
    source VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    price_change NUMERIC,
    price_change_percent NUMERIC,
    price_change_percentage NUMERIC,
    weighted_avg_price NUMERIC,
    prev_close_price NUMERIC,
    last_price NUMERIC,
    last_qty NUMERIC,
    bid_price NUMERIC,
    bid_qty NUMERIC,
    ask_price NUMERIC,
    ask_qty NUMERIC,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    volume NUMERIC,
    quote_volume NUMERIC,
    open_time TIMESTAMPTZ,
    close_time TIMESTAMPTZ,
    first_trade_id BIGINT,
    last_trade_id BIGINT,
    trade_count BIGINT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source, symbol)
);

CREATE INDEX IF NOT EXISTS idx_market_ticker_latest_quote_volume
    ON market_ticker_latest(quote_volume DESC);

CREATE TABLE IF NOT EXISTS daily_klines (
    source VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    interval_name VARCHAR(20) NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume NUMERIC,
    quote_volume NUMERIC,
    trade_count BIGINT,
    number_of_trades BIGINT,
    taker_buy_base_volume NUMERIC,
    taker_buy_quote_volume NUMERIC,
    ignore_value NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source, symbol, interval_name, open_time)
);

CREATE INDEX IF NOT EXISTS idx_daily_klines_symbol_time
    ON daily_klines(symbol, open_time DESC);

CREATE TABLE IF NOT EXISTS coin_market_meta_latest (
    source VARCHAR(50) NOT NULL,
    coingecko_id VARCHAR(120) NOT NULL,
    symbol VARCHAR(40),
    symbol_upper VARCHAR(40),
    name VARCHAR(200),
    image_url TEXT,
    current_price NUMERIC,
    market_cap NUMERIC,
    market_cap_rank INTEGER,
    fully_diluted_valuation NUMERIC,
    total_volume NUMERIC,
    high_24h NUMERIC,
    low_24h NUMERIC,
    price_change_24h NUMERIC,
    price_change_percentage_24h NUMERIC,
    circulating_supply NUMERIC,
    total_supply NUMERIC,
    max_supply NUMERIC,
    ath NUMERIC,
    ath_change_percentage NUMERIC,
    ath_date TIMESTAMPTZ,
    atl NUMERIC,
    atl_change_percentage NUMERIC,
    atl_date TIMESTAMPTZ,
    coingecko_last_updated TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source, coingecko_id)
);

CREATE INDEX IF NOT EXISTS idx_coin_market_meta_symbol_upper
    ON coin_market_meta_latest(symbol_upper);

CREATE INDEX IF NOT EXISTS idx_coin_market_meta_market_cap_rank
    ON coin_market_meta_latest(market_cap_rank);

CREATE TABLE IF NOT EXISTS ingestion_logs (
    id BIGSERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100),
    source VARCHAR(50),
    status VARCHAR(50),
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    scope_quote_asset VARCHAR(30),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('up', 'down')),
    threshold_percent NUMERIC NOT NULL CHECK (threshold_percent > 0),
    comparison_mode VARCHAR(30) NOT NULL CHECK (comparison_mode IN ('rolling_window', 'fixed_date_range')),
    window_minutes INTEGER,
    baseline_start_date DATE,
    baseline_end_date DATE,
    baseline_price_type VARCHAR(30) NOT NULL DEFAULT 'avg_close',
    cooldown_minutes INTEGER NOT NULL DEFAULT 60,
    include_new_symbols BOOLEAN NOT NULL DEFAULT TRUE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at TIMESTAMPTZ,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_recipients (
    id BIGSERIAL PRIMARY KEY,
    rule_id BIGINT NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    email VARCHAR(320) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_events (
    id BIGSERIAL PRIMARY KEY,
    rule_id BIGINT REFERENCES alert_rules(id) ON DELETE SET NULL,
    rule_name VARCHAR(200),
    symbol VARCHAR(30) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    threshold_percent NUMERIC NOT NULL,
    actual_percent NUMERIC NOT NULL,
    baseline_price NUMERIC,
    latest_price NUMERIC,
    baseline_time TIMESTAMPTZ,
    latest_time TIMESTAMPTZ,
    comparison_mode VARCHAR(30),
    baseline_price_type VARCHAR(30),
    window_minutes INTEGER,
    baseline_start_date DATE,
    baseline_end_date DATE,
    email_status VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_email_logs (
    id BIGSERIAL PRIMARY KEY,
    rule_id BIGINT REFERENCES alert_rules(id) ON DELETE SET NULL,
    recipient_email VARCHAR(320) NOT NULL,
    status VARCHAR(80) NOT NULL,
    matched_count INTEGER NOT NULL DEFAULT 0,
    new_symbol_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_new_symbol_notifications (
    rule_id BIGINT NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    symbol VARCHAR(30) NOT NULL,
    notified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (rule_id, symbol)
);
"""


def connect_with_retry(max_attempts=30):
    for attempt in range(1, max_attempts + 1):
        try:
            return psycopg2.connect(**POSTGRES_CONFIG)
        except Exception as exc:
            print(f"Database not ready, attempt {attempt}/{max_attempts}: {exc}")
            time.sleep(2)

    raise RuntimeError("Could not connect to PostgreSQL")


def main():
    print("Starting database bootstrap")
    conn = connect_with_retry()

    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

        conn.commit()
        print("Database bootstrap finished successfully")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
