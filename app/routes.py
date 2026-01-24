from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from fastapi.responses import FileResponse, JSONResponse
from .config import settings
from .models import documents
from .services import pdf_service
import os

router = APIRouter()

# Pages HTML
@router.get("/")
async def index():
    return FileResponse(settings.STATIC_DIR / "index.html")

@router.get("/upload")
async def upload_page():
    return FileResponse(settings.STATIC_DIR / "upload.html")

@router.get("/reader/{doc_id}")
async def reader(doc_id: str):
    return FileResponse(settings.STATIC_DIR / "reader.html")

@router.get("/gallery")
async def gallery():
    return FileResponse(settings.STATIC_DIR / "gallery.html")

# API
@router.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), title: Optional[str] = Form(None)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    # Utiliser le titre personnalisé ou le nom du fichier
    custom_title = title if title else None
    
    try:
        doc = pdf_service.process_pdf(content, file.filename, custom_title)
        return JSONResponse(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

@router.get("/api/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = documents.get(doc_id)
    if not doc:
        # Try to recover from filesystem
        doc_pages_dir = settings.PAGES_DIR / doc_id
        if doc_pages_dir.exists():
            pages = list(doc_pages_dir.glob("page_*.webp"))
            if pages:
                doc = documents.add(doc_id, doc_id, len(pages))
                return doc
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/api/documents/{doc_id}/page/{page_num}")
async def get_page(doc_id: str, page_num: int):
    page_path = settings.PAGES_DIR / doc_id / f"page_{page_num}.webp"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    
    return FileResponse(page_path, media_type="image/webp")


@router.get("/api/documents")
async def list_documents():
    """Liste les derniers flipbooks créés"""
    docs = []
    pages_dir = settings.PAGES_DIR
    
    if pages_dir.exists():
        # Lister les dossiers et les trier par date de modification
        folders = []
        for folder in pages_dir.iterdir():
            if folder.is_dir():
                stat = folder.stat()
                folders.append((folder.name, stat.st_mtime))
        
        # Trier par date décroissante (plus récent en premier)
        folders.sort(key=lambda x: x[1], reverse=True)
        
        # Prendre les 6 derniers
        for doc_id, mtime in folders[:6]:
            doc_pages_dir = pages_dir / doc_id
            pages = list(doc_pages_dir.glob("page_*.webp"))
            if pages:
                # Récupérer le titre depuis le store ou utiliser l'ID
                doc = documents.get(doc_id)
                title = doc["title"] if doc else doc_id
                docs.append({
                    "id": doc_id,
                    "title": title,
                    "pages": len(pages),
                    "thumbnail": f"/pages/{doc_id}/page_1.webp"
                })
    
    return docs
