"""Tests for the migration runner (story-47). Pure — no DB/psycopg2 needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "admin_api"))

import schema_init  # noqa: E402


def test_baseline_migration_present_and_first():
    migs = schema_init.all_migrations()
    assert migs, "expected at least one migration file"
    assert migs[0].name == "0001_baseline.sql"


def test_pending_filters_applied():
    names = [p.name for p in schema_init.all_migrations()]
    assert [p.name for p in schema_init.pending(set())] == names  # nothing applied → all pending
    assert "0001_baseline.sql" not in [p.name for p in schema_init.pending({"0001_baseline.sql"})]


def test_migrations_ordered_by_name():
    names = [p.name for p in schema_init.all_migrations()]
    assert names == sorted(names)
