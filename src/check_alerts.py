import os
import time
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


load_dotenv()


POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "crypto_market"),
    "user": os.getenv("POSTGRES_USER", "crypto_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "12345"),
}


ALERT_CHECK_SECONDS = int(os.getenv("ALERT_CHECK_SECONDS", "60"))
ALERT_DEFAULT_COOLDOWN_MINUTES = int(os.getenv("ALERT_DEFAULT_COOLDOWN_MINUTES", "60"))

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", SMTP_USER)


def get_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)


def smtp_configured():
    return bool(SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASSWORD and ALERT_FROM_EMAIL)


def ensure_schema(conn):
    ddl = """
    CREATE TABLE IF NOT EXISTS alert_rules (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(200) NOT NULL,

        scope_quote_asset VARCHAR(30),
        direction VARCHAR(10) NOT NULL CHECK (direction IN ('up', 'down')),
        threshold_percent NUMERIC NOT NULL,

        comparison_mode VARCHAR(30) NOT NULL CHECK (comparison_mode IN ('rolling_window', 'fixed_date_range')),

        window_minutes INTEGER,

        baseline_start_date DATE,
        baseline_end_date DATE,
        baseline_price_type VARCHAR(30) NOT NULL DEFAULT 'avg_close'
            CHECK (baseline_price_type IN ('first_close', 'last_close', 'avg_close', 'highest_high', 'lowest_low')),

        cooldown_minutes INTEGER NOT NULL DEFAULT 60,
        include_new_symbols BOOLEAN NOT NULL DEFAULT TRUE,

        is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        last_checked_at TIMESTAMPTZ,
        last_triggered_at TIMESTAMPTZ,

        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled
        ON alert_rules(is_enabled);

    CREATE TABLE IF NOT EXISTS alert_recipients (
        id BIGSERIAL PRIMARY KEY,
        rule_id BIGINT NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
        email VARCHAR(320) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_alert_recipients_rule_id
        ON alert_recipients(rule_id);

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

    CREATE INDEX IF NOT EXISTS idx_alert_events_rule_symbol_created
        ON alert_events(rule_id, symbol, created_at DESC);

    CREATE INDEX IF NOT EXISTS idx_alert_events_created_at
        ON alert_events(created_at DESC);

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

    CREATE INDEX IF NOT EXISTS idx_alert_email_logs_created_at
        ON alert_email_logs(created_at DESC);

    CREATE TABLE IF NOT EXISTS alert_new_symbol_notifications (
        rule_id BIGINT NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
        symbol VARCHAR(30) NOT NULL,
        notified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (rule_id, symbol)
    );
    """

    with conn.cursor() as cur:
        cur.execute(ddl)

    conn.commit()


def fetch_rules(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                id,
                name,
                COALESCE(scope_quote_asset, '') AS scope_quote_asset,
                direction,
                threshold_percent::double precision AS threshold_percent,
                comparison_mode,
                window_minutes,
                baseline_start_date,
                baseline_end_date,
                baseline_price_type,
                cooldown_minutes,
                include_new_symbols,
                created_at
            FROM alert_rules
            WHERE is_enabled = TRUE
            ORDER BY id;
        """)
        return [dict(row) for row in cur.fetchall()]


def fetch_recipients(conn, rule_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT email
            FROM alert_recipients
            WHERE rule_id = %s
            ORDER BY email;
        """, (rule_id,))
        return [row[0] for row in cur.fetchall()]


def update_rule_checked(conn, rule_id):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE alert_rules
            SET last_checked_at = NOW(),
                updated_at = NOW()
            WHERE id = %s;
        """, (rule_id,))
    conn.commit()


def scope_filter_sql(alias="s"):
    return f"AND (%s = '' OR COALESCE({alias}.quote_asset, '') = %s)"


def get_rolling_matches(conn, rule):
    sql = f"""
        WITH scoped_symbols AS (
            SELECT
                l.symbol,
                l.last_price,
                l.fetched_at AS latest_time,
                s.base_asset,
                s.quote_asset
            FROM market_ticker_latest l
            LEFT JOIN market_symbols s
                ON s.source = l.source
               AND s.symbol = l.symbol
            WHERE l.source = 'binance'
              AND l.last_price IS NOT NULL
              {scope_filter_sql("s")}
        ),
        baseline AS (
            SELECT DISTINCT ON (h.symbol)
                h.symbol,
                h.last_price AS baseline_price,
                h.fetched_at AS baseline_time
            FROM market_ticker_history h
            JOIN scoped_symbols ss
                ON ss.symbol = h.symbol
            WHERE h.source = 'binance'
              AND h.last_price IS NOT NULL
              AND h.fetched_at >= NOW() - (%s || ' minutes')::interval
            ORDER BY h.symbol, h.fetched_at ASC
        ),
        calculated AS (
            SELECT
                ss.symbol,
                b.baseline_price::double precision AS baseline_price,
                ss.last_price::double precision AS latest_price,
                b.baseline_time,
                ss.latest_time,
                (((ss.last_price - b.baseline_price) / b.baseline_price) * 100)::double precision AS actual_percent
            FROM scoped_symbols ss
            JOIN baseline b
                ON b.symbol = ss.symbol
            WHERE b.baseline_price IS NOT NULL
              AND b.baseline_price <> 0
        )
        SELECT *
        FROM calculated
        WHERE
            (
                %s = 'up'
                AND actual_percent >= %s
            )
            OR
            (
                %s = 'down'
                AND actual_percent <= -ABS(%s)
            )
        ORDER BY ABS(actual_percent) DESC;
    """

    params = (
        rule["scope_quote_asset"],
        rule["scope_quote_asset"],
        rule["window_minutes"],
        rule["direction"],
        rule["threshold_percent"],
        rule["direction"],
        rule["threshold_percent"],
    )

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def baseline_expression(baseline_price_type):
    if baseline_price_type == "first_close":
        return "(ARRAY_AGG(d.close_price ORDER BY d.open_time ASC))[1]"
    if baseline_price_type == "last_close":
        return "(ARRAY_AGG(d.close_price ORDER BY d.open_time DESC))[1]"
    if baseline_price_type == "highest_high":
        return "MAX(d.high_price)"
    if baseline_price_type == "lowest_low":
        return "MIN(d.low_price)"
    return "AVG(d.close_price)"


def get_fixed_range_matches(conn, rule):
    baseline_expr = baseline_expression(rule["baseline_price_type"])

    sql = f"""
        WITH scoped_symbols AS (
            SELECT
                l.symbol,
                l.last_price,
                l.fetched_at AS latest_time,
                s.base_asset,
                s.quote_asset
            FROM market_ticker_latest l
            LEFT JOIN market_symbols s
                ON s.source = l.source
               AND s.symbol = l.symbol
            WHERE l.source = 'binance'
              AND l.last_price IS NOT NULL
              {scope_filter_sql("s")}
        ),
        baseline AS (
            SELECT
                d.symbol,
                {baseline_expr} AS baseline_price,
                MIN(d.open_time) AS baseline_time
            FROM daily_klines d
            JOIN scoped_symbols ss
                ON ss.symbol = d.symbol
            WHERE d.source = 'binance'
              AND d.interval_name = '1d'
              AND d.open_time::date BETWEEN %s::date AND %s::date
            GROUP BY d.symbol
        ),
        calculated AS (
            SELECT
                ss.symbol,
                b.baseline_price::double precision AS baseline_price,
                ss.last_price::double precision AS latest_price,
                b.baseline_time,
                ss.latest_time,
                (((ss.last_price - b.baseline_price) / b.baseline_price) * 100)::double precision AS actual_percent
            FROM scoped_symbols ss
            JOIN baseline b
                ON b.symbol = ss.symbol
            WHERE b.baseline_price IS NOT NULL
              AND b.baseline_price <> 0
        )
        SELECT *
        FROM calculated
        WHERE
            (
                %s = 'up'
                AND actual_percent >= %s
            )
            OR
            (
                %s = 'down'
                AND actual_percent <= -ABS(%s)
            )
        ORDER BY ABS(actual_percent) DESC;
    """

    params = (
        rule["scope_quote_asset"],
        rule["scope_quote_asset"],
        rule["baseline_start_date"],
        rule["baseline_end_date"],
        rule["direction"],
        rule["threshold_percent"],
        rule["direction"],
        rule["threshold_percent"],
    )

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def recently_triggered(conn, rule_id, symbol, cooldown_minutes):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM alert_events
            WHERE rule_id = %s
              AND symbol = %s
              AND created_at >= NOW() - (%s || ' minutes')::interval
            LIMIT 1;
        """, (rule_id, symbol, cooldown_minutes))
        return cur.fetchone() is not None


def filter_cooldown(conn, rule, matches):
    filtered = []

    for item in matches:
        if not recently_triggered(conn, rule["id"], item["symbol"], rule["cooldown_minutes"]):
            filtered.append(item)

    return filtered


def fetch_new_symbols(conn, rule):
    if not rule["include_new_symbols"]:
        return []

    sql = f"""
        SELECT
            ms.symbol,
            ms.base_asset,
            ms.quote_asset,
            TO_CHAR(ms.first_seen_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS first_seen_at
        FROM market_symbols ms
        WHERE ms.source = 'binance'
          {scope_filter_sql("ms")}
          AND ms.first_seen_at >= %s
          AND NOT EXISTS (
              SELECT 1
              FROM alert_new_symbol_notifications n
              WHERE n.rule_id = %s
                AND n.symbol = ms.symbol
          )
        ORDER BY ms.first_seen_at DESC, ms.symbol
        LIMIT 50;
    """

    params = (
        rule["scope_quote_asset"],
        rule["scope_quote_asset"],
        rule["created_at"],
        rule["id"],
    )

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def insert_events(conn, rule, matches, email_status):
    event_ids = []

    with conn.cursor() as cur:
        for item in matches:
            cur.execute("""
                INSERT INTO alert_events (
                    rule_id,
                    rule_name,
                    symbol,
                    direction,
                    threshold_percent,
                    actual_percent,
                    baseline_price,
                    latest_price,
                    baseline_time,
                    latest_time,
                    comparison_mode,
                    baseline_price_type,
                    window_minutes,
                    baseline_start_date,
                    baseline_end_date,
                    email_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                rule["id"],
                rule["name"],
                item["symbol"],
                rule["direction"],
                rule["threshold_percent"],
                item["actual_percent"],
                item["baseline_price"],
                item["latest_price"],
                item["baseline_time"],
                item["latest_time"],
                rule["comparison_mode"],
                rule["baseline_price_type"],
                rule["window_minutes"],
                rule["baseline_start_date"],
                rule["baseline_end_date"],
                email_status,
            ))
            event_ids.append(cur.fetchone()[0])

        if matches:
            cur.execute("""
                UPDATE alert_rules
                SET last_triggered_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s;
            """, (rule["id"],))

    conn.commit()
    return event_ids


def update_events_status(conn, event_ids, status):
    if not event_ids:
        return

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE alert_events
            SET email_status = %s
            WHERE id = ANY(%s);
        """, (status, event_ids))

    conn.commit()


def mark_new_symbols_notified(conn, rule_id, new_symbols):
    if not new_symbols:
        return

    with conn.cursor() as cur:
        for item in new_symbols:
            cur.execute("""
                INSERT INTO alert_new_symbol_notifications (rule_id, symbol)
                VALUES (%s, %s)
                ON CONFLICT (rule_id, symbol)
                DO NOTHING;
            """, (rule_id, item["symbol"]))

    conn.commit()


def insert_email_log(conn, rule_id, recipient, status, matched_count, new_symbol_count, error_message=None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO alert_email_logs (
                rule_id,
                recipient_email,
                status,
                matched_count,
                new_symbol_count,
                error_message
            )
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (rule_id, recipient, status, matched_count, new_symbol_count, error_message))

    conn.commit()


def build_email(rule, matches, new_symbols):
    direction_word = "increased" if rule["direction"] == "up" else "dropped"
    scope = rule["scope_quote_asset"] if rule["scope_quote_asset"] else "ALL"

    subject = (
        f"Crypto Alert: {len(matches)} symbols {direction_word} "
        f"{rule['threshold_percent']}%+"
    )

    lines = []
    lines.append("Crypto Market Alert")
    lines.append("")
    lines.append(f"Rule: {rule['name']}")
    lines.append(f"Scope: {scope}")
    lines.append(f"Direction: {direction_word}")
    lines.append(f"Threshold: {rule['threshold_percent']}%")
    lines.append(f"Comparison mode: {rule['comparison_mode']}")

    if rule["comparison_mode"] == "rolling_window":
        lines.append(f"Window: {rule['window_minutes']} minutes")
    else:
        lines.append(f"Date range: {rule['baseline_start_date']} -> {rule['baseline_end_date']}")
        lines.append(f"Baseline: {rule['baseline_price_type']}")

    lines.append("")
    lines.append("Matched symbols:")

    if matches:
        for item in matches[:100]:
            lines.append(
                f"- {item['symbol']}: {item['actual_percent']:.4f}% "
                f"baseline={item['baseline_price']} latest={item['latest_price']}"
            )

        if len(matches) > 100:
            lines.append(f"... and {len(matches) - 100} more symbols")
    else:
        lines.append("- No price movement matches in this check.")

    if new_symbols:
        lines.append("")
        lines.append("New Binance symbols detected:")
        for item in new_symbols[:50]:
            lines.append(
                f"- {item['symbol']} ({item.get('base_asset') or '-'} / {item.get('quote_asset') or '-'}) "
                f"first_seen={item.get('first_seen_at') or '-'}"
            )

    lines.append("")
    lines.append("Generated by Crypto Market Pulse.")

    return subject, "\n".join(lines)


def send_email(recipients, subject, body):
    if not smtp_configured():
        return "SKIPPED_SMTP_NOT_CONFIGURED", "SMTP is not configured in .env"

    message = EmailMessage()
    message["From"] = ALERT_FROM_EMAIL
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        if SMTP_USE_TLS:
            server.starttls()

        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)

    return "SENT", None


def check_rule(conn, rule):
    update_rule_checked(conn, rule["id"])

    if rule["comparison_mode"] == "rolling_window":
        matches = get_rolling_matches(conn, rule)
    else:
        matches = get_fixed_range_matches(conn, rule)

    matches = filter_cooldown(conn, rule, matches)
    new_symbols = fetch_new_symbols(conn, rule)

    if not matches and not new_symbols:
        print(f"rule={rule['id']} no matches")
        return

    recipients = fetch_recipients(conn, rule["id"])

    if not recipients:
        event_ids = insert_events(conn, rule, matches, "NO_RECIPIENTS")
        print(f"rule={rule['id']} matched={len(matches)} new_symbols={len(new_symbols)} no recipients")
        return

    subject, body = build_email(rule, matches, new_symbols)

    event_ids = insert_events(conn, rule, matches, "PENDING")

    try:
        status, error = send_email(recipients, subject, body)
        update_events_status(conn, event_ids, status)

        for recipient in recipients:
            insert_email_log(
                conn,
                rule["id"],
                recipient,
                status,
                len(matches),
                len(new_symbols),
                error,
            )

        if status == "SENT":
            mark_new_symbols_notified(conn, rule["id"], new_symbols)

        print(
            f"rule={rule['id']} matched={len(matches)} "
            f"new_symbols={len(new_symbols)} email_status={status}"
        )

    except Exception as error:
        update_events_status(conn, event_ids, "FAILED")

        for recipient in recipients:
            insert_email_log(
                conn,
                rule["id"],
                recipient,
                "FAILED",
                len(matches),
                len(new_symbols),
                str(error),
            )

        print(f"rule={rule['id']} email failed: {error}")


def run_loop():
    print("Starting all-market alert worker")
    print(f"Check interval: {ALERT_CHECK_SECONDS} seconds")
    print(f"SMTP configured: {smtp_configured()}")

    conn = get_connection()

    try:
        ensure_schema(conn)

        while True:
            rules = fetch_rules(conn)

            if not rules:
                print("No enabled alert rules")

            for rule in rules:
                try:
                    check_rule(conn, rule)
                except Exception as error:
                    conn.rollback()
                    print(f"rule={rule.get('id')} error: {error}")

            time.sleep(ALERT_CHECK_SECONDS)

    except KeyboardInterrupt:
        print("Stopped by user.")

    finally:
        conn.close()


if __name__ == "__main__":
    run_loop()
