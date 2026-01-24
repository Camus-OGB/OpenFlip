import uuid
from pathlib import Path
from pdf2image import convert_from_path
from .config import settings
from .models import documents

class PDFService:
    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def save_pdf(content: bytes, doc_id: str) -> Path:
        pdf_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(content)
        return pdf_path
    
    @staticmethod
    def convert_to_images(pdf_path: Path, doc_id: str) -> int:
        doc_pages_dir = settings.PAGES_DIR / doc_id
        doc_pages_dir.mkdir(exist_ok=True)
        
        images = convert_from_path(pdf_path, dpi=150, fmt="webp")
        
        for i, image in enumerate(images, 1):
            image_path = doc_pages_dir / f"page_{i}.webp"
            image.save(image_path, "WEBP", quality=85)
        
        return len(images)
    
    @staticmethod
    def cleanup(pdf_path: Path):
        if pdf_path.exists():
            pdf_path.unlink()

    @classmethod
    def process_pdf(cls, content: bytes, filename: str) -> dict:
        doc_id = cls.generate_id()
        pdf_path = cls.save_pdf(content, doc_id)
        
        try:
            pages = cls.convert_to_images(pdf_path, doc_id)
            title = filename.replace(".pdf", "")
            return documents.add(doc_id, title, pages)
        except Exception as e:
            cls.cleanup(pdf_path)
            raise e

pdf_service = PDFService()
