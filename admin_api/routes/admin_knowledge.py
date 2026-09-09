"""Server-rendered super-admin Knowledge pages (story-64 Phase A).

All routes require an active super-admin (an admin may receive knowledge at runtime but not use this
page). Mutations redirect 303; create errors re-render the form with entered values; missing IDs 404.
All storage/validation goes through `knowledge_store`.
"""

import logging
from urllib.parse import quote

import knowledge_store as ks
from audit import log_audit
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from routes.pages import _user, render

log = logging.getLogger("simplifyops-admin")
router = APIRouter()


def _super_guard(request: Request):
    if not request.session.get("admin_email"):
        return RedirectResponse("/")
    if request.session.get("authority") != "super_admin":
        return RedirectResponse("/admin?error=super_admin_required")
    return None


def _ctx(request: Request, **over) -> dict:
    ctx = {
        "user": _user(request),
        "categories": ks.CATEGORIES,
        "authorities": ks.AUTHORITIES,
        "statuses": ks.STATUSES,
        "documents": [],
        "selected": None,
        "new": False,
        "folder": None,
        "status": None,
        "authority": None,
        "error": None,
        "form_values": {},
    }
    ctx.update(over)
    return ctx


@router.get("/admin/knowledge")
async def knowledge_page(request: Request):
    if g := _super_guard(request):
        return g
    ks.seed_from_repo_if_empty()  # first-use seed (no-op once populated)
    q = request.query_params
    folder = q.get("folder") or None
    status = q.get("status") or None
    authority = q.get("authority") or None
    docs = ks.list_docs(folder=folder, status=status, requester_authority=authority)
    selected = ks.get_detail(q["id"]) if q.get("id") else None
    return render(request, "admin/knowledge.html", _ctx(
        request, documents=docs, selected=selected, new=(q.get("new") == "true"),
        folder=folder, status=status, authority=authority, error=q.get("error"),
    ))


@router.post("/admin/knowledge")
async def knowledge_create(request: Request):
    if g := _super_guard(request):
        return g
    form = await request.form()
    actor = request.session["admin_email"]
    try:
        doc = ks.create(actor, form.get("source_folder", ""), form.get("source_filename", ""),
                        form.get("minimum_authority", ""), form.get("content", ""))
    except ks.KnowledgeError as e:
        return render(request, "admin/knowledge.html", _ctx(
            request, documents=ks.list_docs(), new=True, error=str(e),
            form_values={k: form.get(k) for k in
                         ("source_folder", "source_filename", "minimum_authority", "content")},
        ))
    log_audit(actor, "knowledge_create",
              new_value={"slug": doc["slug"], "minimum_authority": doc["minimum_authority"]})
    return RedirectResponse(f"/admin/knowledge?id={doc['id']}", status_code=303)


@router.post("/admin/knowledge/{document_id}")
async def knowledge_edit(request: Request, document_id: str):
    if g := _super_guard(request):
        return g
    before = ks.get_detail(document_id)
    if not before:
        raise HTTPException(404, "not_found")
    form = await request.form()
    actor = request.session["admin_email"]
    try:
        doc = ks.update(actor, document_id, form.get("content", ""), form.get("minimum_authority", ""))
    except ks.KnowledgeError as e:
        return RedirectResponse(f"/admin/knowledge?id={document_id}&error={quote(str(e))}",
                                status_code=303)
    log_audit(actor, "knowledge_edit",
              old_value={"minimum_authority": before["minimum_authority"]},
              new_value={"slug": doc["slug"], "minimum_authority": doc["minimum_authority"]})
    return RedirectResponse(f"/admin/knowledge?id={document_id}", status_code=303)


@router.post("/admin/knowledge/{document_id}/archive")
async def knowledge_archive(request: Request, document_id: str):
    if g := _super_guard(request):
        return g
    actor = request.session["admin_email"]
    try:
        ks.archive(actor, document_id)
    except ks.KnowledgeError:
        raise HTTPException(404, "not_found") from None
    log_audit(actor, "knowledge_archive", new_value={"id": document_id})
    return RedirectResponse(f"/admin/knowledge?id={document_id}", status_code=303)


@router.post("/admin/knowledge/{document_id}/reactivate")
async def knowledge_reactivate(request: Request, document_id: str):
    if g := _super_guard(request):
        return g
    actor = request.session["admin_email"]
    try:
        ks.reactivate(actor, document_id)
    except ks.KnowledgeError:
        raise HTTPException(404, "not_found") from None
    log_audit(actor, "knowledge_reactivate", new_value={"id": document_id})
    return RedirectResponse(f"/admin/knowledge?id={document_id}", status_code=303)


@router.get("/admin/knowledge/{document_id}/download")
async def knowledge_download(request: Request, document_id: str):
    if g := _super_guard(request):
        return g
    res = ks.download_markdown(document_id)
    if not res:
        raise HTTPException(404, "not_found")
    md, filename = res
    return PlainTextResponse(md, media_type="text/markdown",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
