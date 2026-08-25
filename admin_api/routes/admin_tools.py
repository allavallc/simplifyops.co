"""Tools (MCP) admin API (story-9). Read-only view of configured MCP servers from
the runtime config. Non-secret fields only."""

from pathlib import Path

import yaml
from deps import require_admin
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/admin/tools")
HERMES_CONFIG = Path("/home/pi/.hermes/profiles/simplifyops/config.yaml")


@router.get("")
async def list_tools(admin=Depends(require_admin)):
    servers = []
    try:
        cfg = yaml.safe_load(HERMES_CONFIG.read_text()) or {}
        for name, s in (cfg.get("mcp_servers") or {}).items():
            env = s.get("env") or {}
            servers.append({
                "name": name,
                "command": s.get("command"),
                "service": env.get("GOOGLE_WORKSPACE_SERVICES"),
                "enabled": bool(s.get("enabled")),
            })
    except Exception:
        pass
    return {"servers": servers}
