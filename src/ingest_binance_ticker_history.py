import os
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv


load_dotenv()


POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "192.168.1.10"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "crypto_market"),
    "user": os.getenv("POSTGRES_USER", "crypto_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "12345"),
}


BINANCE_REST_URL = os.getenv(
    "BINANCE_REST_URL",
    "https://api.binance.com/api/v3/ticker/24hr",
)

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "30"))

QUOTE_ASSETS = [
    item.strip().upper()
    for item in os.getenv("QUOTE_ASSETS", "").split(",")
    if item.strip()
]

SOURCE_NAME = "binance"


def utc_now():
    return datetime.now(timezone.utc)


def ms_to_datetime(ms):
    if ms is None:
        return None

    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)


def get_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def ensure_schema(conn):
    ddl = """
    CREATE TABLE IF NOT EXISTS ingestion_logs (
        id BIGSERIAL PRIMARY KEY,
        pipeline_name VARCHAR(100) NOT NULL,
        source VARCHAR(50) NOT NULL,
        status VARCHAR(30) NOT NULL,
        message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS market_ticker_history (
        id BIGSERIAL PRIMARY KEY,

        source VARCHAR(50) NOT NULL,
        symbol VARCHAR(30) NOT NULL,

        open_price NUMERIC(24, 10),
        high_price NUMERIC(24, 10),
        low_price NUMERIC(24, 10),
        last_price NUMERIC(24, 10),

        volume NUMERIC(30, 10),
        quote_volume NUMERIC(30, 10),

        open_time TIMESTAMPTZ,
        close_time TIMESTAMPTZ,

        first_trade_id BIGINT,
        last_trade_id BIGINT,
        trade_count BIGINT,

        fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_market_ticker_history_symbol_time
        ON market_ticker_history(symbol, fetched_at DESC);

    CREATE INDEX IF NOT EXISTS idx_market_ticker_history_fetched_at
        ON market_ticker_history(fetched_at DESC);

    CREATE TABLE IF NOT EXISTS market_ticker_latest (
        source VARCHAR(50) NOT NULL,
        symbol VARCHAR(30) NOT NULL,

        open_price NUMERIC(24, 10),
        high_price NUMERIC(24, 10),
        low_price NUMERIC(24, 10),
        last_price NUMERIC(24, 10),

        volume NUMERIC(30, 10),
        quote_volume NUMERIC(30, 10),

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
    """

    with conn.cursor() as cur:
        cur.execute(ddl)

    conn.commit()


def log_ingestion(conn, status, message):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion_logs (
                pipeline_name,
                source,
                status,
                message
            )
            VALUES (%s, %s, %s, %s);
            """,
            (
                "binance_ticker_interval_ingestion",
                SOURCE_NAME,
                status,
                message,
            ),
        )


def should_keep_symbol(symbol):
    if not QUOTE_ASSETS:
        return True

    symbol = symbol.upper()
    return any(symbol.endswith(quote_asset) for quote_asset in QUOTE_ASSETS)


def request_tickers(session):
    response = session.get(
        BINANCE_REST_URL,
        params={"type": "MINI"},
        timeout=30,
    )

    if response.status_code in (418, 429):
        retry_after = response.headers.get("Retry-After")
        sleep_seconds = int(retry_after) if retry_after else 60
        raise RuntimeError(f"Rate limited by Binance. Retry after {sleep_seconds} seconds.")

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError("Expected list response from Binance ticker endpoint")

    return data


def build_rows(tickers, fetched_at):
    rows = []

    for item in tickers:
        symbol = item.get("symbol")

        if not symbol:
            continue

        if not should_keep_symbol(symbol):
            continue

        rows.append(
            (
                SOURCE_NAME,
                symbol,
                item.get("openPrice"),
                item.get("highPrice"),
                item.get("lowPrice"),
                item.get("lastPrice"),
                item.get("volume"),
                item.get("quoteVolume"),
                ms_to_datetime(item.get("openTime")),
                ms_to_datetime(item.get("closeTime")),
                item.get("firstId"),
                item.get("lastId"),
                item.get("count"),
                fetched_at,
            )
        )

    return rows


def insert_history(conn, rows):
    if not rows:
        return 0

    sql = """
        INSERT INTO market_ticker_history (
            source,
            symbol,
            open_price,
            high_price,
            low_price,
            last_price,
            volume,
            quote_volume,
            open_time,
            close_time,
            first_trade_id,
            last_trade_id,
            trade_count,
            fetched_at
        )
        VALUES %s;
    """

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            sql,
            rows,
            page_size=1000,
        )

    return len(rows)


def upsert_latest(conn, rows):
    if not rows:
        return 0

    sql = """
        INSERT INTO market_ticker_latest (
            source,
            symbol,
            open_price,
            high_price,
            low_price,
            last_price,
            volume,
            quote_volume,
            open_time,
            close_time,
            first_trade_id,
            last_trade_id,
            trade_count,
            fetched_at,
            updated_at
        )
        VALUES %s
        ON CONFLICT (source, symbol)
        DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            last_price = EXCLUDED.last_price,
            volume = EXCLUDED.volume,
            quote_volume = EXCLUDED.quote_volume,
            open_time = EXCLUDED.open_time,
            close_time = EXCLUDED.close_time,
            first_trade_id = EXCLUDED.first_trade_id,
            last_trade_id = EXCLUDED.last_trade_id,
            trade_count = EXCLUDED.trade_count,
            fetched_at = EXCLUDED.fetched_at,
            updated_at = NOW();
    """

    latest_rows = [
        row + (utc_now(),)
        for row in rows
    ]

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            sql,
            latest_rows,
            page_size=1000,
        )

    return len(latest_rows)


def run_loop():
    print("Starting Binance interval ticker ingestion")
    print(f"Polling every {POLL_SECONDS} seconds")
    print(f"Quote asset filter: {QUOTE_ASSETS if QUOTE_ASSETS else 'ALL'}")
    print("Mode: APPEND history + UPSERT latest")

    conn = get_connection()
    session = requests.Session()

    try:
        ensure_schema(conn)

        log_ingestion(
            conn,
            "STARTED",
            f"poll_seconds={POLL_SECONDS}, quote_assets={QUOTE_ASSETS if QUOTE_ASSETS else 'ALL'}",
        )
        conn.commit()

        while True:
            started_at = time.time()
            fetched_at = utc_now()

            try:
                tickers = request_tickers(session)
                rows = build_rows(tickers, fetched_at)

                history_count = insert_history(conn, rows)
                latest_count = upsert_latest(conn, rows)

                conn.commit()

                elapsed = time.time() - started_at

                print(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"history_rows={history_count} | "
                    f"latest_rows={latest_count} | "
                    f"elapsed={elapsed:.2f}s"
                )

            except Exception as error:
                conn.rollback()

                try:
                    log_ingestion(conn, "ERROR", str(error))
                    conn.commit()
                except Exception:
                    conn.rollback()

                print(f"ERROR: {error}")

            elapsed = time.time() - started_at
            sleep_time = max(POLL_SECONDS - elapsed, 1)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("Stopped by user.")

        try:
            log_ingestion(conn, "STOPPED", "Stopped by user")
            conn.commit()
        except Exception:
            conn.rollback()

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    run_loop()
