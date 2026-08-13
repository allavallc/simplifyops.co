import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException

from db import Db
from deps import require_admin

router = APIRouter(prefix="/api/activity")


@router.get("")
async def list_activity(status: str = "all", limit: int = 100, admin=Depends(require_admin)):
    limit = min(limit, 500)
    where = "" if status == "all" else "WHERE w.status = %s"
    params = [limit] if status == "all" else [limit, status]
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                SELECT
                    w.id, w.request_id, w.status, w.attempt_count, w.error_summary,
                    left(w.reply_text, 120) AS reply_preview,
                    w.created_at, w.updated_at,
                    r.channel, r.from_id, r.from_name, r.chat_id,
                    left(r.message_text, 200) AS message_preview,
                    length(r.message_text) AS message_length
                FROM work_items w
                JOIN requests r ON r.id = w.request_id
                {where}
                ORDER BY w.created_at DESC
                LIMIT %s
            """, params if status == "all" else [status, limit])
            return list(cur.fetchall())


@router.get("/{item_id}")
async def get_activity(item_id: int, admin=Depends(require_admin)):
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT w.*, r.channel, r.from_id, r.from_name, r.chat_id,
                       r.message_text, r.created_at AS requested_at
                FROM work_items w
                JOIN requests r ON r.id = w.request_id
                WHERE w.id = %s
            """, (item_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, "not_found")
    return row
