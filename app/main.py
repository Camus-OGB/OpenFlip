import mimetypes
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .config import settings
from .routes import router
from .database import init_db

mimetypes.add_type("image/webp", ".webp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base de données au démarrage"""
    init_db()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
app.mount("/pages", StaticFiles(directory=settings.PAGES_DIR), name="pages")
app.mount("/storage/images", StaticFiles(directory=settings.STORAGE_DIR / "images"), name="images")

app.include_router(router)
