import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import contents, dashboard, products, social, videos
from app.clipper.api.page import router as clipper_page_router
from app.clipper.api.routes import router as clipper_router
from app.core.auth import BasicAuthMiddleware
from app.core.config import settings
from app.video_ai.api.page import router as video_ai_page_router
from app.video_ai.api.routes import router as video_ai_router

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if not settings.admin_username or not settings.admin_password:
    logging.getLogger(__name__).warning(
        "ADMIN_USERNAME/ADMIN_PASSWORD not set — app is running with NO authentication. "
        "Set both before exposing this to the internet."
    )

app = FastAPI(title=settings.app_name)
app.add_middleware(BasicAuthMiddleware)

app.include_router(products.router)
app.include_router(contents.router)
app.include_router(videos.router)
app.include_router(social.router)
app.include_router(clipper_page_router)
app.include_router(clipper_router)
app.include_router(video_ai_page_router)
app.include_router(video_ai_router)
app.include_router(dashboard.router)

app.mount("/storage-files", StaticFiles(directory=settings.storage_path), name="storage-files")
app.mount("/clipper-fonts", StaticFiles(directory="app/clipper/fonts"), name="clipper-fonts")
