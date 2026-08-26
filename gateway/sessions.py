"""Session history + Hermes session mappings + message-cap read.

Extracted from the gateway.py god-module (story-26). One logical session per
user/channel maps to the current physical Hermes session; the cap read drives
physical-session rotation in `hermes_client`.
"""

import os

from gwdb import get_db_conn
from logging_setup import get_logger

log = get_logger("simplifyops-gateway")

SESSION_MESSAGE_CAP_FALLBACK = int(os.environ.get("SESSION_MESSAGE_CAP", "100"))


def append_user_history(user_id: str, user_msg: str, assistant_msg: str) -> None:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO session_history (user_id, user_msg, assistant_msg)
                VALUES (%s, %s, %s)
            """, (user_id, user_msg, assistant_msg))
        conn.commit()
    except Exception as e:
        log.warning("Failed to save session history: %s", e)
        conn.rollback()
    finally:
        conn.close()


def _logical_session_id(channel: str, user_id: str) -> str:
    return f"{channel}:{user_id}"


def get_hermes_session(user_id: str) -> str | None:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT hermes_session_id FROM hermes_session_mappings WHERE user_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def save_hermes_session(user_id: str, channel: str, hermes_session_id: str,
                        rotation_reason: str = None,
                        message_count_at_rotation: int = None) -> None:
    logical = _logical_session_id(channel, user_id)
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hermes_session_mappings
                    (user_id, channel, logical_session_id, hermes_session_id,
                     rotation_reason, message_count_at_rotation)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                    SET hermes_session_id         = EXCLUDED.hermes_session_id,
                        channel                   = EXCLUDED.channel,
                        logical_session_id        = EXCLUDED.logical_session_id,
                        physical_rotations        = hermes_session_mappings.physical_rotations + 1,
                        rotation_reason           = EXCLUDED.rotation_reason,
                        message_count_at_rotation = EXCLUDED.message_count_at_rotation,
                        updated_at                = now()
            """, (user_id, channel, logical, hermes_session_id,
                  rotation_reason, message_count_at_rotation))
        conn.commit()
    except Exception as e:
        log.warning("Failed to save hermes session mapping: %s", e)
        conn.rollback()
    finally:
        conn.close()


def clear_hermes_session(user_id: str) -> None:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hermes_session_mappings WHERE user_id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        log.warning("Failed to clear hermes session mapping: %s", e)
        conn.rollback()
    finally:
        conn.close()


def get_session_message_cap() -> int:
    """Read global cap from admin_settings, fall back to env var default."""
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM admin_settings WHERE key = 'session_message_cap'")
            row = cur.fetchone()
            return int(row[0]) if row else SESSION_MESSAGE_CAP_FALLBACK
    except Exception:
        return SESSION_MESSAGE_CAP_FALLBACK
    finally:
        conn.close()
