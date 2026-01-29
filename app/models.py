from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import json
import uuid


def generate_uuid() -> str:
    """Genere un UUID court (8 caracteres)"""
    return str(uuid.uuid4())[:8]


def generate_share_token() -> str:
    """Genere un token de partage unique"""
    import secrets
    return secrets.token_urlsafe(24)


# ============================================================================
# TABLE FLIPBOOK
# ============================================================================

class Flipbook(SQLModel, table=True):
    """Table principale des flipbooks"""

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    title: str = Field(index=True)
    path_pdf: str = Field(default="")  # Chemin vers le PDF original
    style_json: str = Field(default="{}")  # Configuration de style (JSON)
    share_token: str = Field(default_factory=generate_share_token, index=True)  # Token de partage unique
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relations
    pages: List["Page"] = Relationship(
        back_populates="flipbook",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @property
    def page_count(self) -> int:
        return len(self.pages) if self.pages else 0

    @property
    def thumbnail(self) -> str:
        return f"/pages/{self.id}/page_1.webp"

    @property
    def style(self) -> dict:
        try:
            return json.loads(self.style_json) if self.style_json else {}
        except json.JSONDecodeError:
            return {}

    @style.setter
    def style(self, value: dict):
        self.style_json = json.dumps(value, ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "pages": self.page_count,
            "thumbnail": self.thumbnail,
            "style": self.style,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ============================================================================
# TABLE PAGE
# ============================================================================

class Page(SQLModel, table=True):
    """Table des pages avec dimensions"""

    id: Optional[int] = Field(default=None, primary_key=True)
    flipbook_id: str = Field(foreign_key="flipbook.id", index=True)
    page_num: int = Field(index=True)
    image_path: str  # Chemin relatif: "{flipbook_id}/page_{num}.webp"
    width: int = Field(default=0)
    height: int = Field(default=0)

    # Relations
    flipbook: Optional[Flipbook] = Relationship(back_populates="pages")
    widgets: List["Widget"] = Relationship(
        back_populates="page",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "page_num": self.page_num,
            "image_url": f"/pages/{self.image_path}",
            "width": self.width,
            "height": self.height,
            "widgets": [w.to_dict() for w in self.widgets] if self.widgets else []
        }


# ============================================================================
# TABLE WIDGET
# ============================================================================

class Widget(SQLModel, table=True):
    """
    Table des widgets interactifs (videos, liens, hotspots, etc.)

    Types supportes:
    - "link": Lien hypertexte
    - "video": Video YouTube/Vimeo embedded
    - "audio": Fichier audio
    - "hotspot": Zone cliquable
    - "image": Image superposee
    - "text": Zone de texte
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    page_id: int = Field(foreign_key="page.id", index=True)
    type: str = Field(index=True)  # "link", "video", "audio", "hotspot", "image", "text"

    # Proprietes du widget (JSON)
    # Ex: {"url": "https://...", "title": "Mon lien", "target": "_blank"}
    props_json: str = Field(default="{}")

    # Geometrie/Position (JSON)
    # Ex: {"x": 100, "y": 200, "width": 150, "height": 80, "rotation": 0}
    geometry_json: str = Field(default="{}")

    # Ordre d'affichage (z-index)
    z_index: int = Field(default=0)

    # Relation
    page: Optional[Page] = Relationship(back_populates="widgets")

    @property
    def props(self) -> dict:
        try:
            return json.loads(self.props_json)
        except json.JSONDecodeError:
            return {}

    @props.setter
    def props(self, value: dict):
        self.props_json = json.dumps(value, ensure_ascii=False)

    @property
    def geometry(self) -> dict:
        try:
            return json.loads(self.geometry_json)
        except json.JSONDecodeError:
            return {}

    @geometry.setter
    def geometry(self, value: dict):
        self.geometry_json = json.dumps(value, ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "props": self.props,
            "geometry": self.geometry,
            "z_index": self.z_index
        }

    @classmethod
    def from_dict(cls, page_id: int, data: dict) -> "Widget":
        """Cree un Widget depuis un dictionnaire"""
        return cls(
            page_id=page_id,
            type=data.get("type", "link"),
            props_json=json.dumps(data.get("props", {}), ensure_ascii=False),
            geometry_json=json.dumps(data.get("geometry", {}), ensure_ascii=False),
            z_index=data.get("z_index", 0)
        )


# ============================================================================
# SCHEMAS PYDANTIC (pour validation)
# ============================================================================

class WidgetCreate(SQLModel):
    """Schema pour creer un widget"""
    type: str
    props: dict = {}
    geometry: dict = {}
    z_index: int = 0


class PageUpdate(SQLModel):
    """Schema pour mettre a jour une page"""
    page_num: int
    widgets: List[WidgetCreate] = []


class EditorSaveRequest(SQLModel):
    """Schema pour la requete de sauvegarde editeur"""
    title: Optional[str] = None
    pages: List[PageUpdate] = []


class FlipbookResponse(SQLModel):
    """Schema de reponse flipbook"""
    id: str
    title: str
    pages: int
    thumbnail: str
    created_at: str
    updated_at: str
