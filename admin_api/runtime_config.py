"""Runtime config-ownership service (story-44).

Owns the env-owned Hermes `config.yaml` lifecycle:
  - **seed-if-missing** from the tracked per-env base `hermes/config.base.<env>.yaml`
    (never overwrites an existing live config);
  - **redacted metadata read** for the admin UI (never returns the whole raw config);
  - **allowlisted, structured writes** (atomic + backup) — only known non-secret keys, plus
    MCP-server registrations via dedicated helpers.

The tracked base holds structural non-secret defaults only. The live `config.yaml` is
env-owned/gitignored and is the ONLY file a write touches. Secrets never live in either the base or
this module's output. No DB import — audit + session-clearing are the caller's job (route layer,
one-way-deps rule 4).
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

ENV = os.environ.get("SIMPLIFYOPS_ENV", "prod")
PROFILE_ROOT = Path(os.environ.get("HERMES_PROFILE_ROOT", "/home/pi/.hermes/profiles/simplifyops"))
LIVE_CONFIG = PROFILE_ROOT / "config.yaml"
BASE_DIR = Path(__file__).resolve().parent.parent / "hermes"
RESTART_SERVICE = "simplifyops-agent-runtime.service"

# Editable non-secret scalar keys (dotted). Anything not listed is file-only and rejected by apply().
# Story-44 decision A: provider/model/context + session bits (+ MCP servers via helpers below).
ALLOWLIST = frozenset({
    "model.provider",
    "model.default",
    "model.base_url",
    "memory.url",
    "approvals.mode",
    "agent.max_turns",
    "agent.reasoning_effort",
    "sessions.auto_prune",
    "sessions.retention_days",
})

# MCP-server fields the UI/editor may set (non-secret structure). `env` values can carry host paths,
# so they are stored but never returned by read_metadata() (keys shown as presence only).
_MCP_FIELDS = frozenset({"command", "args", "enabled", "env"})


def base_path(env: str = ENV) -> Path:
    return BASE_DIR / f"config.base.{env}.yaml"


def read_raw(path: Path = LIVE_CONFIG) -> dict:
    """Full parsed config. Internal use only — never return this straight to a client."""
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _write_atomic(cfg: dict, path: Path = LIVE_CONFIG) -> None:
    """Back up the current file (`.bak`) then atomically replace it. Restrictive perms."""
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    tmp = Path(tempfile.mktemp(dir=path.parent, prefix=".config.yaml."))
    try:
        tmp.write_text(yaml.dump(cfg, default_flow_style=False, allow_unicode=True, sort_keys=False))
        os.chmod(tmp, 0o600)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def seed_if_missing(path: Path = LIVE_CONFIG, base: Path | None = None) -> bool:
    """If the live config is absent, seed it from the tracked base. Returns True if seeded.
    Never overwrites an existing live config."""
    if path.exists():
        return False
    src = base or base_path()
    if not src.exists():
        raise FileNotFoundError(f"no base template for env: {src}")
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(yaml.safe_load(src.read_text()) or {}, path)
    return True


def _get(cfg: dict, dotted: str):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _set(cfg: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    cur = cfg
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _mcp_summary(cfg: dict) -> list[dict]:
    """Non-secret MCP view: name/enabled/command/args + env KEYS only (values may be host paths)."""
    out = []
    for name, spec in sorted((cfg.get("mcp_servers") or {}).items()):
        spec = spec or {}
        out.append({
            "name": name,
            "enabled": bool(spec.get("enabled", True)),
            "command": spec.get("command"),
            "args": spec.get("args") or [],
            "env_keys": sorted((spec.get("env") or {}).keys()),
        })
    return out


def read_metadata(path: Path = LIVE_CONFIG) -> dict:
    """Redacted, structured view for the admin UI. Never returns the whole raw config."""
    cfg = read_raw(path)
    model = cfg.get("model") or {}
    return {
        "env": ENV,
        "live_exists": path.exists(),
        "base_exists": base_path().exists(),
        "config_version": cfg.get("_config_version"),
        "provider": model.get("provider"),
        "model": model.get("default"),
        "base_url": model.get("base_url"),
        "memory_url": (cfg.get("memory") or {}).get("url"),
        "approvals_mode": (cfg.get("approvals") or {}).get("mode"),
        "agent_max_turns": (cfg.get("agent") or {}).get("max_turns"),
        "agent_reasoning_effort": (cfg.get("agent") or {}).get("reasoning_effort"),
        "sessions": cfg.get("sessions") or {},
        "mcp_servers": _mcp_summary(cfg),
        "editable_keys": sorted(ALLOWLIST),
    }


class ConfigError(ValueError):
    """Rejected config write (non-allowlisted key or invalid value)."""


def apply(patch: dict, path: Path = LIVE_CONFIG) -> dict:
    """Apply allowlisted scalar changes. `patch` maps dotted keys -> values. Rejects any key not in
    ALLOWLIST. Structured merge preserves all unrelated keys. Returns before/after (only the touched
    keys) + changed/restart_required. Does NOT restart or audit (caller's job)."""
    bad = [k for k in patch if k not in ALLOWLIST]
    if bad:
        raise ConfigError(f"not editable: {', '.join(sorted(bad))}")
    cfg = read_raw(path)
    before = {k: _get(cfg, k) for k in patch}
    for k, v in patch.items():
        _set(cfg, k, v)
    after = {k: _get(cfg, k) for k in patch}
    changed = before != after
    if changed:
        _write_atomic(cfg, path)
    return {"changed": changed, "restart_required": changed, "before": before, "after": after}


def set_mcp_server(name: str, command: str, args: list | None = None,
                   enabled: bool = True, env: dict | None = None,
                   path: Path = LIVE_CONFIG) -> dict:
    """Add or update an MCP server registration (non-secret structure). Returns restart_required."""
    if not name:
        raise ConfigError("mcp server name required")
    cfg = read_raw(path)
    servers = cfg.setdefault("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ConfigError("mcp_servers is malformed")
    spec = {"command": command, "args": args or [], "enabled": bool(enabled)}
    if env:
        spec["env"] = env
    servers[name] = spec
    _write_atomic(cfg, path)
    return {"changed": True, "restart_required": True, "server": name}


def toggle_mcp_server(name: str, enabled: bool, path: Path = LIVE_CONFIG) -> dict:
    cfg = read_raw(path)
    servers = cfg.get("mcp_servers") or {}
    if name not in servers:
        raise ConfigError(f"unknown mcp server: {name}")
    servers[name]["enabled"] = bool(enabled)
    _write_atomic(cfg, path)
    return {"changed": True, "restart_required": True, "server": name, "enabled": bool(enabled)}


def remove_mcp_server(name: str, path: Path = LIVE_CONFIG) -> dict:
    cfg = read_raw(path)
    servers = cfg.get("mcp_servers") or {}
    if name not in servers:
        raise ConfigError(f"unknown mcp server: {name}")
    del servers[name]
    _write_atomic(cfg, path)
    return {"changed": True, "restart_required": True, "server": name}


def restart_runtime() -> None:
    """Explicit runtime reload (the one shared restart action; story-44 decision B)."""
    result = subprocess.run(
        ["sudo", "/bin/systemctl", "restart", RESTART_SERVICE],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"runtime restart failed: {result.stderr[:200]}")
