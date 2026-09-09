"""Knowledge store/service (story-64, Phase A).

Shared validation + persistence for curated knowledge docs. Routes and (later) tools go through this
single service — no independent parsing/storage rules elsewhere. Pure helpers (front-matter parsing,
validation, slug/category, path safety, canonical render, authority ladder) are unit-testable without a
DB; the store methods lazy-import `db`.

Front-matter contract (exactly two keys):

    ---
    minimum_authority: member
    status: active
    ---
    # Title
    body...
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = REPO_ROOT / "knowledge"

AUTHORITIES = ["contact", "member", "admin", "super_admin"]  # ascending
STATUSES = ["active", "archived"]
CATEGORIES = ["principles", "processes", "patterns", "playbooks",
              "real-life-examples", "case-studies", "reference", "about-myself"]

# Structural/human files the seeder never imports as knowledge docs.
SEED_SKIP_NAMES = {"README.md", "INDEX.md", "sources.md"}

_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
]
# Path components: start alnum; then alnum, dot, underscore, hyphen.
_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class KnowledgeError(ValueError):
    """Rejected knowledge input (bad front matter, path, or content)."""


def authority_meets(requester: str, minimum: str) -> bool:
    """True if `requester`'s authority is >= the doc's `minimum_authority`."""
    if requester not in AUTHORITIES or minimum not in AUTHORITIES:
        return False
    return AUTHORITIES.index(requester) >= AUTHORITIES.index(minimum)


def _scan_secrets(text: str) -> bool:
    return any(p.search(text) for p in _SECRET_PATTERNS)


def parse_and_validate(text: str) -> tuple[dict, str]:
    """Parse front matter + body; validate the contract. Returns (meta, body) or raises."""
    if "\x00" in text:
        raise KnowledgeError("content contains NUL")
    if not text.startswith("---"):
        raise KnowledgeError("missing front matter")
    # split: ---\n<yaml>\n---\n<body>
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        raise KnowledgeError("malformed front matter")
    raw_meta, body = m.group(1), m.group(2)
    try:
        meta = yaml.safe_load(raw_meta)
    except yaml.YAMLError as e:
        raise KnowledgeError(f"invalid YAML front matter: {e}") from None
    if not isinstance(meta, dict):
        raise KnowledgeError("front matter is not a mapping")
    if set(meta.keys()) != {"minimum_authority", "status"}:
        raise KnowledgeError("front matter must have exactly: minimum_authority, status")
    if meta["minimum_authority"] not in AUTHORITIES:
        raise KnowledgeError(f"minimum_authority must be one of {AUTHORITIES}")
    if meta["status"] not in STATUSES:
        raise KnowledgeError(f"status must be one of {STATUSES}")
    if not body.strip():
        raise KnowledgeError("empty content")
    if _scan_secrets(text):
        raise KnowledgeError("content appears to contain secret-like material")
    return meta, body


def title_from_body(body: str, slug: str) -> str:
    """First level-1 heading, else derive from the slug's last segment."""
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return slug.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").strip()


def slug_and_category(rel_path: str) -> tuple[str, str]:
    """`playbooks/x.md` -> ('playbooks/x', 'playbooks'); root file -> category 'root'."""
    rel = rel_path[:-3] if rel_path.endswith(".md") else rel_path
    parts = rel.split("/")
    category = parts[0] if len(parts) > 1 else "root"
    return rel, category


def validate_rel_path(rel_path: str) -> str:
    """Validate a canonical `knowledge/`-relative path. Returns it, or raises."""
    if rel_path != rel_path.strip() or rel_path.startswith("/") or "\\" in rel_path:
        raise KnowledgeError("invalid path")
    parts = rel_path.split("/")
    for p in parts:
        if p in ("", ".", "..") or p.startswith(".") or not _PATH_COMPONENT.match(p):
            raise KnowledgeError(f"invalid path component: {p!r}")
    if not rel_path.endswith(".md"):
        raise KnowledgeError("path must end in .md")
    return rel_path


def build_path(folder: str, filename: str) -> str:
    """Create-form input: an approved folder + a single `.md` filename → canonical rel path."""
    if folder not in CATEGORIES:
        raise KnowledgeError(f"folder must be one of {CATEGORIES}")
    if "/" in filename or "\\" in filename:
        raise KnowledgeError("filename must not contain a path")
    return validate_rel_path(f"{folder}/{filename}")


def is_read_only(rel_path: str) -> bool:
    return "/generated/" in rel_path or rel_path.startswith("generated/")


def render_canonical(minimum_authority: str, status: str, content_md: str) -> str:
    """Canonical Markdown from structured fields + body (for download)."""
    body = content_md if content_md.endswith("\n") else content_md + "\n"
    return f"---\nminimum_authority: {minimum_authority}\nstatus: {status}\n---\n\n{body}"


# ── Persistence (lazy db import) ────────────────────────────────────────────

def _summary(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "category": row["category"],
        "slug": row["slug"],
        "title": row["title"],
        "source_type": row["source_type"],
        "read_only": row["read_only"],
        "status": row["status"],
        "minimum_authority": row["minimum_authority"],
        "source_path": row["source_path"],
        "sync_state": row["sync_state"],
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "updated_by": row["updated_by"],
    }


def _record_version(cur, doc_id, content_md: str, actor_email: str, change_summary: str) -> None:
    import hashlib
    sha = hashlib.sha256(content_md.encode("utf-8")).hexdigest()
    cur.execute("""
        INSERT INTO knowledge_document_versions
            (document_id, version_number, content_sha256, content_md, actor_email, change_summary)
        SELECT %s, COALESCE(MAX(version_number), 0) + 1, %s, %s, %s, %s
        FROM knowledge_document_versions WHERE document_id = %s
    """, (doc_id, sha, content_md, actor_email, change_summary, doc_id))


def create(actor_email: str, folder: str, filename: str, minimum_authority: str, content: str) -> dict:
    import psycopg2.errors
    import psycopg2.extras
    from db import Db
    rel_path = build_path(folder, filename)
    full_text = render_canonical(minimum_authority, "active", content)
    meta, body = parse_and_validate(full_text)
    slug, category = slug_and_category(rel_path)
    title = title_from_body(body, slug)
    read_only = is_read_only(rel_path)
    if read_only:
        raise KnowledgeError("cannot create documents under generated/")
    with Db() as conn:
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO knowledge_documents
                        (category, slug, title, content_md, source_type, read_only, status,
                         minimum_authority, source_path, sync_state, updated_by)
                    VALUES (%s,%s,%s,%s,'admin_created',%s,'active',%s,%s,'db_only',%s)
                    RETURNING *
                """, (category, slug, title, body, read_only, minimum_authority, rel_path, actor_email))
                row = cur.fetchone()
                _record_version(cur, row["id"], body, actor_email, "created")
        except psycopg2.errors.UniqueViolation:
            raise KnowledgeError("a document with that path/slug already exists") from None
    return _summary(row)


def update(actor_email: str, doc_id: str, content: str, minimum_authority: str) -> dict:
    import psycopg2.extras
    from db import Db
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM knowledge_documents WHERE id = %s", (doc_id,))
            cur_row = cur.fetchone()
            if not cur_row:
                raise KnowledgeError("document not found", )
            if cur_row["read_only"]:
                raise KnowledgeError("document is read-only")
            full_text = render_canonical(minimum_authority, cur_row["status"], content)
            _meta, body = parse_and_validate(full_text)
            title = title_from_body(body, cur_row["slug"])
            body_changed = body != cur_row["content_md"]
            cur.execute("""
                UPDATE knowledge_documents
                SET content_md=%s, title=%s, minimum_authority=%s, updated_by=%s, updated_at=now()
                WHERE id=%s RETURNING *
            """, (body, title, minimum_authority, actor_email, doc_id))
            row = cur.fetchone()
            if body_changed:
                _record_version(cur, doc_id, body, actor_email, "edited")
    return _summary(row)


def _set_status(actor_email: str, doc_id: str, status: str) -> dict:
    import psycopg2.extras
    from db import Db
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                UPDATE knowledge_documents SET status=%s, updated_by=%s, updated_at=now()
                WHERE id=%s RETURNING *
            """, (status, actor_email, doc_id))
            row = cur.fetchone()
    if not row:
        raise KnowledgeError("document not found")
    return _summary(row)


def archive(actor_email: str, doc_id: str) -> dict:
    return _set_status(actor_email, doc_id, "archived")


def reactivate(actor_email: str, doc_id: str) -> dict:
    return _set_status(actor_email, doc_id, "active")


def get_detail(doc_id: str) -> dict | None:
    import psycopg2.extras
    from db import Db
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM knowledge_documents WHERE id = %s", (doc_id,))
            row = cur.fetchone()
    if not row:
        return None
    d = _summary(row)
    d["content_md"] = row["content_md"]
    return d


def list_docs(folder: str | None = None, status: str | None = None,
              requester_authority: str | None = None) -> list[dict]:
    """Admin listing. `requester_authority` (if set) filters to docs at/below that authority."""
    import psycopg2.extras
    from db import Db
    clauses, params = [], []
    if folder:
        clauses.append("category = %s"); params.append(folder)
    if status:
        clauses.append("status = %s"); params.append(status)
    if requester_authority in AUTHORITIES:
        allowed = AUTHORITIES[: AUTHORITIES.index(requester_authority) + 1]
        clauses.append("minimum_authority = ANY(%s)"); params.append(allowed)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with Db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT * FROM knowledge_documents {where} ORDER BY category, slug", params)
            return [_summary(r) for r in cur.fetchall()]


def download_markdown(doc_id: str) -> tuple[str, str] | None:
    d = get_detail(doc_id)
    if not d:
        return None
    md = render_canonical(d["minimum_authority"], d["status"], d["content_md"])
    filename = d["slug"].rsplit("/", 1)[-1] + ".md"
    return md, filename


def seed_from_repo_if_empty() -> int:
    """First-use seed: only when the store is empty, import valid knowledge docs under knowledge/
    (skipping structural files + generated/). Returns count imported. Invalid files are skipped."""
    import logging

    import psycopg2.extras
    from db import Db
    log = logging.getLogger("simplifyops-admin")
    with Db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM knowledge_documents")
            if cur.fetchone()[0] > 0:
                return 0
    imported = 0
    if not KNOWLEDGE_ROOT.exists():
        return 0
    for path in sorted(KNOWLEDGE_ROOT.rglob("*.md")):
        rel = path.relative_to(KNOWLEDGE_ROOT).as_posix()
        if path.name in SEED_SKIP_NAMES or "/generated/" in rel or rel.startswith("generated/"):
            continue
        try:
            validate_rel_path(rel)
            meta, body = parse_and_validate(path.read_text(encoding="utf-8"))
        except (KnowledgeError, UnicodeDecodeError) as e:
            log.warning("knowledge seed: skipping %s: %s", rel, e)
            continue
        slug, category = slug_and_category(rel)
        title = title_from_body(body, slug)
        with Db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO knowledge_documents
                        (category, slug, title, content_md, source_type, read_only, status,
                         minimum_authority, source_path, sync_state, updated_by)
                    VALUES (%s,%s,%s,%s,'repo_seed',false,%s,%s,%s,'seeded','system')
                    ON CONFLICT (slug) DO NOTHING
                    RETURNING id
                """, (category, slug, title, body, meta["status"], meta["minimum_authority"], rel))
                r = cur.fetchone()
                if r:
                    _record_version(cur, r["id"], body, "system", "seeded from repo")
                    imported += 1
    log.info("knowledge seed: imported %d docs", imported)
    return imported
