import json
from db import Db


def log_audit(actor_email: str, action: str, subject_email: str = None,
              old_value: dict = None, new_value: dict = None):
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_log (actor_email, action, subject_email, old_value, new_value)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                actor_email, action, subject_email,
                json.dumps(old_value) if old_value else None,
                json.dumps(new_value) if new_value else None,
            ))
