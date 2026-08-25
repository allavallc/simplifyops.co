"""
Shared People governance service (spec: architecture/people-page.md).

Single source of truth for people + identity read/mutation logic, used by BOTH the
server-rendered Jinja admin routes (`main.py`) and the JSON API
(`routes/admin_people.py`) — so admin writes and runtime reads go through one place
(spec: "admin writes and runtime reads use the same source of truth").

Each function takes an already-open connection (the caller owns the transaction via
`Db()`) plus the acting admin dict, enforces validation/authorization, and writes a
non-secret audit event on mutation. Domain failures raise `PeopleError(code, status)`;
callers map it to their surface (JSON API -> HTTPException, Jinja -> re-render).
"""

import os

import psycopg2
import psycopg2.extras
from audit import log_audit

AUTHORITIES = ["member", "contact", "admin", "super_admin"]
IDENTITY_TYPES = ["email", "telegram", "discord", "phone", "whatsapp", "google_calendar", "google_chat"]
# Conversational-governance identities exclude google_calendar (provider notifications, per spec).
TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Anchorage", "Pacific/Honolulu", "UTC", "Europe/London", "Europe/Paris",
    "Asia/Kolkata", "Asia/Singapore", "Asia/Tokyo", "Australia/Sydney",
]
# Bootstrap/protected super-admins that can never be deactivated (spec safety guard).
PROTECTED_EMAILS = {
    e.strip().lower() for e in os.environ.get("PROTECTED_SUPER_ADMIN_EMAILS", "").split(",") if e.strip()
}

_STATUS_WHERE = {"active": "p.deleted_at IS NULL", "inactive": "p.deleted_at IS NOT NULL", "all": "TRUE"}


class PeopleError(Exception):
    """Domain error. `code` is a stable machine-readable string; `status` is the HTTP
    status the JSON API should use. Jinja callers render `code` as a form error."""
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


# ── helpers ──────────────────────────────────────────────────────────────────

def norm_email(v: str) -> str:
    return (v or "").strip().lower()


def full_name(first: str, last: str) -> str:
    return " ".join(p for p in [(first or "").strip(), (last or "").strip()] if p)


def can_grant(actor_authority: str, target_authority: str) -> bool:
    """Only super_admin may grant admin/super_admin; admin may grant member/contact."""
    if actor_authority == "super_admin":
        return True
    if actor_authority == "admin":
        return target_authority in ("member", "contact")
    return False


def count_active_admins(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)::int FROM people
            WHERE deleted_at IS NULL AND authority IN ('admin','super_admin')
        """)
        return cur.fetchone()[0]


def load_person(conn, person_id: int) -> dict:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM people WHERE id = %s", (person_id,))
        row = cur.fetchone()
    if not row:
        raise PeopleError("person_not_found", 404)
    return row


def person_id_for_email(conn, email: str) -> int:
    """Resolve a person_email to id — lets Jinja routes keep email-based URLs while the
    service stays id-keyed (spec/blueprint key on id)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM people WHERE person_email = %s", (norm_email(email),))
        row = cur.fetchone()
    if not row:
        raise PeopleError("person_not_found", 404)
    return row[0]


def identities(conn, person_id: int) -> list:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, identity_type, identity_value, normalized_value, is_primary
            FROM person_identities WHERE person_id = %s ORDER BY is_primary DESC, identity_type
        """, (person_id,))
        return list(cur.fetchall())


def normalize_identity(identity_type: str, value: str) -> str:
    """Type-specific normalization shared with governance lookup. Email/chat handles are
    lowercased; phone keeps digits and a leading '+'; others trimmed."""
    v = (value or "").strip()
    if identity_type in ("email", "google_calendar", "google_chat", "discord", "whatsapp"):
        return v.lower()
    if identity_type == "phone":
        return "+" + "".join(c for c in v if c.isdigit()) if v else v
    return v


# ── read ─────────────────────────────────────────────────────────────────────

def list_index(conn, status: str = "active") -> tuple[str, list]:
    """Aggregated index read model — identity types joined in one query (no N+1)."""
    where = _STATUS_WHERE.get(status, _STATUS_WHERE["active"])
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT p.id, p.person_name, p.first_name, p.last_name, p.person_email,
                   p.authority, p.can_converse, p.can_influence, p.status,
                   (p.deleted_at IS NULL) AS is_active,
                   COALESCE(array_agg(DISTINCT pi.identity_type)
                       FILTER (WHERE pi.identity_type IS NOT NULL), ARRAY[]::text[]) AS identity_types
            FROM people p
            LEFT JOIN person_identities pi ON pi.person_id = p.id
            WHERE {where}
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """)
        rows = list(cur.fetchall())
    return (status if status in _STATUS_WHERE else "active"), rows


def get_detail(conn, person_id: int) -> dict:
    person = load_person(conn, person_id)
    person["is_active"] = person["deleted_at"] is None
    person["identities"] = identities(conn, person_id)
    person["deactivate_confirm_phrase"] = person["person_email"]
    return person


# ── mutations ────────────────────────────────────────────────────────────────

def create_person(conn, actor, *, first_name, last_name, primary_email, authority="member",
                  can_converse=True, can_influence=True, timezone=None, notes=None) -> int:
    if authority not in AUTHORITIES:
        raise PeopleError("invalid_authority", 400)
    if not can_grant(actor["authority"], authority):
        raise PeopleError("not_authorized_for_authority", 403)
    first, last = (first_name or "").strip(), (last_name or "").strip()
    if not first or not last:
        raise PeopleError("first_and_last_name_required", 400)
    email = norm_email(primary_email)
    if not email:
        raise PeopleError("primary_email_required", 400)

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO people (first_name, last_name, person_name, person_email,
                    authority, can_converse, can_influence, timezone, notes, admin, created_by, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                RETURNING id
            """, (first, last, full_name(first, last), email, authority, can_converse,
                  can_influence, (timezone or None), (notes or None),
                  authority in ("admin", "super_admin"), actor["email"]))
            person_id = cur.fetchone()["id"]
            cur.execute("""
                INSERT INTO person_identities (person_id, identity_type, identity_value, normalized_value, is_primary)
                VALUES (%s,'email',%s,%s,true)
                ON CONFLICT (identity_type, normalized_value) DO NOTHING
            """, (person_id, email, email))
    except psycopg2.errors.UniqueViolation:
        raise PeopleError("email_already_exists", 409)

    log_audit(actor["email"], "person_created", subject_email=email,
              new_value={"id": person_id, "authority": authority, "name": full_name(first, last)})
    return person_id


def update_person(conn, actor, person_id, *, first_name, last_name, authority,
                  can_converse=True, can_influence=True, timezone=None, notes=None) -> None:
    if authority not in AUTHORITIES:
        raise PeopleError("invalid_authority", 400)
    first, last = (first_name or "").strip(), (last_name or "").strip()
    if not first or not last:
        raise PeopleError("first_and_last_name_required", 400)

    before = load_person(conn, person_id)
    if before["authority"] != authority and not can_grant(actor["authority"], authority):
        raise PeopleError("not_authorized_for_authority", 403)
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE people SET first_name=%s, last_name=%s, person_name=%s, authority=%s,
                can_converse=%s, can_influence=%s, timezone=%s, notes=%s, admin=%s, updated_at=now()
            WHERE id=%s
        """, (first, last, full_name(first, last), authority, can_converse, can_influence,
              (timezone or None), (notes or None), authority in ("admin", "super_admin"), person_id))

    log_audit(actor["email"], "person_updated", subject_email=before["person_email"],
              old_value={"authority": before["authority"], "name": before["person_name"],
                         "can_converse": before["can_converse"], "can_influence": before["can_influence"]},
              new_value={"authority": authority, "name": full_name(first, last),
                         "can_converse": can_converse, "can_influence": can_influence})


def deactivate_person(conn, actor, person_id, confirm) -> None:
    person = load_person(conn, person_id)
    email = person["person_email"]

    if email and email.lower() in PROTECTED_EMAILS:
        log_audit(actor["email"], "person_deactivate_rejected", subject_email=email,
                  new_value={"reason": "protected_super_admin"})
        raise PeopleError("protected_profile", 403)
    if actor.get("id") is not None and int(actor["id"]) == int(person_id):
        raise PeopleError("cannot_deactivate_self", 400)
    if person["authority"] in ("admin", "super_admin") and person["deleted_at"] is None:
        if count_active_admins(conn) <= 1:
            raise PeopleError("cannot_deactivate_last_admin", 400)
    if (confirm or "").strip().lower() != (email or "").strip().lower():
        raise PeopleError("confirmation_mismatch", 400)

    with conn.cursor() as cur:
        cur.execute("UPDATE people SET deleted_at=now(), updated_at=now() WHERE id=%s AND deleted_at IS NULL",
                    (person_id,))
    log_audit(actor["email"], "person_deactivated", subject_email=email, old_value={"active": True})


def activate_person(conn, actor, person_id) -> None:
    person = load_person(conn, person_id)
    with conn.cursor() as cur:
        cur.execute("UPDATE people SET deleted_at=NULL, updated_at=now() WHERE id=%s", (person_id,))
    log_audit(actor["email"], "person_activated", subject_email=person["person_email"],
              new_value={"active": True})


def add_identity(conn, actor, person_id, identity_type, value) -> int:
    person = load_person(conn, person_id)
    if identity_type not in IDENTITY_TYPES:
        raise PeopleError("invalid_identity_type", 400)
    raw = (value or "").strip()
    if not raw:
        raise PeopleError("identity_value_required", 400)
    normalized = normalize_identity(identity_type, raw)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO person_identities (person_id, identity_type, identity_value, normalized_value, is_primary)
                VALUES (%s,%s,%s,%s,false) RETURNING id
            """, (person_id, identity_type, raw, normalized))
            identity_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise PeopleError("identity_already_exists", 409)

    log_audit(actor["email"], "person_identity_added", subject_email=person["person_email"],
              new_value={"identity_type": identity_type, "value": normalized})
    return identity_id


def delete_identity(conn, actor, person_id, identity_id) -> None:
    person = load_person(conn, person_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM person_identities WHERE id=%s", (identity_id,))
        ident = cur.fetchone()
    if not ident:
        raise PeopleError("identity_not_found", 404)
    if ident["person_id"] != int(person_id):
        raise PeopleError("identity_person_mismatch", 400)
    if ident["is_primary"]:
        raise PeopleError("cannot_delete_primary_identity", 400)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM person_identities WHERE id=%s", (identity_id,))
    log_audit(actor["email"], "person_identity_deleted", subject_email=person["person_email"],
              old_value={"identity_id": identity_id, "identity_type": ident["identity_type"]})
