"""
People governance routes.
Owns people + person_identities — the source of truth for who may talk to the agent.
"""

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from pydantic import BaseModel

from db import Db
from deps import require_admin
from audit import log_audit

router = APIRouter(prefix="/api/people")

VALID_AUTHORITIES = {"super_admin", "admin", "member", "contact"}


class PersonBody(BaseModel):
    person_name: str | None = None
    person_email: str
    authority: str = "member"
    can_converse: bool = True
    can_influence: bool = True
    status: str = "allowed"
    admin: bool = False
    notes: str | None = None
    telegram_id: str | None = None
    phone_country_code: str | None = None
    phone_number: str | None = None


class PersonPatch(BaseModel):
    person_name: str | None = None
    person_email: str | None = None
    authority: str | None = None
    can_converse: bool | None = None
    can_influence: bool | None = None
    status: str | None = None
    admin: bool | None = None
    notes: str | None = None
    telegram_id: str | None = None
    phone_country_code: str | None = None
    phone_number: str | None = None


def _upsert_identity(conn, person_id: int, identity_type: str, value: str):
    if not value:
        return
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO person_identities (person_id, identity_type, identity_value, normalized_value, is_primary)
            VALUES (%s, %s, %s, %s, true)
            ON CONFLICT (identity_type, normalized_value) DO UPDATE
                SET person_id = EXCLUDED.person_id
        """, (person_id, identity_type, value, value))


def _remove_identity(conn, person_id: int, identity_type: str):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM person_identities WHERE person_id = %s AND identity_type = %s",
            (person_id, identity_type)
        )


def _count_admins(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*)::int FROM people WHERE admin = true AND deleted_at IS NULL")
        return cur.fetchone()[0]


@router.get("")
async def list_people(admin=Depends(require_admin), show_deleted: bool = False):
    where = "" if show_deleted else "WHERE deleted_at IS NULL"
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT * FROM people {where} ORDER BY created_at DESC")
            return list(cur.fetchall())


@router.get("/{email}")
async def get_person(email: str, admin=Depends(require_admin)):
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM people WHERE person_email = %s LIMIT 1", (email.lower(),))
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, "not_found")
    return row


@router.post("")
async def upsert_person(body: PersonBody, admin=Depends(require_admin)):
    if body.authority not in VALID_AUTHORITIES:
        raise HTTPException(400, f"invalid authority: {body.authority}")
    email = body.person_email.lower().strip()

    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO people (
                    person_name, person_email, authority, can_converse, can_influence,
                    status, admin, notes, telegram_id, phone_country_code, phone_number,
                    created_by, updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                ON CONFLICT (person_email) DO UPDATE SET
                    person_name = EXCLUDED.person_name,
                    authority = EXCLUDED.authority,
                    can_converse = EXCLUDED.can_converse,
                    can_influence = EXCLUDED.can_influence,
                    status = EXCLUDED.status,
                    admin = EXCLUDED.admin,
                    notes = EXCLUDED.notes,
                    telegram_id = EXCLUDED.telegram_id,
                    phone_country_code = EXCLUDED.phone_country_code,
                    phone_number = EXCLUDED.phone_number,
                    created_by = EXCLUDED.created_by,
                    updated_at = now()
                RETURNING *
            """, (body.person_name, email, body.authority, body.can_converse, body.can_influence,
                  body.status, body.admin, body.notes, body.telegram_id,
                  body.phone_country_code, body.phone_number, admin["email"]))
            person = cur.fetchone()

        if body.telegram_id:
            _upsert_identity(conn, person["id"], "telegram", body.telegram_id)

    log_audit(admin["email"], "upsert_person", subject_email=email, new_value=dict(person))
    return person


@router.patch("/{email}")
async def update_person(email: str, body: PersonPatch, admin=Depends(require_admin)):
    email = email.lower()
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM people WHERE person_email = %s", (email,))
            before = cur.fetchone()
        if not before:
            raise HTTPException(404, "not_found")

        if body.admin is False and before["admin"] and _count_admins(conn) <= 1:
            raise HTTPException(400, "cannot_remove_last_admin")

        if body.authority and body.authority not in VALID_AUTHORITIES:
            raise HTTPException(400, f"invalid authority: {body.authority}")

        new_email = (body.person_email or email).lower().strip()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                UPDATE people SET
                    person_email = %s,
                    person_name = COALESCE(%s, person_name),
                    authority = COALESCE(%s, authority),
                    can_converse = COALESCE(%s, can_converse),
                    can_influence = COALESCE(%s, can_influence),
                    status = COALESCE(%s, status),
                    admin = COALESCE(%s, admin),
                    notes = COALESCE(%s, notes),
                    telegram_id = COALESCE(%s, telegram_id),
                    phone_country_code = COALESCE(%s, phone_country_code),
                    phone_number = COALESCE(%s, phone_number),
                    updated_at = now()
                WHERE person_email = %s
                RETURNING *
            """, (new_email, body.person_name, body.authority, body.can_converse,
                  body.can_influence, body.status, body.admin, body.notes,
                  body.telegram_id, body.phone_country_code, body.phone_number, email))
            person = cur.fetchone()

        if body.telegram_id is not None:
            if body.telegram_id:
                _upsert_identity(conn, person["id"], "telegram", body.telegram_id)
            else:
                _remove_identity(conn, person["id"], "telegram")

    log_audit(admin["email"], "update_person", subject_email=email,
              old_value=dict(before), new_value=dict(person))
    return person


@router.delete("/{email}")
async def delete_person(email: str, admin=Depends(require_admin)):
    email = email.lower()
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM people WHERE person_email = %s", (email,))
            before = cur.fetchone()
        if not before:
            raise HTTPException(404, "not_found")
        if before["admin"] and _count_admins(conn) <= 1:
            raise HTTPException(400, "cannot_delete_last_admin")
        # Soft delete (story-20): never physically remove; restorable.
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE people SET deleted_at=now(), updated_at=now() "
                "WHERE person_email = %s AND deleted_at IS NULL",
                (email,),
            )

    log_audit(admin["email"], "soft_delete_person", subject_email=email, old_value=dict(before))
    return {"ok": True}
