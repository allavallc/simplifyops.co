import os

import psycopg2
import psycopg2.extras
import psycopg2.pool

DSN = os.environ.get("GATEWAY_DB_DSN", "postgresql:///whitelist_app?host=/var/run/postgresql")

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def init_pool():
    global _pool
    _pool = psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=10, dsn=DSN)


def get_conn():
    return _pool.getconn()


def put_conn(conn):
    _pool.putconn(conn)


class Db:
    """Context manager: acquire a connection, auto-commit or rollback, return to pool."""
    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = get_conn()
        self.conn.autocommit = False
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        put_conn(self.conn)
        return False


# ── admin_settings: single source of truth ──────────────────────────────────
# Defaults are defined here once. Never re-read a key with an inline default
# literal elsewhere — go through get_setting/set_setting.
DEFAULT_SESSION_MESSAGE_CAP = 100
DEFAULT_TIMEZONE = "America/New_York"


def get_setting(cur, key, default=None):
    """Read one admin_settings value using an existing cursor.
    Returns the stored string, or `default` if the key is absent."""
    cur.execute("SELECT value FROM admin_settings WHERE key=%s", (key,))
    row = cur.fetchone()
    return row[0] if row else default


def set_setting(cur, key, value, updated_by):
    """Upsert one admin_settings value using an existing cursor."""
    cur.execute(
        """
        INSERT INTO admin_settings (key, value, updated_by)
        VALUES (%s, %s, %s)
        ON CONFLICT (key) DO UPDATE
            SET value=%s, updated_at=now(), updated_by=%s
        """,
        (key, str(value), updated_by, str(value), updated_by),
    )
