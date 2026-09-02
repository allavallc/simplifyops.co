"""Tests for the runtime config-ownership service (story-44). Pure — temp files, no DB/live config."""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "admin_api"))

import runtime_config as rc  # noqa: E402


def _write(p: Path, cfg: dict):
    p.write_text(yaml.dump(cfg))


def test_seed_if_missing_copies_base_then_is_noop(tmp_path):
    base = tmp_path / "base.yaml"
    _write(base, {"model": {"provider": "openai-codex", "default": "gpt-5.5"}})
    live = tmp_path / "config.yaml"

    assert rc.seed_if_missing(live, base) is True
    assert live.exists()
    assert rc.read_raw(live)["model"]["default"] == "gpt-5.5"
    # second call must NOT overwrite
    assert rc.seed_if_missing(live, base) is False


def test_seed_never_overwrites_existing(tmp_path):
    base = tmp_path / "base.yaml"
    _write(base, {"model": {"default": "from-base"}})
    live = tmp_path / "config.yaml"
    _write(live, {"model": {"default": "operator-set"}})

    assert rc.seed_if_missing(live, base) is False
    assert rc.read_raw(live)["model"]["default"] == "operator-set"


def test_apply_sets_allowlisted_and_preserves_unrelated(tmp_path):
    live = tmp_path / "config.yaml"
    _write(live, {"model": {"provider": "old", "default": "m"}, "keep": {"this": 1}})

    res = rc.apply({"model.provider": "new"}, live)

    assert res["changed"] is True and res["restart_required"] is True
    assert res["before"] == {"model.provider": "old"}
    cfg = rc.read_raw(live)
    assert cfg["model"]["provider"] == "new"
    assert cfg["model"]["default"] == "m"      # untouched sibling
    assert cfg["keep"] == {"this": 1}          # untouched unrelated subtree


def test_apply_rejects_non_allowlisted_key(tmp_path):
    live = tmp_path / "config.yaml"
    _write(live, {"model": {"provider": "x"}})
    with pytest.raises(rc.ConfigError):
        rc.apply({"logging.level": "DEBUG"}, live)


def test_apply_noop_when_unchanged_does_not_write(tmp_path):
    live = tmp_path / "config.yaml"
    _write(live, {"approvals": {"mode": "smart"}})
    res = rc.apply({"approvals.mode": "smart"}, live)
    assert res["changed"] is False and res["restart_required"] is False
    assert not (tmp_path / "config.yaml.bak").exists()   # no write -> no backup


def test_write_creates_backup_of_previous(tmp_path):
    live = tmp_path / "config.yaml"
    _write(live, {"model": {"provider": "v1"}})
    rc.apply({"model.provider": "v2"}, live)
    bak = tmp_path / "config.yaml.bak"
    assert bak.exists()
    assert yaml.safe_load(bak.read_text())["model"]["provider"] == "v1"


def test_mcp_add_toggle_remove_roundtrip(tmp_path):
    live = tmp_path / "config.yaml"
    _write(live, {"mcp_servers": {}})

    rc.set_mcp_server("gmail", command="npx", args=["-y", "pkg"], enabled=True,
                      env={"HOME": "/x"}, path=live)
    assert rc.read_raw(live)["mcp_servers"]["gmail"]["command"] == "npx"

    rc.toggle_mcp_server("gmail", False, live)
    assert rc.read_raw(live)["mcp_servers"]["gmail"]["enabled"] is False

    rc.remove_mcp_server("gmail", live)
    assert "gmail" not in rc.read_raw(live)["mcp_servers"]

    with pytest.raises(rc.ConfigError):
        rc.toggle_mcp_server("nope", True, live)


def test_read_metadata_redacts_mcp_env_values_and_omits_raw(tmp_path):
    live = tmp_path / "config.yaml"
    _write(live, {
        "model": {"provider": "openai-codex", "default": "gpt-5.5"},
        "mcp_servers": {"gmail": {"command": "npx", "enabled": True,
                                   "env": {"HOME": "/home/pi/secret-ish/path"}}},
    })
    meta = rc.read_metadata(live)

    assert meta["provider"] == "openai-codex"
    server = meta["mcp_servers"][0]
    assert server["name"] == "gmail"
    assert server["env_keys"] == ["HOME"]          # keys only...
    assert "env" not in server                      # ...never the values
    # metadata is a curated view, not the raw config dump
    assert "_config_version" not in meta or "config_version" in meta
    dumped = str(meta)
    assert "/home/pi/secret-ish/path" not in dumped
