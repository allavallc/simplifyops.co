from db import get_conn, put_conn
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        put_conn(conn)
