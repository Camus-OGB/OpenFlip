from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import json


class Flipbook(SQLModel, table=True):
    """Table principale des flipbooks"""
    
    id: str = Field(primary_key=True)
    title: str
    path: str = Field(default="")
    page_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    flipbook_pages: List["Page"] = Relationship(back_populates="flipbook")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "pages": self.page_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Page(SQLModel, table=True):
    """Table des pages avec métadonnées"""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    flipbook_id: str = Field(foreign_key="flipbook.id", index=True)
    page_number: int = Field(index=True)
    image_path: str = Field(default="")
    metadata_json: str = Field(default="{}")
    
    flipbook: Optional[Flipbook] = Relationship(back_populates="flipbook_pages")
    
    def get_metadata(self) -> dict:
        """Parse le JSON des métadonnées"""
        try:
            return json.loads(self.metadata_json)
        except json.JSONDecodeError:
            return {}
    
    def set_metadata(self, value: dict):
        """Sérialise les métadonnées en JSON"""
        self.metadata_json = json.dumps(value, ensure_ascii=False)
    
    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "image_path": self.image_path,
            "metadata": self.get_metadata(),
        }


class EditorData(SQLModel):
    """Schéma pour les données de l'éditeur (non persisté)"""
    flipbook_id: str
    title: str
    pages: List[dict]


class LinkMetadata(SQLModel):
    """Schéma pour un lien hypertexte extrait"""
    x: float
    y: float
    width: float
    height: float
    url: str
    page_number: int


class PageMetadata(SQLModel):
    """Schéma pour les métadonnées d'une page"""
    links: List[LinkMetadata] = []
    text: str = ""
    custom_elements: List[dict] = []
