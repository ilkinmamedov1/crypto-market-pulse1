import os
from contextlib import closing

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


load_dotenv()


def get_db_config():
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "crypto_market"),
        "user": os.getenv("POSTGRES_USER", "crypto_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "12345"),
    }


def get_connection():
    return psycopg2.connect(**get_db_config())


def fetch_all(sql, params=None):
    params = params or ()

    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def fetch_one(sql, params=None):
    params = params or ()

    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def execute(sql, params=None, fetch_one_result=False, fetch_all_result=False):
    params = params or ()

    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)

            result = None

            if fetch_one_result:
                row = cur.fetchone()
                result = dict(row) if row else None

            if fetch_all_result:
                result = [dict(row) for row in cur.fetchall()]

            conn.commit()
            return result
