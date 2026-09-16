"""Shared pytest fixtures.

`knowledge_db` provisions a throwaway Postgres schema (the real migrations applied into it) so the
DB-layer authority filters (story-65) run against a real database, fully isolated from the live
`public.*` knowledge tables. It skips cleanly when no Postgres socket is reachable, so the pure suite
(and CI) is unaffected.
"""

import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ADMIN_API = str(Path(__file__).resolve().parent.parent / "admin_api")
if ADMIN_API not in sys.path:
    sys.path.insert(0, ADMIN_API)

BASE_DSN = "postgresql:///whitelist_app?host=/var/run/postgresql"


def _db_reachable() -> bool:
    try:
        import psycopg2
    except ModuleNotFoundError:
        return False
    try:
        psycopg2.connect(BASE_DSN, connect_timeout=2).close()
        return True
    except Exception:
        return False


@contextmanager
def _admin_conn():
    """Autocommit connection on the plain DSN (default search_path) — for schema create/drop."""
    import psycopg2
    conn = psycopg2.connect(BASE_DSN)
    conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()


# The tables under test. Cloned structurally from the live `public.*` tables via `LIKE ... INCLUDING
# ALL` — the most authoritative DDL source (the live schema itself), and `LIKE` omits foreign keys, so
# tool_contexts clones without needing the `people` table it normally references. The app's schema is
# fragmented across admin/gateway/migration files with no single "build from scratch" entrypoint, so
# replaying those files is not a clean option.
SOURCE_TABLES = ("knowledge_documents", "knowledge_document_versions", "tool_contexts")


@pytest.fixture(scope="session")
def knowledge_db():
    """Yield a throwaway schema whose tables are structural clones of the live ones. Drops the schema on
    teardown. Skips if Postgres is unreachable or the source tables are absent."""
    if not _db_reachable():
        pytest.skip("Postgres not reachable — skipping DB-layer tests")

    import db

    schema = f"ktest_{os.getpid()}"
    with _admin_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT " + ", ".join(f"to_regclass('public.{t}')" for t in SOURCE_TABLES))
        if any(v is None for v in cur.fetchone()):
            pytest.skip("live knowledge/tool_contexts tables absent — cannot clone")
        cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        cur.execute(f'CREATE SCHEMA "{schema}"')
        for t in SOURCE_TABLES:
            cur.execute(f'CREATE TABLE "{schema}".{t} (LIKE public.{t} INCLUDING ALL)')

    # search_path = the throwaway schema, so the store's unqualified queries resolve to the clones.
    original_dsn = db.DSN
    db.DSN = f"{BASE_DSN}&options=-csearch_path%3D{schema}"
    db.init_pool()
    try:
        yield schema
    finally:
        # Fully revert the session-global mutation of the db module (pool + DSN).
        if db._pool is not None:
            db._pool.closeall()
            db._pool = None
        db.DSN = original_dsn
        with _admin_conn() as conn, conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


@pytest.fixture
def kdb(knowledge_db):
    """Function-scoped: a clean throwaway schema — truncates the knowledge/tool-context tables so each
    test starts empty. Returns the schema name."""
    import db
    with db.Db() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE knowledge_documents, knowledge_document_versions, tool_contexts "
                    "RESTART IDENTITY")
    return knowledge_db
