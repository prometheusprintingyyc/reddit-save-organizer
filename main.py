from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db
from config import settings
from api.auth_routes import router as auth_router
from api.items import router as items_router
from api.tags import router as tags_router
from api.sync_routes import router as sync_router
from api.settings import router as settings_router
from scheduler import create_scheduler

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_dir = os.path.dirname(settings.database_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    init_db()
    global _scheduler
    _scheduler = create_scheduler(settings.sync_interval_hours)
    _scheduler.start()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(items_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(settings_router, prefix="/api")

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
