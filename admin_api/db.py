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
