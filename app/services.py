import asyncio
import json
from pathlib import Path
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image
import aiofiles
import aiofiles.os

from .config import settings
from .models import Flipbook, Page, Widget, generate_uuid
from .database import Session

# Pool de threads pour les operations CPU-bound (conversion PDF)
executor = ThreadPoolExecutor(max_workers=4)


# ============================================================================
# EXCEPTIONS
# ============================================================================

class PDFConversionError(Exception):
    """Erreur lors de la conversion PDF"""
    pass


class StorageError(Exception):
    """Erreur de stockage fichier"""
    pass


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PageRenderResult:
    """Resultat du rendu d'une page"""
    page_num: int
    image_path: str
    width: int
    height: int
    links: List[dict]


@dataclass
class ConversionResult:
    """Resultat complet de la conversion"""
    doc_id: str
    page_count: int
    pages: List[PageRenderResult]


# ============================================================================
# PDF SERVICE
# ============================================================================

class PDFService:
    """Service de conversion PDF vers flipbook"""

    # Configuration
    DPI: int = 150  # Resolution de rendu
    WEBP_QUALITY: int = 85  # Qualite WebP (0-100)

    @staticmethod
    def generate_id() -> str:
        """Genere un ID unique pour le flipbook"""
        return generate_uuid()

    # -------------------------------------------------------------------------
    # OPERATIONS FICHIER (ASYNC)
    # -------------------------------------------------------------------------

    @staticmethod
    async def save_pdf_async(content: bytes, doc_id: str) -> Path:
        """
        Sauvegarde le PDF uploade de maniere asynchrone.

        Args:
            content: Contenu binaire du PDF
            doc_id: ID du document

        Returns:
            Path vers le fichier sauve
        """
        pdf_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"

        async with aiofiles.open(pdf_path, "wb") as f:
            await f.write(content)

        return pdf_path

    @staticmethod
    async def create_pages_dir(doc_id: str) -> Path:
        """
        Cree le repertoire pour les pages d'un flipbook.

        Args:
            doc_id: ID du document

        Returns:
            Path vers le repertoire cree
        """
        pages_dir = settings.PAGES_DIR / doc_id

        # aiofiles.os.makedirs n'existe pas, on utilise run_in_executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: pages_dir.mkdir(exist_ok=True))

        return pages_dir

    @staticmethod
    async def delete_file_async(path: Path) -> None:
        """Supprime un fichier de maniere asynchrone"""
        if path.exists():
            await aiofiles.os.remove(path)

    @staticmethod
    async def delete_dir_async(path: Path) -> None:
        """Supprime un repertoire et son contenu"""
        import shutil

        loop = asyncio.get_event_loop()
        if path.exists():
            await loop.run_in_executor(None, lambda: shutil.rmtree(path))

    # -------------------------------------------------------------------------
    # EXTRACTION PDF (SYNC - CPU BOUND)
    # -------------------------------------------------------------------------

    @classmethod
    def extract_links_from_page(cls, page: fitz.Page, page_num: int) -> List[dict]:
        """
        Extrait les liens hypertextes d'une page PDF.

        Args:
            page: Page PyMuPDF
            page_num: Numero de la page

        Returns:
            Liste des liens avec leurs coordonnees
        """
        links = []
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                rect = link.get("from", fitz.Rect())
                links.append({
                    "url": uri,
                    "x": round(rect.x0, 2),
                    "y": round(rect.y0, 2),
                    "width": round(rect.width, 2),
                    "height": round(rect.height, 2),
                })
        return links

    @classmethod
    def render_page_to_webp(
        cls,
        page: fitz.Page,
        output_path: Path,
        dpi: int = None,
        quality: int = None
    ) -> Tuple[int, int]:
        """
        Convertit une page PDF en image WebP.

        Args:
            page: Page PyMuPDF
            output_path: Chemin de sortie
            dpi: Resolution (defaut: 150)
            quality: Qualite WebP (defaut: 85)

        Returns:
            Tuple (width, height) de l'image
        """
        dpi = dpi or cls.DPI
        quality = quality or cls.WEBP_QUALITY

        # Calcul de la matrice de zoom
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        # Rendu de la page
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        # Conversion en image Pillow et sauvegarde WebP
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(output_path, "WEBP", quality=quality)

        return pix.width, pix.height

    @classmethod
    def convert_pdf_sync(cls, pdf_path: Path, doc_id: str) -> ConversionResult:
        """
        Convertit un PDF en images WebP (operation synchrone CPU-bound).

        Args:
            pdf_path: Chemin du PDF
            doc_id: ID du document

        Returns:
            ConversionResult avec toutes les pages
        """
        pages_dir = settings.PAGES_DIR / doc_id
        pages_dir.mkdir(exist_ok=True)

        try:
            pdf_doc = fitz.open(pdf_path)
        except Exception as e:
            raise PDFConversionError(f"Impossible d'ouvrir le PDF: {str(e)}")

        pages: List[PageRenderResult] = []

        try:
            for page_idx in range(len(pdf_doc)):
                page = pdf_doc[page_idx]
                page_num = page_idx + 1

                # Chemin de l'image
                image_filename = f"page_{page_num}.webp"
                image_path = pages_dir / image_filename

                # Rendu de la page
                width, height = cls.render_page_to_webp(page, image_path)

                # Extraction des liens
                links = cls.extract_links_from_page(page, page_num)

                pages.append(PageRenderResult(
                    page_num=page_num,
                    image_path=f"{doc_id}/{image_filename}",
                    width=width,
                    height=height,
                    links=links
                ))

            return ConversionResult(
                doc_id=doc_id,
                page_count=len(pdf_doc),
                pages=pages
            )

        except Exception as e:
            raise PDFConversionError(f"Erreur de conversion: {str(e)}")
        finally:
            pdf_doc.close()

    # -------------------------------------------------------------------------
    # TRAITEMENT COMPLET (ASYNC)
    # -------------------------------------------------------------------------

    @classmethod
    async def process_pdf(
        cls,
        content: bytes,
        filename: str,
        custom_title: Optional[str],
        session: Session
    ) -> dict:
        """
        Traite un PDF complet:
        1. Sauvegarde le PDF sur disque
        2. Convertit les pages en WebP
        3. Extrait les liens hypertextes
        4. Cree les entrees en base de donnees

        Args:
            content: Contenu binaire du PDF
            filename: Nom du fichier original
            custom_title: Titre personnalise (optionnel)
            session: Session SQLModel

        Returns:
            dict: Donnees du flipbook cree
        """
        doc_id = cls.generate_id()

        # 1. Sauvegarde du PDF
        pdf_path = await cls.save_pdf_async(content, doc_id)

        try:
            # 2. Cree le repertoire des pages
            await cls.create_pages_dir(doc_id)

            # 3. Conversion PDF (CPU-bound -> executor)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                cls.convert_pdf_sync,
                pdf_path,
                doc_id
            )

            # 4. Titre du flipbook
            title = custom_title or filename.replace(".pdf", "").replace("_", " ").title()

            # 5. Creation du flipbook en base
            flipbook = Flipbook(
                id=doc_id,
                title=title,
                path_pdf=str(pdf_path),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(flipbook)

            # 6. Creation des pages en base
            for page_result in result.pages:
                page = Page(
                    flipbook_id=doc_id,
                    page_num=page_result.page_num,
                    image_path=page_result.image_path,
                    width=page_result.width,
                    height=page_result.height
                )
                session.add(page)
                session.flush()  # Pour obtenir l'ID de la page

                # 7. Creation des widgets pour les liens extraits du PDF
                for link_data in page_result.links:
                    widget = Widget(
                        page_id=page.id,
                        type="link",
                        props_json=json.dumps({
                            "url": link_data["url"],
                            "target": "_blank"
                        }, ensure_ascii=False),
                        geometry_json=json.dumps({
                            "x": link_data["x"],
                            "y": link_data["y"],
                            "width": link_data["width"],
                            "height": link_data["height"]
                        }, ensure_ascii=False),
                        z_index=0
                    )
                    session.add(widget)

            # 8. Commit final
            session.commit()
            session.refresh(flipbook)

            # Retourne les donnees du flipbook avec le nombre de pages
            return {
                "id": flipbook.id,
                "title": flipbook.title,
                "pages": result.page_count,
                "thumbnail": flipbook.thumbnail,
                "created_at": flipbook.created_at.isoformat(),
                "updated_at": flipbook.updated_at.isoformat(),
            }

        except PDFConversionError:
            # Nettoyage en cas d'erreur de conversion
            await cls.delete_file_async(pdf_path)
            await cls.delete_dir_async(settings.PAGES_DIR / doc_id)
            raise

        except Exception as e:
            # Nettoyage en cas d'erreur inattendue
            await cls.delete_file_async(pdf_path)
            await cls.delete_dir_async(settings.PAGES_DIR / doc_id)
            raise PDFConversionError(f"Erreur inattendue: {str(e)}")

    # -------------------------------------------------------------------------
    # SUPPRESSION
    # -------------------------------------------------------------------------

    @classmethod
    async def delete_flipbook_files(cls, doc_id: str, pdf_path: Optional[str] = None) -> None:
        """
        Supprime tous les fichiers associes a un flipbook.

        Args:
            doc_id: ID du flipbook
            pdf_path: Chemin du PDF (optionnel)
        """
        # Suppression du repertoire des pages
        pages_dir = settings.PAGES_DIR / doc_id
        await cls.delete_dir_async(pages_dir)

        # Suppression du PDF
        if pdf_path:
            await cls.delete_file_async(Path(pdf_path))
        else:
            default_pdf = settings.UPLOAD_DIR / f"{doc_id}.pdf"
            await cls.delete_file_async(default_pdf)


# Instance singleton du service
pdf_service = PDFService()
