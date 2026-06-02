import os
import time
from datetime import datetime, timedelta, timezone

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


BINANCE_EXCHANGE_INFO_URL = os.getenv(
    "BINANCE_EXCHANGE_INFO_URL",
    "https://api.binance.com/api/v3/exchangeInfo",
)

BINANCE_KLINES_URL = os.getenv(
    "BINANCE_KLINES_URL",
    "https://api.binance.com/api/v3/klines",
)

BACKFILL_INTERVAL = os.getenv("BACKFILL_INTERVAL", "1d")
BACKFILL_LIMIT = min(int(os.getenv("BACKFILL_LIMIT", "1000")), 1000)

BACKFILL_SLEEP_SECONDS = float(os.getenv("BACKFILL_SLEEP_SECONDS", "0.25"))
BACKFILL_ERROR_SLEEP_SECONDS = float(os.getenv("BACKFILL_ERROR_SLEEP_SECONDS", "5"))

BACKFILL_MAX_SYMBOLS = int(os.getenv("BACKFILL_MAX_SYMBOLS", "20"))
EXCLUDE_CURRENT_DAY = os.getenv("EXCLUDE_CURRENT_DAY", "true").lower() == "true"
REPAIR_GAPS = os.getenv("REPAIR_GAPS", "true").lower() == "true"

BACKFILL_QUOTE_ASSETS = [
    item.strip().upper()
    for item in os.getenv("BACKFILL_QUOTE_ASSETS", "").split(",")
    if item.strip()
]

SOURCE_NAME = "binance"
ONE_DAY_MS = 24 * 60 * 60 * 1000


def utc_now():
    return datetime.now(timezone.utc)


def today_utc_start():
    now = utc_now()
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def dt_to_ms(value):
    return int(value.timestamp() * 1000)


def ms_to_datetime(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)


def get_target_last_day_start():
    if EXCLUDE_CURRENT_DAY:
        return today_utc_start() - timedelta(days=1)

    return today_utc_start()


def get_target_end_ms():
    target_last_day = get_target_last_day_start()
    return dt_to_ms(target_last_day + timedelta(days=1)) - 1


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

    CREATE TABLE IF NOT EXISTS market_symbols (
        source VARCHAR(50) NOT NULL,
        symbol VARCHAR(30) NOT NULL,
        base_asset VARCHAR(30),
        quote_asset VARCHAR(30),
        status VARCHAR(30),
        is_spot_trading_allowed BOOLEAN,
        first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE UNIQUE INDEX IF NOT EXISTS ux_market_symbols_source_symbol
        ON market_symbols(source, symbol);

    CREATE INDEX IF NOT EXISTS idx_market_symbols_quote_asset
        ON market_symbols(quote_asset);

    CREATE TABLE IF NOT EXISTS daily_klines (
        id BIGSERIAL PRIMARY KEY,

        source VARCHAR(50) NOT NULL,
        symbol VARCHAR(30) NOT NULL,
        interval_name VARCHAR(10) NOT NULL,

        open_time TIMESTAMPTZ NOT NULL,
        close_time TIMESTAMPTZ NOT NULL,

        open_price NUMERIC(24, 10),
        high_price NUMERIC(24, 10),
        low_price NUMERIC(24, 10),
        close_price NUMERIC(24, 10),

        volume NUMERIC(30, 10),
        quote_volume NUMERIC(30, 10),
        trade_count BIGINT,

        taker_buy_base_volume NUMERIC(30, 10),
        taker_buy_quote_volume NUMERIC(30, 10),

        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    ALTER TABLE daily_klines
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

    CREATE UNIQUE INDEX IF NOT EXISTS ux_daily_klines_key
        ON daily_klines(source, symbol, interval_name, open_time);

    CREATE INDEX IF NOT EXISTS idx_daily_klines_symbol_open_time
        ON daily_klines(symbol, open_time DESC);

    CREATE INDEX IF NOT EXISTS idx_daily_klines_open_time
        ON daily_klines(open_time DESC);
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
                "binance_daily_klines_full_sync",
                SOURCE_NAME,
                status,
                message,
            ),
        )


def request_json(session, url, params=None, retries=5):
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, params=params, timeout=30)

            if response.status_code in (418, 429):
                retry_after = response.headers.get("Retry-After")
                sleep_seconds = int(retry_after) if retry_after else 60

                print(
                    f"Rate limit response {response.status_code}. "
                    f"Sleeping {sleep_seconds} seconds..."
                )

                time.sleep(sleep_seconds)
                continue

            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            last_error = error
            sleep_seconds = min(5 * attempt, 30)

            print(
                f"Request error attempt={attempt}/{retries}: {error}. "
                f"Sleeping {sleep_seconds} seconds..."
            )

            time.sleep(sleep_seconds)

    raise last_error


def should_keep_quote_asset(quote_asset):
    if not BACKFILL_QUOTE_ASSETS:
        return True

    return quote_asset.upper() in BACKFILL_QUOTE_ASSETS


def fetch_exchange_symbols(session):
    data = request_json(session, BINANCE_EXCHANGE_INFO_URL)
    raw_symbols = data.get("symbols", [])

    symbols = []

    for item in raw_symbols:
        symbol = item.get("symbol")
        status = item.get("status")
        base_asset = item.get("baseAsset")
        quote_asset = item.get("quoteAsset")
        is_spot_allowed = item.get("isSpotTradingAllowed")

        if not symbol:
            continue

        if status != "TRADING":
            continue

        if is_spot_allowed is False:
            continue

        if quote_asset and not should_keep_quote_asset(quote_asset):
            continue

        symbols.append(
            {
                "symbol": symbol,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "status": status,
                "is_spot_trading_allowed": is_spot_allowed,
            }
        )

    symbols.sort(key=lambda x: x["symbol"])

    if BACKFILL_MAX_SYMBOLS > 0:
        symbols = symbols[:BACKFILL_MAX_SYMBOLS]

    return symbols


def upsert_market_symbols(conn, symbols):
    if not symbols:
        return 0

    rows = [
        (
            SOURCE_NAME,
            item["symbol"],
            item["base_asset"],
            item["quote_asset"],
            item["status"],
            item["is_spot_trading_allowed"],
        )
        for item in symbols
    ]

    sql = """
        INSERT INTO market_symbols (
            source,
            symbol,
            base_asset,
            quote_asset,
            status,
            is_spot_trading_allowed
        )
        VALUES %s
        ON CONFLICT (source, symbol)
        DO UPDATE SET
            base_asset = EXCLUDED.base_asset,
            quote_asset = EXCLUDED.quote_asset,
            status = EXCLUDED.status,
            is_spot_trading_allowed = EXCLUDED.is_spot_trading_allowed,
            updated_at = NOW();
    """

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=1000)

    return len(rows)


def get_symbol_max_open_time(conn, symbol):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT MAX(open_time)
            FROM daily_klines
            WHERE source = %s
              AND symbol = %s
              AND interval_name = %s;
            """,
            (SOURCE_NAME, symbol, BACKFILL_INTERVAL),
        )

        return cur.fetchone()[0]


def get_symbol_min_open_time(conn, symbol):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT MIN(open_time)
            FROM daily_klines
            WHERE source = %s
              AND symbol = %s
              AND interval_name = %s;
            """,
            (SOURCE_NAME, symbol, BACKFILL_INTERVAL),
        )

        return cur.fetchone()[0]


def fetch_klines(session, symbol, start_ms, end_ms):
    return request_json(
        session,
        BINANCE_KLINES_URL,
        params={
            "symbol": symbol,
            "interval": BACKFILL_INTERVAL,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": BACKFILL_LIMIT,
        },
    )


def insert_klines(conn, symbol, klines):
    if not klines:
        return 0

    current_day_start = today_utc_start()
    rows = []

    for item in klines:
        open_time = ms_to_datetime(item[0])
        close_time = ms_to_datetime(item[6])

        if EXCLUDE_CURRENT_DAY and open_time >= current_day_start:
            continue

        rows.append(
            (
                SOURCE_NAME,
                symbol,
                BACKFILL_INTERVAL,
                open_time,
                close_time,
                item[1],
                item[2],
                item[3],
                item[4],
                item[5],
                item[7],
                item[8],
                item[9],
                item[10],
            )
        )

    if not rows:
        return 0

    sql = """
        INSERT INTO daily_klines (
            source,
            symbol,
            interval_name,
            open_time,
            close_time,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            quote_volume,
            trade_count,
            taker_buy_base_volume,
            taker_buy_quote_volume
        )
        VALUES %s
        ON CONFLICT (source, symbol, interval_name, open_time)
        DO UPDATE SET
            close_time = EXCLUDED.close_time,
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            quote_volume = EXCLUDED.quote_volume,
            trade_count = EXCLUDED.trade_count,
            taker_buy_base_volume = EXCLUDED.taker_buy_base_volume,
            taker_buy_quote_volume = EXCLUDED.taker_buy_quote_volume,
            updated_at = NOW();
    """

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=1000)

    return len(rows)


def sync_range(conn, session, symbol, start_ms, end_ms):
    total_saved = 0
    request_count = 0
    current_start = start_ms

    while current_start <= end_ms:
        klines = fetch_klines(session, symbol, current_start, end_ms)
        request_count += 1

        if not klines:
            break

        saved = insert_klines(conn, symbol, klines)
        conn.commit()

        total_saved += saved

        last_open_ms = int(klines[-1][0])
        next_start = last_open_ms + ONE_DAY_MS

        if next_start <= current_start:
            break

        current_start = next_start

        if len(klines) < BACKFILL_LIMIT:
            break

        time.sleep(BACKFILL_SLEEP_SECONDS)

    return total_saved, request_count


def get_missing_day_ranges(conn, symbol, target_last_day):
    min_open_time = get_symbol_min_open_time(conn, symbol)

    if not min_open_time:
        return []

    sql = """
        WITH bounds AS (
            SELECT
                (%s::timestamptz AT TIME ZONE 'UTC')::date AS start_day,
                %s::date AS end_day
        ),
        days AS (
            SELECT generate_series(
                (SELECT start_day FROM bounds),
                (SELECT end_day FROM bounds),
                INTERVAL '1 day'
            )::date AS day
        ),
        existing_days AS (
            SELECT DISTINCT
                (open_time AT TIME ZONE 'UTC')::date AS day
            FROM daily_klines
            WHERE source = %s
              AND symbol = %s
              AND interval_name = %s
        ),
        missing_days AS (
            SELECT d.day
            FROM days d
            LEFT JOIN existing_days e ON e.day = d.day
            WHERE e.day IS NULL
        ),
        grouped AS (
            SELECT
                day,
                day - (ROW_NUMBER() OVER (ORDER BY day))::int AS grp
            FROM missing_days
        )
        SELECT
            MIN(day) AS start_day,
            MAX(day) AS end_day,
            COUNT(*) AS missing_days
        FROM grouped
        GROUP BY grp
        ORDER BY start_day;
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                min_open_time,
                target_last_day.date(),
                SOURCE_NAME,
                symbol,
                BACKFILL_INTERVAL,
            ),
        )

        return cur.fetchall()


def sync_symbol(conn, session, symbol, index, total_symbols):
    target_last_day = get_target_last_day_start()
    end_ms = get_target_end_ms()

    max_open_time = get_symbol_max_open_time(conn, symbol)

    total_saved = 0
    total_requests = 0
    repaired_days = 0

    if max_open_time is None:
        mode = "FULL_FROM_FIRST_BINANCE_DAY"
        start_ms = 0
    else:
        next_day = max_open_time + timedelta(days=1)

        if next_day.date() > target_last_day.date():
            mode = "UP_TO_DATE"
            start_ms = None
        else:
            mode = "INCREMENTAL"
            start_ms = dt_to_ms(next_day)

    if start_ms is not None:
        saved, requests_count = sync_range(conn, session, symbol, start_ms, end_ms)
        total_saved += saved
        total_requests += requests_count

    if REPAIR_GAPS:
        missing_ranges = get_missing_day_ranges(conn, symbol, target_last_day)

        for start_day, end_day, missing_count in missing_ranges:
            range_start = datetime(
                start_day.year,
                start_day.month,
                start_day.day,
                tzinfo=timezone.utc,
            )

            range_end = datetime(
                end_day.year,
                end_day.month,
                end_day.day,
                tzinfo=timezone.utc,
            ) + timedelta(days=1)

            range_start_ms = dt_to_ms(range_start)
            range_end_ms = dt_to_ms(range_end) - 1

            saved, requests_count = sync_range(
                conn,
                session,
                symbol,
                range_start_ms,
                range_end_ms,
            )

            total_saved += saved
            total_requests += requests_count
            repaired_days += missing_count

            time.sleep(BACKFILL_SLEEP_SECONDS)

    print(
        f"{index}/{total_symbols} | {symbol} | "
        f"mode={mode} | saved={total_saved} | "
        f"requests={total_requests} | repaired_missing_days={repaired_days}"
    )

    return total_saved, total_requests, repaired_days


def run_sync():
    conn = get_connection()
    session = requests.Session()

    total_saved_all = 0
    total_requests_all = 0
    total_errors = 0
    total_repaired_days = 0

    try:
        ensure_schema(conn)

        symbols = fetch_exchange_symbols(session)
        upserted_symbols = upsert_market_symbols(conn, symbols)
        conn.commit()

        print("Starting Binance DAILY KLINES full sync")
        print(f"Active symbols loaded: {upserted_symbols}")
        print(f"Interval: {BACKFILL_INTERVAL}")
        print(f"Limit per request: {BACKFILL_LIMIT}")
        print(f"Quote filter: {BACKFILL_QUOTE_ASSETS if BACKFILL_QUOTE_ASSETS else 'ALL'}")
        print(f"Max symbols: {BACKFILL_MAX_SYMBOLS if BACKFILL_MAX_SYMBOLS > 0 else 'ALL'}")
        print(f"Exclude current day: {EXCLUDE_CURRENT_DAY}")
        print(f"Repair gaps: {REPAIR_GAPS}")
        print("-" * 80)

        log_ingestion(
            conn,
            "STARTED",
            (
                f"symbols={len(symbols)}, interval={BACKFILL_INTERVAL}, "
                f"quote_filter={BACKFILL_QUOTE_ASSETS if BACKFILL_QUOTE_ASSETS else 'ALL'}, "
                f"repair_gaps={REPAIR_GAPS}"
            ),
        )
        conn.commit()

        for index, item in enumerate(symbols, start=1):
            symbol = item["symbol"]

            try:
                saved, requests_count, repaired_days = sync_symbol(
                    conn,
                    session,
                    symbol,
                    index,
                    len(symbols),
                )

                total_saved_all += saved
                total_requests_all += requests_count
                total_repaired_days += repaired_days

            except Exception as error:
                conn.rollback()
                total_errors += 1

                message = f"{symbol}: {error}"
                log_ingestion(conn, "SYMBOL_ERROR", message)
                conn.commit()

                print(f"ERROR | {message}")
                time.sleep(BACKFILL_ERROR_SLEEP_SECONDS)

            time.sleep(BACKFILL_SLEEP_SECONDS)

        log_ingestion(
            conn,
            "FINISHED",
            (
                f"total_saved={total_saved_all}, "
                f"total_requests={total_requests_all}, "
                f"total_errors={total_errors}, "
                f"total_repaired_days={total_repaired_days}"
            ),
        )
        conn.commit()

        print("-" * 80)
        print("Full sync finished")
        print(f"Total saved/updated rows: {total_saved_all}")
        print(f"Total requests: {total_requests_all}")
        print(f"Total repaired missing days: {total_repaired_days}")
        print(f"Total errors: {total_errors}")

    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    run_sync()
