"""
Admin People JSON API (spec: architecture/people-page.md).

Thin typed-JSON wrappers over the shared `people_service` — the same service the
server-rendered Jinja `/admin/people` pages use, so admin writes and runtime reads
share one source of truth. Kept for programmatic/tool consumers (the React SPA was
retired — story-25). All logic, validation, authorization, and audit live in
`people_service`; these handlers only translate HTTP <-> service calls.
"""

import people_service as svc
from db import Db
from deps import require_admin
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/people")


def _http(err: svc.PeopleError) -> HTTPException:
    return HTTPException(err.status, err.code)


# ── read ─────────────────────────────────────────────────────────────────────

@router.get("")
async def people_index(admin=Depends(require_admin), status: str = Query("active")):
    with Db() as conn:
        status, rows = svc.list_index(conn, status)
    return {"status": status, "count": len(rows), "people": rows}


@router.get("/form-options")
async def form_options(admin=Depends(require_admin)):
    return {"authorities": svc.AUTHORITIES, "identity_types": svc.IDENTITY_TYPES, "timezones": svc.TIMEZONES}


@router.get("/{person_id}")
async def person_detail(person_id: int, admin=Depends(require_admin)):
    try:
        with Db() as conn:
            return svc.get_detail(conn, person_id)
    except svc.PeopleError as e:
        raise _http(e)


# ── mutations ───────────────────────────────────────────────────────────────

class PersonCreate(BaseModel):
    first_name: str
    last_name: str
    primary_email: str
    authority: str = "member"
    can_converse: bool = True
    can_influence: bool = True
    timezone: str | None = None
    notes: str | None = None


class PersonUpdate(BaseModel):
    first_name: str
    last_name: str
    authority: str
    can_converse: bool = True
    can_influence: bool = True
    timezone: str | None = None
    notes: str | None = None


class DeactivateRequest(BaseModel):
    confirm: str


class IdentityCreate(BaseModel):
    identity_type: str
    value: str


@router.post("", status_code=201)
async def create_person(body: PersonCreate, admin=Depends(require_admin)):
    try:
        with Db() as conn:
            person_id = svc.create_person(
                conn, admin, first_name=body.first_name, last_name=body.last_name,
                primary_email=body.primary_email, authority=body.authority,
                can_converse=body.can_converse, can_influence=body.can_influence,
                timezone=body.timezone, notes=body.notes)
        return {"ok": True, "id": person_id}
    except svc.PeopleError as e:
        raise _http(e)


@router.patch("/{person_id}")
async def update_person(person_id: int, body: PersonUpdate, admin=Depends(require_admin)):
    try:
        with Db() as conn:
            svc.update_person(
                conn, admin, person_id, first_name=body.first_name, last_name=body.last_name,
                authority=body.authority, can_converse=body.can_converse,
                can_influence=body.can_influence, timezone=body.timezone, notes=body.notes)
        return {"ok": True, "id": person_id}
    except svc.PeopleError as e:
        raise _http(e)


@router.post("/{person_id}/deactivate")
async def deactivate_person(person_id: int, body: DeactivateRequest, admin=Depends(require_admin)):
    try:
        with Db() as conn:
            svc.deactivate_person(conn, admin, person_id, body.confirm)
        return {"ok": True, "id": person_id, "is_active": False}
    except svc.PeopleError as e:
        raise _http(e)


@router.post("/{person_id}/activate")
async def activate_person(person_id: int, admin=Depends(require_admin)):
    try:
        with Db() as conn:
            svc.activate_person(conn, admin, person_id)
        return {"ok": True, "id": person_id, "is_active": True}
    except svc.PeopleError as e:
        raise _http(e)


@router.post("/{person_id}/identities", status_code=201)
async def add_identity(person_id: int, body: IdentityCreate, admin=Depends(require_admin)):
    try:
        with Db() as conn:
            identity_id = svc.add_identity(conn, admin, person_id, body.identity_type, body.value)
        return {"ok": True, "id": identity_id}
    except svc.PeopleError as e:
        raise _http(e)


@router.delete("/{person_id}/identities/{identity_id}")
async def delete_identity(person_id: int, identity_id: int, admin=Depends(require_admin)):
    try:
        with Db() as conn:
            svc.delete_identity(conn, admin, person_id, identity_id)
        return {"ok": True}
    except svc.PeopleError as e:
        raise _http(e)
