"""Gateway database connection + schema application.

Extracted from the former gateway.py god-module (story-26) so DB access is one
small, reusable seam instead of being intertwined with workers/adapters.
"""

import os
from pathlib import Path

import psycopg2
from logging_setup import get_logger

log = get_logger("simplifyops-gateway")

DB_DSN = os.environ.get("GATEWAY_DB_DSN", "postgresql:///whitelist_app?host=/var/run/postgresql")


def get_db_conn():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    return conn


def apply_schema():
    schema_path = Path(__file__).parent / "sql" / "schema.sql"
    sql = schema_path.read_text()
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        log.info("Schema applied")
    finally:
        conn.close()
