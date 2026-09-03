"""Tests for the soul (identity) file service (story-60). Pure — temp path, never the real soul."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "admin_api"))

import soul_file as sf  # noqa: E402


def test_validate_rejects_empty_and_whitespace():
    assert sf.validate("")
    assert sf.validate("   \n\t ")


def test_validate_rejects_too_big():
    assert sf.validate("x" * (sf.MAX_BYTES + 1))


def test_validate_rejects_secret_like():
    assert sf.validate("Name: James\n-----BEGIN RSA PRIVATE KEY-----\n...")
    assert sf.validate("api token sk-abcdefghijklmnopqrstuvwxyz012345")


def test_validate_accepts_persona_prose():
    assert sf.validate("## Agent Identity\nName: James Bott\nHe is helpful and concise.") == []


def test_write_atomic_writes_valid(tmp_path, monkeypatch):
    p = tmp_path / "soul.md"
    monkeypatch.setattr(sf, "SOUL_PATH", p)
    meta = sf.write_atomic("## Agent\nName: Test persona")
    assert p.read_text(encoding="utf-8") == "## Agent\nName: Test persona"
    assert meta["bytes"] > 0
    assert len(meta["sha256"]) == 64


def test_write_atomic_rejects_invalid_and_does_not_write(tmp_path, monkeypatch):
    p = tmp_path / "soul.md"
    monkeypatch.setattr(sf, "SOUL_PATH", p)
    with pytest.raises(ValueError):
        sf.write_atomic("   ")
    assert not p.exists()
