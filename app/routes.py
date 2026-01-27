from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import json

from .config import settings
from .models import Flipbook, Page, Widget, EditorSaveRequest
from .database import get_session
from .services import pdf_service, PDFConversionError

router = APIRouter()


# ============================================================================
# PAGES HTML
# ============================================================================

@router.get("/")
async def index():
    """Page d'accueil"""
    return FileResponse(settings.STATIC_DIR / "index.html")


@router.get("/upload")
async def upload_page():
    """Page d'upload"""
    return FileResponse(settings.STATIC_DIR / "upload.html")


@router.get("/reader/{doc_id}")
async def reader(doc_id: str):
    """Page de lecture du flipbook"""
    return FileResponse(settings.STATIC_DIR / "reader.html")


@router.get("/gallery")
async def gallery():
    """Page galerie"""
    return FileResponse(settings.STATIC_DIR / "gallery.html")


@router.get("/editor/{doc_id}")
async def editor_page(doc_id: str):
    """Page editeur"""
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
    """
    Upload et convertit un PDF en flipbook.

    - Recoit un fichier PDF (max 50MB)
    - Le sauvegarde dans storage/uploads/
    - Convertit chaque page en WebP dans storage/pages/{id}/
    - Cree les entrees en base de donnees
    - Extrait automatiquement les liens hypertextes du PDF

    Returns:
        JSON avec les infos du flipbook cree
    """
    # Validation du fichier
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptes")

    # Lecture du contenu
    content = await file.read()

    # Validation de la taille
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux (max {settings.MAX_FILE_SIZE // (1024*1024)}MB)"
        )

    # Traitement du PDF
    try:
        result = await pdf_service.process_pdf(
            content=content,
            filename=file.filename,
            custom_title=title,
            session=session
        )
        return JSONResponse(result)

    except PDFConversionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de conversion: {str(e)}")


@router.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload une image (background ou logo).
    
    - Accepte JPG, PNG, WebP, GIF
    - Sauvegarde dans storage/images/
    - Retourne l'URL relative
    """
    import uuid
    import mimetypes
    from pathlib import Path
    
    # Créer le dossier s'il n'existe pas
    images_dir = settings.STORAGE_DIR / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Validation du type de fichier
    allowed_types = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé. Acceptés: JPG, PNG, WebP, GIF"
        )
    
    # Validation de la taille (max 5MB pour les images)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image trop volumineux (max 5MB)"
        )
    
    # Générer un nom unique
    ext = Path(file.filename).suffix or mimetypes.guess_extension(file.content_type)
    filename = f"{uuid.uuid4()}{ext}"
    filepath = images_dir / filename
    
    # Sauvegarder le fichier
    try:
        with open(filepath, "wb") as f:
            f.write(content)
        
        # Retourner l'URL relative
        relative_url = f"/storage/images/{filename}"
        return {"url": relative_url, "filename": filename}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'upload: {str(e)}")


# ============================================================================
# API - DOCUMENTS (CRUD)
# ============================================================================

@router.get("/api/documents")
async def list_documents(
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session)
):
    """
    Liste tous les flipbooks.

    Args:
        limit: Nombre max de resultats (defaut: 20)
        offset: Decalage pour pagination (defaut: 0)

    Returns:
        Liste des flipbooks avec leurs metadonnees
    """
    # Requete avec chargement des pages pour le count
    statement = (
        select(Flipbook)
        .options(selectinload(Flipbook.pages))
        .order_by(Flipbook.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    flipbooks = session.exec(statement).all()

    return [
        {
            "id": fb.id,
            "title": fb.title,
            "pages": len(fb.pages),
            "thumbnail": f"/pages/{fb.id}/page_1.webp",
            "created_at": fb.created_at.isoformat(),
            "updated_at": fb.updated_at.isoformat(),
        }
        for fb in flipbooks
    ]


@router.get("/api/documents/{doc_id}")
async def get_document(doc_id: str, session: Session = Depends(get_session)):
    """
    Recupere les details d'un flipbook.

    Args:
        doc_id: ID du flipbook

    Returns:
        Details complets du flipbook
    """
    statement = (
        select(Flipbook)
        .where(Flipbook.id == doc_id)
        .options(selectinload(Flipbook.pages))
    )
    flipbook = session.exec(statement).first()

    if not flipbook:
        raise HTTPException(status_code=404, detail="Document non trouve")

    return {
        "id": flipbook.id,
        "title": flipbook.title,
        "pages": len(flipbook.pages),
        "thumbnail": flipbook.thumbnail,
        "created_at": flipbook.created_at.isoformat(),
        "updated_at": flipbook.updated_at.isoformat(),
    }


@router.get("/api/documents/{doc_id}/page/{page_num}")
async def get_page_image(doc_id: str, page_num: int):
    """
    Recupere l'image d'une page.

    Args:
        doc_id: ID du flipbook
        page_num: Numero de la page

    Returns:
        Image WebP de la page
    """
    page_path = settings.PAGES_DIR / doc_id / f"page_{page_num}.webp"

    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Page non trouvee")

    return FileResponse(page_path, media_type="image/webp")


@router.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, session: Session = Depends(get_session)):
    """
    Supprime un flipbook et tous ses fichiers associes.

    Args:
        doc_id: ID du flipbook

    Returns:
        Confirmation de suppression
    """
    flipbook = session.get(Flipbook, doc_id)

    if not flipbook:
        raise HTTPException(status_code=404, detail="Document non trouve")

    pdf_path = flipbook.path_pdf

    # La suppression en cascade est geree par SQLModel (cascade="all, delete-orphan")
    session.delete(flipbook)
    session.commit()

    # Suppression des fichiers
    await pdf_service.delete_flipbook_files(doc_id, pdf_path)

    return {"status": "deleted", "id": doc_id}


# ============================================================================
# API - EDITOR (COMPLET AVEC WIDGETS)
# ============================================================================

@router.get("/api/editor/{doc_id}")
async def get_editor_data(doc_id: str, session: Session = Depends(get_session)):
    """
    Recupere les donnees completes d'un flipbook pour l'editeur.

    Inclut:
    - Informations du flipbook
    - Toutes les pages avec dimensions
    - Tous les widgets de chaque page

    Args:
        doc_id: ID du flipbook

    Returns:
        JSON complet pour l'editeur
    """
    try:
        # Chargement avec toutes les relations
        statement = (
            select(Flipbook)
            .where(Flipbook.id == doc_id)
            .options(
                selectinload(Flipbook.pages).selectinload(Page.widgets)
            )
        )
        flipbook = session.exec(statement).first()

        if not flipbook:
            raise HTTPException(status_code=404, detail="Flipbook non trouve")

        # Construction des donnees des pages
        pages_data = []
        for page in sorted(flipbook.pages, key=lambda p: p.page_num):
            page_dict = {
                "id": page.id,
                "page_num": page.page_num,
                "image_url": f"/pages/{page.image_path}",
                "width": page.width,
                "height": page.height,
                "widgets": [
                    {
                        "id": w.id,
                        "type": w.type,
                        "props": w.props,
                        "geometry": w.geometry,
                        "z_index": w.z_index
                    }
                    for w in sorted(page.widgets, key=lambda w: w.z_index)
                ]
            }
            pages_data.append(page_dict)

        # Ensure style is a dict (not a property that could fail)
        style_data = flipbook.style or {}

        return {
            "flipbook_id": flipbook.id,
            "id": flipbook.id,
            "title": flipbook.title,
            "page_count": len(flipbook.pages),
            "style": style_data,
            "created_at": flipbook.created_at.isoformat(),
            "updated_at": flipbook.updated_at.isoformat(),
            "pages": pages_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_editor_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")


@router.post("/api/editor/{doc_id}/save")
async def save_editor_data(
    doc_id: str,
    data: dict,
    session: Session = Depends(get_session)
):
    """
    Sauvegarde les modifications de l'editeur.

    Strategie: Supprime tous les anciens widgets du flipbook et cree les nouveaux.
    Cela garantit la coherence et evite les orphelins.

    Body JSON attendu:
    {
        "title": "Nouveau titre (optionnel)",
        "pages": [
            {
                "page_num": 1,
                "widgets": [
                    {
                        "type": "link",
                        "props": {"url": "https://...", "target": "_blank"},
                        "geometry": {"x": 100, "y": 200, "width": 150, "height": 80},
                        "z_index": 0
                    },
                    {
                        "type": "video",
                        "props": {"url": "https://youtube.com/...", "autoplay": false},
                        "geometry": {"x": 50, "y": 300, "width": 320, "height": 180},
                        "z_index": 1
                    }
                ]
            }
        ]
    }

    Args:
        doc_id: ID du flipbook
        data: Donnees de l'editeur

    Returns:
        Confirmation avec timestamp
    """
    # Chargement du flipbook avec pages et widgets
    statement = (
        select(Flipbook)
        .where(Flipbook.id == doc_id)
        .options(
            selectinload(Flipbook.pages).selectinload(Page.widgets)
        )
    )
    flipbook = session.exec(statement).first()

    if not flipbook:
        raise HTTPException(status_code=404, detail="Flipbook non trouve")

    # Mise a jour du titre si fourni
    if "title" in data and data["title"]:
        flipbook.title = data["title"]

    # Mise a jour du style si fourni
    if "style" in data and data["style"]:
        flipbook.style_json = json.dumps(data["style"], ensure_ascii=False)

    # Mise a jour du timestamp
    flipbook.updated_at = datetime.utcnow()

    # Traitement des pages et widgets
    if "pages" in data:
        # Creer un dictionnaire page_num -> Page pour acces rapide
        pages_by_num = {p.page_num: p for p in flipbook.pages}

        for page_data in data["pages"]:
            page_num = page_data.get("page_num")
            if not page_num or page_num not in pages_by_num:
                continue

            page = pages_by_num[page_num]

            # Suppression de tous les widgets existants de cette page
            for widget in page.widgets:
                session.delete(widget)

            # Creation des nouveaux widgets
            widgets_data = page_data.get("widgets", [])
            for widget_data in widgets_data:
                widget = Widget(
                    page_id=page.id,
                    type=widget_data.get("type", "link"),
                    props_json=json.dumps(widget_data.get("props", {}), ensure_ascii=False),
                    geometry_json=json.dumps(widget_data.get("geometry", {}), ensure_ascii=False),
                    z_index=widget_data.get("z_index", 0)
                )
                session.add(widget)

    # Commit des changements
    session.add(flipbook)
    session.commit()
    session.refresh(flipbook)

    return {
        "status": "saved",
        "flipbook_id": doc_id,
        "title": flipbook.title,
        "updated_at": flipbook.updated_at.isoformat()
    }


# ============================================================================
# API - WIDGETS (OPERATIONS INDIVIDUELLES)
# ============================================================================

@router.post("/api/editor/{doc_id}/page/{page_num}/widget")
async def add_widget(
    doc_id: str,
    page_num: int,
    widget_data: dict,
    session: Session = Depends(get_session)
):
    """
    Ajoute un widget a une page specifique.

    Body JSON attendu:
    {
        "type": "video",
        "props": {"url": "https://youtube.com/...", "autoplay": false},
        "geometry": {"x": 100, "y": 200, "width": 320, "height": 180},
        "z_index": 1
    }

    Args:
        doc_id: ID du flipbook
        page_num: Numero de la page
        widget_data: Donnees du widget

    Returns:
        Widget cree avec son ID
    """
    # Recherche de la page
    statement = select(Page).where(
        Page.flipbook_id == doc_id,
        Page.page_num == page_num
    )
    page = session.exec(statement).first()

    if not page:
        raise HTTPException(status_code=404, detail="Page non trouvee")

    # Creation du widget
    widget = Widget(
        page_id=page.id,
        type=widget_data.get("type", "link"),
        props_json=json.dumps(widget_data.get("props", {}), ensure_ascii=False),
        geometry_json=json.dumps(widget_data.get("geometry", {}), ensure_ascii=False),
        z_index=widget_data.get("z_index", 0)
    )
    session.add(widget)

    # Mise a jour du timestamp du flipbook
    flipbook = session.get(Flipbook, doc_id)
    if flipbook:
        flipbook.updated_at = datetime.utcnow()
        session.add(flipbook)

    session.commit()
    session.refresh(widget)

    return {
        "status": "created",
        "widget": widget.to_dict()
    }


@router.put("/api/editor/{doc_id}/widget/{widget_id}")
async def update_widget(
    doc_id: str,
    widget_id: int,
    widget_data: dict,
    session: Session = Depends(get_session)
):
    """
    Met a jour un widget existant.

    Args:
        doc_id: ID du flipbook (pour verification)
        widget_id: ID du widget
        widget_data: Nouvelles donnees

    Returns:
        Widget mis a jour
    """
    # Recherche du widget avec verification du flipbook
    statement = (
        select(Widget)
        .join(Page)
        .where(
            Widget.id == widget_id,
            Page.flipbook_id == doc_id
        )
    )
    widget = session.exec(statement).first()

    if not widget:
        raise HTTPException(status_code=404, detail="Widget non trouve")

    # Mise a jour des champs
    if "type" in widget_data:
        widget.type = widget_data["type"]
    if "props" in widget_data:
        widget.props_json = json.dumps(widget_data["props"], ensure_ascii=False)
    if "geometry" in widget_data:
        widget.geometry_json = json.dumps(widget_data["geometry"], ensure_ascii=False)
    if "z_index" in widget_data:
        widget.z_index = widget_data["z_index"]

    session.add(widget)

    # Mise a jour du timestamp du flipbook
    flipbook = session.get(Flipbook, doc_id)
    if flipbook:
        flipbook.updated_at = datetime.utcnow()
        session.add(flipbook)

    session.commit()
    session.refresh(widget)

    return {
        "status": "updated",
        "widget": widget.to_dict()
    }


@router.delete("/api/editor/{doc_id}/widget/{widget_id}")
async def delete_widget(
    doc_id: str,
    widget_id: int,
    session: Session = Depends(get_session)
):
    """
    Supprime un widget.

    Args:
        doc_id: ID du flipbook (pour verification)
        widget_id: ID du widget

    Returns:
        Confirmation de suppression
    """
    # Recherche du widget avec verification du flipbook
    statement = (
        select(Widget)
        .join(Page)
        .where(
            Widget.id == widget_id,
            Page.flipbook_id == doc_id
        )
    )
    widget = session.exec(statement).first()

    if not widget:
        raise HTTPException(status_code=404, detail="Widget non trouve")

    session.delete(widget)

    # Mise a jour du timestamp du flipbook
    flipbook = session.get(Flipbook, doc_id)
    if flipbook:
        flipbook.updated_at = datetime.utcnow()
        session.add(flipbook)

    session.commit()

    return {
        "status": "deleted",
        "widget_id": widget_id
    }


# ============================================================================
# API - READER (DONNEES POUR AFFICHAGE)
# ============================================================================

@router.get("/api/reader/{doc_id}")
async def get_reader_data(doc_id: str, session: Session = Depends(get_session)):
    """
    Recupere les donnees optimisees pour le lecteur de flipbook.

    Inclut toutes les pages et widgets pour un affichage fluide.

    Args:
        doc_id: ID du flipbook

    Returns:
        Donnees completes pour le reader
    """
    statement = (
        select(Flipbook)
        .where(Flipbook.id == doc_id)
        .options(
            selectinload(Flipbook.pages).selectinload(Page.widgets)
        )
    )
    flipbook = session.exec(statement).first()

    if not flipbook:
        raise HTTPException(status_code=404, detail="Flipbook non trouve")

    pages_data = []
    for page in sorted(flipbook.pages, key=lambda p: p.page_num):
        pages_data.append({
            "page_num": page.page_num,
            "image_url": f"/pages/{page.image_path}",
            "width": page.width,
            "height": page.height,
            "widgets": [w.to_dict() for w in page.widgets]
        })

    return {
        "id": flipbook.id,
        "title": flipbook.title,
        "page_count": len(flipbook.pages),
        "style": flipbook.style,
        "pages": pages_data
    }
