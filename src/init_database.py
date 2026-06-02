import os
import time

import psycopg2
from dotenv import load_dotenv

from src.ingest_binance_ticker_history import ensure_schema as ensure_ticker_schema
from src.sync_daily_klines_full import ensure_schema as ensure_daily_schema
from src.sync_coingecko_market_meta import ensure_schema as ensure_coingecko_schema
from src.check_alerts import ensure_schema as ensure_alert_schema


load_dotenv()


POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "crypto_market"),
    "user": os.getenv("POSTGRES_USER", "crypto_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "12345"),
}


def connect_with_retry(max_attempts=30, sleep_seconds=2):
    for attempt in range(1, max_attempts + 1):
        try:
            return psycopg2.connect(**POSTGRES_CONFIG)
        except Exception as exc:
            print(f"Database not ready, attempt {attempt}/{max_attempts}: {exc}")
            time.sleep(sleep_seconds)

    raise RuntimeError("Could not connect to PostgreSQL")


def main():
    print("Starting database bootstrap")

    conn = connect_with_retry()

    try:
        print("Ensuring daily/history schema...")
        ensure_daily_schema(conn)

        print("Ensuring realtime ticker schema...")
        ensure_ticker_schema(conn)

        print("Ensuring CoinGecko metadata schema...")
        ensure_coingecko_schema(conn)

        print("Ensuring alert schema...")
        ensure_alert_schema(conn)

        print("Database bootstrap finished successfully")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
