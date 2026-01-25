from sqlmodel import SQLModel, create_engine, Session
from .config import settings

DATABASE_URL = f"sqlite:///{settings.STORAGE_DIR}/openflip.db"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def init_db():
    """Crée les tables si elles n'existent pas"""
    SQLModel.metadata.create_all(engine, checkfirst=True)

def get_session():
    """Générateur de session pour les dépendances FastAPI"""
    with Session(engine) as session:
        yield session
