"""Tests for gateway self-knowledge runtime context (story-64 Phase C1). Pure — temp files."""

from gateway.self_knowledge import self_knowledge_context

DOC = """---
minimum_authority: admin
status: active
---

# James — Self-Knowledge

Disclosure policy line.

## Summary

Public one-paragraph summary safe for everyone.

## How I'm Set Up

Admin-only setup detail.
"""


def _write(tmp_path, text):
    p = tmp_path / "self-knowledge.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_admin_gets_full_body(tmp_path):
    p = _write(tmp_path, DOC)
    out = self_knowledge_context("admin", p)
    assert "Admin-only setup detail." in out
    assert "Public one-paragraph summary" in out
    assert "minimum_authority" not in out  # front matter stripped


def test_super_admin_gets_full_body(tmp_path):
    out = self_knowledge_context("super_admin", _write(tmp_path, DOC))
    assert "Admin-only setup detail." in out


def test_member_gets_summary_only(tmp_path):
    out = self_knowledge_context("member", _write(tmp_path, DOC))
    assert out == "Public one-paragraph summary safe for everyone."
    assert "Admin-only setup detail." not in out


def test_contact_gets_summary_only(tmp_path):
    out = self_knowledge_context("contact", _write(tmp_path, DOC))
    assert "Admin-only setup detail." not in out


def test_missing_file_omitted(tmp_path):
    assert self_knowledge_context("admin", tmp_path / "nope.md") is None


def test_secret_like_content_omitted(tmp_path):
    bad = DOC + "\nleaked sk-abcdefghijklmnopqrstuvwxyz012345\n"
    assert self_knowledge_context("admin", _write(tmp_path, bad)) is None


def test_repo_generated_file_loads_for_admin():
    # the committed generated file resolves and returns admin content
    out = self_knowledge_context("super_admin")
    assert out and "James" in out
