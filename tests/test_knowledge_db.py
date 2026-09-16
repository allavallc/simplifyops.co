"""Real-Postgres tests for the knowledge DB layer (story-65).

Covers the authorization-critical SQL that the monkeypatched connector tests cannot: the authority
window + `status='active'` filters in `list_docs`/`get_visible_by_slug`/`search_visible` and token
expiry in `tool_context_store.resolve`. Runs against a throwaway schema (see `conftest.knowledge_db`);
skips when no Postgres is reachable.
"""

import hashlib
from datetime import UTC, datetime, timedelta

import db
import knowledge_store as ks
import tool_context_store as tcs


def _seed_token(authority: str, minutes: int = 10) -> str:
    raw = f"tok-{authority}-{datetime.now(UTC).timestamp()}"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = datetime.now(UTC) + timedelta(minutes=minutes)
    with db.Db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tool_contexts (token_hash, request_id, authority, channel, from_id, "
            "can_influence, expires_at) VALUES (%s,%s,%s,'t','t',false,%s)",
            (token_hash, f"req-{authority}", authority, expires),
        )
    return raw


def _mk(folder: str, filename: str, authority: str, body: str) -> dict:
    return ks.create("t@t", folder, filename, authority, body)


# ── token resolution ─────────────────────────────────────────────────────────

def test_resolve_valid_and_unknown(kdb):
    member = _seed_token("member")
    assert (tcs.resolve(member) or {}).get("authority") == "member"
    assert tcs.resolve("bogus-token") is None


def test_resolve_expired_token(kdb):
    expired = _seed_token("admin", minutes=-1)
    assert tcs.resolve(expired) is None


# ── list: authority window + active-only ─────────────────────────────────────

def test_list_filters_authority_and_archived(kdb):
    _mk("reference", "m.md", "member", "# m\n\nmember body")
    _mk("reference", "a.md", "admin", "# a\n\nadmin body")
    archived = _mk("reference", "old.md", "member", "# old\n\nold body")
    ks.archive("t@t", archived["id"])

    member_view = {d["slug"] for d in ks.list_docs(status="active", requester_authority="member")}
    admin_view = {d["slug"] for d in ks.list_docs(status="active", requester_authority="admin")}

    assert "reference/m" in member_view
    assert "reference/a" not in member_view          # over-authority hidden
    assert "reference/old" not in member_view        # archived hidden
    assert {"reference/m", "reference/a"} <= admin_view


# ── read by slug: authority + missing==invisible ─────────────────────────────

def test_read_authority_and_not_found_unification(kdb):
    _mk("reference", "a.md", "admin", "# a\n\nadmin secret")
    archived = _mk("reference", "old.md", "member", "# old\n\nold body")
    ks.archive("t@t", archived["id"])

    assert ks.get_visible_by_slug("reference/a", "member") is None       # over-authority
    got = ks.get_visible_by_slug("reference/a", "admin")
    assert got["slug"] == "reference/a" and "admin secret" in got["content_md"]
    assert ks.get_visible_by_slug("reference/old", "admin") is None      # archived == missing
    assert ks.get_visible_by_slug("reference/nope", "admin") is None     # truly missing


# ── search: no restricted leak, never archived ───────────────────────────────

def test_search_no_restricted_leak(kdb):
    mark = "ZZMARKER"
    _mk("reference", "m.md", "member", f"# m\n\n{mark} member line")
    _mk("reference", "a.md", "admin", f"# a\n\n{mark} admin line")
    archived = _mk("reference", "old.md", "member", f"# old\n\n{mark} archived line")
    ks.archive("t@t", archived["id"])

    member_hits = {h["slug"] for h in ks.search_visible(mark, "member")}
    admin_hits = {h["slug"] for h in ks.search_visible(mark, "admin")}

    assert "reference/a" not in member_hits          # restricted doc not leaked
    assert "reference/m" in member_hits
    assert "reference/a" in admin_hits
    assert "reference/old" not in admin_hits          # archived never returned


def test_search_match_shape_and_category_filter(kdb):
    _mk("playbooks", "p.md", "member", "# P\n\nfirst\nfindme here\nlast")
    _mk("reference", "r.md", "member", "# R\n\nfindme elsewhere")

    # content_md keeps the "# P" heading, so lines are: 1:"# P" 2:"" 3:"first" 4:"findme here" 5:"last"
    hit = next(h for h in ks.search_visible("findme", "member") if h["slug"] == "playbooks/p")
    assert hit == {"slug": "playbooks/p", "title": "P", "category": "playbooks",
                   "line": 4, "snippet": "findme here"}

    scoped = {h["slug"] for h in ks.search_visible("findme", "member", category="playbooks")}
    assert scoped == {"playbooks/p"}                   # category filter excludes reference/r


# ── create → read round-trip through the shared service ──────────────────────

def test_create_read_roundtrip(kdb):
    _mk("playbooks", "p.md", "member", "# Title Line\n\nhello world body")
    got = ks.get_visible_by_slug("playbooks/p", "member")
    assert got["title"] == "Title Line"
    assert "hello world body" in got["content_md"]
    assert got["status"] == "active" and got["minimum_authority"] == "member"
