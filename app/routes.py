from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional, List
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session, select
from datetime import datetime
import json

from .config import settings
from .models import Flipbook, Page
from .database import get_session
from .services import pdf_service, PDFConversionError

router = APIRouter()


# ============================================================================
# PAGES HTML
# ============================================================================

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

@router.get("/editor/{doc_id}")
async def editor_page(doc_id: str):
    return FileResponse(settings.STATIC_DIR / "editor.html")


# ============================================================================
# API - UPLOAD
# ============================================================================

@router.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...), 
    title: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """Upload et convertit un PDF en flipbook"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    custom_title = title if title else None
    
    try:
        doc = await pdf_service.process_pdf(content, file.filename, custom_title, session)
        return JSONResponse(doc)
    except PDFConversionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


# ============================================================================
# API - DOCUMENTS (CRUD)
# ============================================================================

@router.get("/api/documents")
async def list_documents(
    limit: int = 20,
    session: Session = Depends(get_session)
):
    """Liste tous les flipbooks, triés par date de création décroissante"""
    statement = select(Flipbook).order_by(Flipbook.created_at.desc()).limit(limit)
    flipbooks = session.exec(statement).all()
    
    result = []
    for fb in flipbooks:
        result.append({
            "id": fb.id,
            "title": fb.title,
            "pages": fb.page_count,
            "thumbnail": f"/pages/{fb.id}/page_1.webp",
            "created_at": fb.created_at.isoformat(),
        })
    
    return result


@router.get("/api/documents/{doc_id}")
async def get_document(doc_id: str, session: Session = Depends(get_session)):
    """Récupère les détails d'un flipbook"""
    flipbook = session.get(Flipbook, doc_id)
    
    if not flipbook:
        doc_pages_dir = settings.PAGES_DIR / doc_id
        if doc_pages_dir.exists():
            pages = list(doc_pages_dir.glob("page_*.webp"))
            if pages:
                flipbook = Flipbook(
                    id=doc_id,
                    title=doc_id,
                    path=str(doc_pages_dir),
                    page_count=len(pages),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(flipbook)
                session.commit()
                return flipbook.to_dict()
        raise HTTPException(status_code=404, detail="Document not found")
    
    return flipbook.to_dict()


@router.get("/api/documents/{doc_id}/page/{page_num}")
async def get_page(doc_id: str, page_num: int):
    """Récupère l'image d'une page"""
    page_path = settings.PAGES_DIR / doc_id / f"page_{page_num}.webp"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    
    return FileResponse(page_path, media_type="image/webp")


@router.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, session: Session = Depends(get_session)):
    """Supprime un flipbook et ses pages"""
    flipbook = session.get(Flipbook, doc_id)
    if not flipbook:
        raise HTTPException(status_code=404, detail="Document not found")
    
    statement = select(Page).where(Page.flipbook_id == doc_id)
    pages = session.exec(statement).all()
    for page in pages:
        session.delete(page)
    
    session.delete(flipbook)
    session.commit()
    
    import shutil
    doc_pages_dir = settings.PAGES_DIR / doc_id
    if doc_pages_dir.exists():
        shutil.rmtree(doc_pages_dir)
    
    pdf_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    
    return {"status": "deleted", "id": doc_id}


# ============================================================================
# API - EDITOR
# ============================================================================

@router.get("/api/editor/{doc_id}")
async def get_editor_data(doc_id: str, session: Session = Depends(get_session)):
    """
    Récupère les données complètes d'un flipbook pour l'éditeur.
    Inclut les images et toutes les métadonnées (liens, texte, éléments custom).
    """
    flipbook = session.get(Flipbook, doc_id)
    if not flipbook:
        raise HTTPException(status_code=404, detail="Flipbook not found")
    
    statement = select(Page).where(Page.flipbook_id == doc_id).order_by(Page.page_number)
    pages = session.exec(statement).all()
    
    pages_data = []
    for page in pages:
        pages_data.append({
            "page_number": page.page_number,
            "image_url": f"/pages/{page.image_path}",
            "metadata": page.get_metadata()
        })
    
    return {
        "flipbook_id": flipbook.id,
        "title": flipbook.title,
        "page_count": flipbook.page_count,
        "created_at": flipbook.created_at.isoformat(),
        "updated_at": flipbook.updated_at.isoformat(),
        "pages": pages_data
    }


@router.post("/api/editor/{doc_id}")
async def save_editor_data(
    doc_id: str, 
    data: dict,
    session: Session = Depends(get_session)
):
    """
    Sauvegarde les modifications de l'éditeur.
    Permet de modifier le titre et les métadonnées des pages (liens, vidéos, etc.).
    
    Body JSON attendu:
    {
        "title": "Nouveau titre",
        "pages": [
            {
                "page_number": 1,
                "metadata": {
                    "links": [...],
                    "text": "...",
                    "custom_elements": [
                        {"type": "video", "url": "...", "x": 10, "y": 20, "width": 200, "height": 150},
                        {"type": "hotspot", "url": "...", "x": 50, "y": 100, "width": 50, "height": 50}
                    ]
                }
            }
        ]
    }
    """
    flipbook = session.get(Flipbook, doc_id)
    if not flipbook:
        raise HTTPException(status_code=404, detail="Flipbook not found")
    
    if "title" in data:
        flipbook.title = data["title"]
    
    flipbook.updated_at = datetime.utcnow()
    
    if "pages" in data:
        for page_data in data["pages"]:
            page_number = page_data.get("page_number")
            if not page_number:
                continue
            
            statement = select(Page).where(
                Page.flipbook_id == doc_id,
                Page.page_number == page_number
            )
            page = session.exec(statement).first()
            
            if page and "metadata" in page_data:
                page.metadata_json = json.dumps(page_data["metadata"], ensure_ascii=False)
                session.add(page)
    
    session.add(flipbook)
    session.commit()
    session.refresh(flipbook)
    
    return {
        "status": "saved",
        "flipbook_id": doc_id,
        "updated_at": flipbook.updated_at.isoformat()
    }


@router.patch("/api/editor/{doc_id}/page/{page_num}")
async def update_page_metadata(
    doc_id: str,
    page_num: int,
    metadata: dict,
    session: Session = Depends(get_session)
):
    """
    Met à jour les métadonnées d'une page spécifique.
    Utile pour ajouter/modifier un élément sans renvoyer tout le flipbook.
    """
    statement = select(Page).where(
        Page.flipbook_id == doc_id,
        Page.page_number == page_num
    )
    page = session.exec(statement).first()
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    current_metadata = page.get_metadata()
    
    if "links" in metadata:
        current_metadata["links"] = metadata["links"]
    if "text" in metadata:
        current_metadata["text"] = metadata["text"]
    if "custom_elements" in metadata:
        current_metadata["custom_elements"] = metadata["custom_elements"]
    
    page.metadata_json = json.dumps(current_metadata, ensure_ascii=False)
    session.add(page)
    
    flipbook = session.get(Flipbook, doc_id)
    if flipbook:
        flipbook.updated_at = datetime.utcnow()
        session.add(flipbook)
    
    session.commit()
    
    return {
        "status": "updated",
        "page_number": page_num,
        "metadata": current_metadata
    }
