import os
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv


load_dotenv()


POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "crypto_market"),
    "user": os.getenv("POSTGRES_USER", "crypto_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "12345"),
}


COINGECKO_MARKETS_URL = os.getenv(
    "COINGECKO_MARKETS_URL",
    "https://api.coingecko.com/api/v3/coins/markets",
)

COINGECKO_VS_CURRENCY = os.getenv("COINGECKO_VS_CURRENCY", "usd")
COINGECKO_PER_PAGE = int(os.getenv("COINGECKO_PER_PAGE", "250"))
COINGECKO_MAX_PAGES = int(os.getenv("COINGECKO_MAX_PAGES", "8"))
COINGECKO_SLEEP_SECONDS = float(os.getenv("COINGECKO_SLEEP_SECONDS", "20"))
COINGECKO_START_PAGE = int(os.getenv("COINGECKO_START_PAGE", "1"))
COINGECKO_RATE_LIMIT_SLEEP_SECONDS = int(os.getenv("COINGECKO_RATE_LIMIT_SLEEP_SECONDS", "90"))

SOURCE_NAME = "coingecko"


def utc_now():
    return datetime.now(timezone.utc)


def get_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def ensure_schema(conn):
    ddl = """
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
    """

    with conn.cursor() as cur:
        cur.execute(ddl)

    conn.commit()


def parse_dt(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def fetch_page(session, page):
    params = {
        "vs_currency": COINGECKO_VS_CURRENCY,
        "order": "market_cap_desc",
        "per_page": COINGECKO_PER_PAGE,
        "page": page,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }

    for attempt in range(1, 8):
        response = session.get(
            COINGECKO_MARKETS_URL,
            params=params,
            timeout=40,
        )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            sleep_seconds = int(retry_after) if retry_after else COINGECKO_RATE_LIMIT_SLEEP_SECONDS

            print(
                f"CoinGecko rate limit on page={page}. "
                f"attempt={attempt}/7. Sleeping {sleep_seconds} seconds..."
            )

            time.sleep(sleep_seconds)
            continue

        if response.status_code >= 500:
            sleep_seconds = min(30 * attempt, 120)
            print(
                f"CoinGecko server error {response.status_code} on page={page}. "
                f"Sleeping {sleep_seconds} seconds..."
            )
            time.sleep(sleep_seconds)
            continue

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            raise ValueError("Unexpected CoinGecko response")

        return data

    raise RuntimeError(f"CoinGecko page={page} failed after retries")


def upsert_page(conn, coins):
    if not coins:
        return 0

    fetched_at = utc_now()
    rows = []

    for item in coins:
        symbol = item.get("symbol")

        rows.append(
            (
                SOURCE_NAME,
                item.get("id"),
                symbol,
                symbol.upper() if symbol else None,
                item.get("name"),
                item.get("image"),

                item.get("current_price"),
                item.get("market_cap"),
                item.get("market_cap_rank"),
                item.get("fully_diluted_valuation"),
                item.get("total_volume"),

                item.get("high_24h"),
                item.get("low_24h"),
                item.get("price_change_24h"),
                item.get("price_change_percentage_24h"),

                item.get("circulating_supply"),
                item.get("total_supply"),
                item.get("max_supply"),

                item.get("ath"),
                item.get("ath_change_percentage"),
                parse_dt(item.get("ath_date")),

                item.get("atl"),
                item.get("atl_change_percentage"),
                parse_dt(item.get("atl_date")),

                parse_dt(item.get("last_updated")),
                fetched_at,
                fetched_at,
            )
        )

    sql = """
        INSERT INTO coin_market_meta_latest (
            source,
            coingecko_id,
            symbol,
            symbol_upper,
            name,
            image_url,

            current_price,
            market_cap,
            market_cap_rank,
            fully_diluted_valuation,
            total_volume,

            high_24h,
            low_24h,
            price_change_24h,
            price_change_percentage_24h,

            circulating_supply,
            total_supply,
            max_supply,

            ath,
            ath_change_percentage,
            ath_date,

            atl,
            atl_change_percentage,
            atl_date,

            coingecko_last_updated,
            fetched_at,
            updated_at
        )
        VALUES %s
        ON CONFLICT (source, coingecko_id)
        DO UPDATE SET
            symbol = EXCLUDED.symbol,
            symbol_upper = EXCLUDED.symbol_upper,
            name = EXCLUDED.name,
            image_url = EXCLUDED.image_url,

            current_price = EXCLUDED.current_price,
            market_cap = EXCLUDED.market_cap,
            market_cap_rank = EXCLUDED.market_cap_rank,
            fully_diluted_valuation = EXCLUDED.fully_diluted_valuation,
            total_volume = EXCLUDED.total_volume,

            high_24h = EXCLUDED.high_24h,
            low_24h = EXCLUDED.low_24h,
            price_change_24h = EXCLUDED.price_change_24h,
            price_change_percentage_24h = EXCLUDED.price_change_percentage_24h,

            circulating_supply = EXCLUDED.circulating_supply,
            total_supply = EXCLUDED.total_supply,
            max_supply = EXCLUDED.max_supply,

            ath = EXCLUDED.ath,
            ath_change_percentage = EXCLUDED.ath_change_percentage,
            ath_date = EXCLUDED.ath_date,

            atl = EXCLUDED.atl,
            atl_change_percentage = EXCLUDED.atl_change_percentage,
            atl_date = EXCLUDED.atl_date,

            coingecko_last_updated = EXCLUDED.coingecko_last_updated,
            fetched_at = EXCLUDED.fetched_at,
            updated_at = NOW();
    """

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=500)

    conn.commit()
    return len(rows)


def run_sync():
    conn = get_connection()
    session = requests.Session()

    try:
        ensure_schema(conn)

        total = 0
        page = COINGECKO_START_PAGE

        print("Starting CoinGecko market metadata sync")
        print(f"per_page={COINGECKO_PER_PAGE}, max_pages={COINGECKO_MAX_PAGES}, start_page={COINGECKO_START_PAGE}")

        while True:
            if COINGECKO_MAX_PAGES > 0 and page > COINGECKO_MAX_PAGES:
                break

            coins = fetch_page(session, page)

            if not coins:
                break

            saved = upsert_page(conn, coins)
            total += saved

            print(f"page={page} | saved={saved} | total={total}")

            page += 1
            time.sleep(COINGECKO_SLEEP_SECONDS)

        print("CoinGecko metadata sync finished")
        print(f"Total saved/updated: {total}")

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    run_sync()
