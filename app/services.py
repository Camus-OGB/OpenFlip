import uuid
import json
import asyncio
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image
import io

from .config import settings
from .models import Flipbook, Page
from .database import get_session, Session

executor = ThreadPoolExecutor(max_workers=4)


class PDFConversionError(Exception):
    """Erreur lors de la conversion PDF"""
    pass


class PDFService:
    
    @staticmethod
    def generate_id() -> str:
        """Génère un ID unique pour le flipbook"""
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    async def save_pdf(content: bytes, doc_id: str) -> Path:
        """Sauvegarde le PDF uploadé"""
        pdf_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"
        
        def _write():
            with open(pdf_path, "wb") as f:
                f.write(content)
            return pdf_path
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _write)
    
    @staticmethod
    def extract_links_from_page(page: fitz.Page, page_number: int) -> List[dict]:
        """Extrait les liens hypertextes d'une page PDF"""
        links = []
        for link in page.get_links():
            if link.get("uri"):
                rect = link.get("from", fitz.Rect())
                links.append({
                    "x": round(rect.x0, 2),
                    "y": round(rect.y0, 2),
                    "width": round(rect.width, 2),
                    "height": round(rect.height, 2),
                    "url": link["uri"],
                    "page_number": page_number
                })
        return links
    
    @staticmethod
    def extract_text_from_page(page: fitz.Page) -> str:
        """Extrait le texte brut d'une page PDF"""
        try:
            return page.get_text("text").strip()
        except Exception:
            return ""
    
    @staticmethod
    def render_page_to_webp(page: fitz.Page, output_path: Path, dpi: int = 150, quality: int = 85):
        """Convertit une page PDF en image WebP haute qualité"""
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(output_path, "WEBP", quality=quality)
    
    @classmethod
    def convert_pdf_with_metadata(cls, pdf_path: Path, doc_id: str) -> Tuple[int, List[dict]]:
        """
        Convertit un PDF en images WebP et extrait les métadonnées.
        
        Returns:
            Tuple[int, List[dict]]: (nombre de pages, liste des métadonnées par page)
        """
        doc_pages_dir = settings.PAGES_DIR / doc_id
        doc_pages_dir.mkdir(exist_ok=True)
        
        try:
            pdf_doc = fitz.open(pdf_path)
        except Exception as e:
            raise PDFConversionError(f"Impossible d'ouvrir le PDF: {str(e)}")
        
        pages_metadata = []
        
        try:
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                page_number = page_num + 1
                
                image_path = doc_pages_dir / f"page_{page_number}.webp"
                cls.render_page_to_webp(page, image_path)
                
                links = cls.extract_links_from_page(page, page_number)
                text = cls.extract_text_from_page(page)
                
                page_metadata = {
                    "page_number": page_number,
                    "image_path": f"{doc_id}/page_{page_number}.webp",
                    "metadata": {
                        "links": links,
                        "text": text,
                        "custom_elements": []
                    }
                }
                pages_metadata.append(page_metadata)
            
            return len(pdf_doc), pages_metadata
            
        except Exception as e:
            raise PDFConversionError(f"Erreur lors de la conversion: {str(e)}")
        finally:
            pdf_doc.close()
    
    @staticmethod
    def cleanup(pdf_path: Path):
        """Supprime le fichier PDF temporaire"""
        if pdf_path.exists():
            pdf_path.unlink()
    
    @classmethod
    async def process_pdf(cls, content: bytes, filename: str, custom_title: str = None, session: Session = None) -> dict:
        """
        Traite un PDF complet: sauvegarde, conversion, extraction métadonnées, stockage en DB.
        
        Args:
            content: Contenu binaire du PDF
            filename: Nom du fichier original
            custom_title: Titre personnalisé (optionnel)
            session: Session SQLModel
            
        Returns:
            dict: Données du flipbook créé
        """
        doc_id = cls.generate_id()
        pdf_path = await cls.save_pdf(content, doc_id)
        
        try:
            loop = asyncio.get_event_loop()
            page_count, pages_metadata = await loop.run_in_executor(
                executor, 
                cls.convert_pdf_with_metadata, 
                pdf_path, 
                doc_id
            )
            
            title = custom_title if custom_title else filename.replace(".pdf", "").replace("_", " ")
            
            flipbook = Flipbook(
                id=doc_id,
                title=title,
                path=str(settings.PAGES_DIR / doc_id),
                page_count=page_count,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(flipbook)
            
            for page_data in pages_metadata:
                page = Page(
                    flipbook_id=doc_id,
                    page_number=page_data["page_number"],
                    image_path=page_data["image_path"],
                    metadata_json=json.dumps(page_data["metadata"], ensure_ascii=False)
                )
                session.add(page)
            
            session.commit()
            session.refresh(flipbook)
            
            return flipbook.to_dict()
            
        except PDFConversionError:
            cls.cleanup(pdf_path)
            raise
        except Exception as e:
            cls.cleanup(pdf_path)
            raise PDFConversionError(f"Erreur inattendue: {str(e)}")


pdf_service = PDFService()
