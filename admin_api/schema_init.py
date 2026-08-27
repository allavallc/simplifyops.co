"""Forward-only DB migration runner (story-47).

Applies `migrations/*.sql` in filename order, recording applied versions in the
`schema_migrations` table. Idempotent: the baseline uses `IF NOT EXISTS`, so running
against the existing live DB is a safe no-op that just records the baseline as applied.
Each migration runs in its own transaction (statements + the tracking insert together).

Not a place for destructive operations without an explicit, reviewed migration.
"""

from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def all_migrations() -> list:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def pending(applied: set) -> list:
    """Migrations not yet applied, in filename order. Pure — used by tests."""
    return [p for p in all_migrations() if p.name not in applied]


def _applied(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    text PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
        """)
        conn.commit()
        cur.execute("SELECT version FROM schema_migrations")
        return {r[0] for r in cur.fetchall()}


def run_migrations() -> list:
    """Apply pending migrations; return the applied version names (empty if up to date)."""
    from db import Db  # lazy — keeps this module importable (e.g. in CI) without psycopg2
    with Db() as conn:
        applied = _applied(conn)
    ran = []
    for path in pending(applied):
        sql = path.read_text()
        with Db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
        ran.append(path.name)
    return ran
