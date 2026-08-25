from fastapi import HTTPException, Request


def require_admin(request: Request) -> dict:
    email = request.session.get("admin_email")
    if not email:
        raise HTTPException(status_code=401, detail="not_signed_in")
    return {
        "email": email,
        "id": request.session.get("admin_id"),
        "authority": request.session.get("authority"),
    }


def require_admin_page(request: Request):
    """For page routes — redirect to login instead of returning JSON 401."""
    from fastapi.responses import RedirectResponse
    email = request.session.get("admin_email")
    if not email:
        return RedirectResponse("/auth/login")
    return None
