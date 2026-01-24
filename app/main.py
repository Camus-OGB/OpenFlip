import mimetypes
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .config import settings
from .routes import router

# Add webp mime type
mimetypes.add_type("image/webp", ".webp")

app = FastAPI(title=settings.APP_NAME)

app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
app.mount("/pages", StaticFiles(directory=settings.PAGES_DIR), name="pages")

app.include_router(router)
