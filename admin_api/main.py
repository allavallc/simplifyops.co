import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from db import init_pool
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes.activity import router as activity_router
from routes.admin_memories import router as admin_memories_router
from routes.admin_people import router as admin_people_router
from routes.admin_tools import router as admin_tools_router
from routes.auth import router as auth_router
from routes.health import router as health_router
from routes.inbox import router as inbox_router
from routes.integrations import router as integrations_router
from routes.messages import router as messages_router
from routes.pages import router as pages_router
from routes.people import router as people_router
from routes.settings import router as settings_router
from routes.settings import runtime_router
from routes.tool_contexts import router as tool_contexts_router
from schema_init import run_migrations
from starlette.middleware.sessions import SessionMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

SESSION_SECRET = os.environ["ADMIN_SESSION_SECRET"]
BASE_DIR = Path(__file__).parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    run_migrations()
    yield


app = FastAPI(title="SimplifyOps Admin API", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=60 * 60 * 24 * 7)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(messages_router)
app.include_router(people_router)
app.include_router(admin_people_router)
app.include_router(admin_tools_router)
app.include_router(admin_memories_router)
app.include_router(inbox_router)
app.include_router(integrations_router)
app.include_router(activity_router)
app.include_router(tool_contexts_router)
app.include_router(settings_router)
app.include_router(runtime_router)
app.include_router(pages_router)  # server-rendered admin pages (routes/pages.py)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
