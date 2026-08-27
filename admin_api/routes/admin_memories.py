"""Memories admin API (story-9). Read-only inspection of Hindsight memory banks."""

import json
import urllib.request

from deps import require_admin
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/admin/memories")
HINDSIGHT = "http://127.0.0.1:8888"


def _get(path: str):
    with urllib.request.urlopen(HINDSIGHT + path, timeout=5) as r:
        return json.loads(r.read())


@router.get("/banks")
async def list_banks(admin=Depends(require_admin)):
    try:
        data = _get("/v1/default/banks")
    except Exception as e:
        raise HTTPException(502, f"hindsight_unreachable: {e}") from e
    return data
