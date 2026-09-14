import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import contents, dashboard, products, social, videos
from app.clipper.api.page import router as clipper_page_router
from app.clipper.api.routes import router as clipper_router
from app.core.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title=settings.app_name)

app.include_router(products.router)
app.include_router(contents.router)
app.include_router(videos.router)
app.include_router(social.router)
app.include_router(clipper_page_router)
app.include_router(clipper_router)
app.include_router(dashboard.router)

app.mount("/storage-files", StaticFiles(directory=settings.storage_path), name="storage-files")
