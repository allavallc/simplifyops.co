"""Tests for knowledge_store pure helpers (story-64 Phase A). No DB."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "admin_api"))

import knowledge_store as ks  # noqa: E402


def _doc(auth="member", status="active", body="# Title\n\nbody"):
    return f"---\nminimum_authority: {auth}\nstatus: {status}\n---\n\n{body}\n"


def test_authority_ladder():
    assert ks.authority_meets("admin", "member") is True
    assert ks.authority_meets("member", "admin") is False
    assert ks.authority_meets("super_admin", "super_admin") is True
    assert ks.authority_meets("bogus", "member") is False


def test_parse_valid():
    meta, body = ks.parse_and_validate(_doc())
    assert meta == {"minimum_authority": "member", "status": "active"}
    assert body.strip() == "# Title\n\nbody".strip()


@pytest.mark.parametrize("text", [
    "no front matter",
    "---\nminimum_authority: member\n---\n\nbody",           # missing status
    "---\nminimum_authority: member\nstatus: active\nextra: x\n---\n\nbody",  # extra key
    "---\nminimum_authority: boss\nstatus: active\n---\n\nbody",  # bad authority
    "---\nminimum_authority: member\nstatus: live\n---\n\nbody",  # bad status
    "---\nminimum_authority: member\nstatus: active\n---\n\n   ",  # empty body
])
def test_parse_rejects(text):
    with pytest.raises(ks.KnowledgeError):
        ks.parse_and_validate(text)


def test_parse_rejects_secret_like():
    with pytest.raises(ks.KnowledgeError):
        ks.parse_and_validate(_doc(body="# T\n\ntoken sk-abcdefghijklmnopqrstuvwxyz012345"))


def test_title_from_body_and_fallback():
    assert ks.title_from_body("# Hello World\n\nx", "reference/x") == "Hello World"
    assert ks.title_from_body("no heading here", "playbooks/my-doc") == "my doc"


def test_slug_and_category():
    assert ks.slug_and_category("playbooks/x.md") == ("playbooks/x", "playbooks")
    assert ks.slug_and_category("root-note.md") == ("root-note", "root")


@pytest.mark.parametrize("bad", [
    "../escape.md", "principles/../x.md", ".hidden/x.md", "a/b.md/../c.md",
    "has space.md", "principles/x.txt", "/abs/x.md",
])
def test_validate_rel_path_rejects(bad):
    with pytest.raises(ks.KnowledgeError):
        ks.validate_rel_path(bad)


def test_build_path_and_read_only():
    assert ks.build_path("reference", "ok.md") == "reference/ok.md"
    with pytest.raises(ks.KnowledgeError):
        ks.build_path("not-a-folder", "ok.md")
    with pytest.raises(ks.KnowledgeError):
        ks.build_path("reference", "sub/ok.md")
    assert ks.is_read_only("about-myself/generated/self-knowledge.md") is True
    assert ks.is_read_only("reference/x.md") is False


def test_render_canonical_roundtrips():
    md = ks.render_canonical("admin", "active", "# T\n\nbody")
    meta, body = ks.parse_and_validate(md)
    assert meta == {"minimum_authority": "admin", "status": "active"}
    assert body.strip() == "# T\n\nbody"
