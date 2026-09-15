"""Tests for governed knowledge retrieval (story-64 Phase C2).

Pure: the search helpers in knowledge_store. Governance: the connector tool functions with the shared
service + token resolver monkeypatched (no DB) — asserts the authority-only-from-token rule, the
single not-found error for missing/invisible slugs, argument validation, and that the token never
appears in results or error messages.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "admin_api"))
sys.path.insert(0, str(ROOT))

import knowledge_store as ks  # noqa: E402
import tool_context_store as tcs  # noqa: E402
from mcp.server.fastmcp.exceptions import ToolError  # noqa: E402

from connectors.knowledge import mcp_server as conn  # noqa: E402

# ── pure search helpers ──────────────────────────────────────────────────────

def test_clamp_max_results():
    assert ks.clamp_max_results(0) == 1
    assert ks.clamp_max_results(-5) == 1
    assert ks.clamp_max_results(100) == 50
    assert ks.clamp_max_results(20) == 20
    assert ks.clamp_max_results("x") == ks.SEARCH_DEFAULT_RESULTS
    assert ks.clamp_max_results(None) == ks.SEARCH_DEFAULT_RESULTS


def _docs():
    return [
        {"slug": "principles/a", "title": "A", "category": "principles",
         "content_md": "First line\nSecond MATCH line\nthird match again"},
        {"slug": "playbooks/b", "title": "B", "category": "playbooks",
         "content_md": "no hits here"},
    ]


def test_search_case_insensitive_and_line_numbers():
    m = ks.search_matches(_docs(), "match", 20)
    assert [(x["slug"], x["line"]) for x in m] == [
        ("principles/a", 2), ("principles/a", 3)]
    assert m[0]["snippet"] == "Second MATCH line"
    assert m[0]["title"] == "A" and m[0]["category"] == "principles"


def test_search_empty_query_matches_nothing():
    assert ks.search_matches(_docs(), "   ", 20) == []


def test_search_respects_max_results():
    assert len(ks.search_matches(_docs(), "match", 1)) == 1


def test_snippet_truncates_long_lines():
    long = "x" * (ks.SNIPPET_MAX + 50)
    doc = [{"slug": "reference/x", "title": "X", "category": "reference", "content_md": long}]
    snip = ks.search_matches(doc, "x", 20)[0]["snippet"]
    assert len(snip) == ks.SNIPPET_MAX and snip.endswith("…")


# ── connector governance (monkeypatched service) ─────────────────────────────

@pytest.fixture
def as_member(monkeypatch):
    monkeypatch.setattr(tcs, "resolve",
                        lambda tok: {"authority": "member", "request_id": "req-1"})


def test_resolve_rejects_blank_token():
    with pytest.raises(ToolError):
        conn._resolve("   ")


def test_resolve_rejects_unknown_token(monkeypatch):
    monkeypatch.setattr(tcs, "resolve", lambda tok: None)
    with pytest.raises(ToolError):
        conn._resolve("whatever")


def test_bad_token_never_leaks_into_error(monkeypatch):
    monkeypatch.setattr(tcs, "resolve", lambda tok: None)
    secret = "SECRET-TOKEN-abc123"
    with pytest.raises(ToolError) as ei:
        conn._resolve(secret)
    assert secret not in str(ei.value)


def test_list_uses_token_authority_and_active_only(as_member, monkeypatch):
    captured = {}

    def fake_list_docs(folder=None, status=None, requester_authority=None):
        captured.update(folder=folder, status=status, requester_authority=requester_authority)
        return [{"slug": "principles/a"}]

    monkeypatch.setattr(ks, "list_docs", fake_list_docs)
    out = conn.list_knowledge_docs("tok", category="principles")
    assert out == {"status": "ok", "documents": [{"slug": "principles/a"}]}
    assert captured == {"folder": "principles", "status": "active", "requester_authority": "member"}


def test_read_missing_or_invisible_is_not_found(as_member, monkeypatch):
    monkeypatch.setattr(ks, "get_visible_by_slug", lambda slug, auth: None)
    with pytest.raises(ToolError) as ei:
        conn.read_knowledge_doc("tok", "principles/ghost")
    assert "not found" in str(ei.value).lower()


def test_read_returns_ok_envelope(as_member, monkeypatch):
    doc = {"slug": "principles/a", "content_md": "body"}
    monkeypatch.setattr(ks, "get_visible_by_slug", lambda slug, auth: doc)
    assert conn.read_knowledge_doc("tok", "principles/a") == {"status": "ok", "document": doc}


def test_read_rejects_blank_slug(as_member):
    with pytest.raises(ToolError):
        conn.read_knowledge_doc("tok", "  ")


def test_search_rejects_blank_query(as_member):
    with pytest.raises(ToolError):
        conn.search_knowledge_docs("tok", "   ")


def test_search_ok_envelope_and_authority(as_member, monkeypatch):
    captured = {}

    def fake_search(query, authority, category=None, max_results=20):
        captured.update(query=query, authority=authority, category=category, max_results=max_results)
        return [{"slug": "principles/a", "line": 2}]

    monkeypatch.setattr(ks, "search_visible", fake_search)
    out = conn.search_knowledge_docs("tok", "  hello ", category="principles", max_results=5)
    assert out == {"status": "ok", "query": "hello", "matches": [{"slug": "principles/a", "line": 2}]}
    assert captured == {"query": "hello", "authority": "member",
                        "category": "principles", "max_results": 5}
