# main.py  (will be expanded in Task 9)
from fastapi import FastAPI
from api.auth_routes import router as auth_router
from api.items import router as items_router
from api.tags import router as tags_router
from api.sync_routes import router as sync_router
from api.settings import router as settings_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(items_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
