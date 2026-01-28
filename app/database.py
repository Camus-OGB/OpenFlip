from sqlmodel import SQLModel, create_engine, Session
from contextlib import contextmanager
from typing import Generator
import os

from .config import settings

# ============================================================================
# CONFIGURATION DATABASE
# ============================================================================

# Détection automatique du mode Production vs Local
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Mode Production : utilise PostgreSQL via la variable DATABASE_URL
    # Correction critique pour SQLAlchemy >= 2.0 : 
    # Render fournit postgres://, mais SQLAlchemy requiert postgresql://
    database_url = database_url.replace("postgres://", "postgresql://")
    DATABASE_URL = database_url
else:
    # Mode Local : utilise SQLite
    DATABASE_URL = f"sqlite:///{settings.STORAGE_DIR}/openflip.db"

# Déterminer les arguments de connexion selon la base de données
if database_url and "postgresql://" in DATABASE_URL:
    # PostgreSQL
    connect_args = {}
    pool_pre_ping = True  # Vérifie la connexion avant chaque requête
else:
    # SQLite
    connect_args = {
        "check_same_thread": False,  # Permet l'acces multi-thread pour FastAPI
        "timeout": 30  # Timeout de 30 secondes pour les locks
    }
    pool_pre_ping = False

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=pool_pre_ping
)


# ============================================================================
# INITIALISATION
# ============================================================================

def init_db():
    """
    Cree toutes les tables si elles n'existent pas.
    Appele au demarrage de l'application.
    """
    # Import des modeles pour que SQLModel les connaisse
    from .models import Flipbook, Page, Widget  # noqa: F401

    try:
        SQLModel.metadata.create_all(engine, checkfirst=True)
    except Exception as e:
        # Si la table existe mais avec un schéma différent, on ignore l'erreur
        # C'est une situation de migration qui nécessite un script SQL manuel
        print(f"Warning: Database schema issue: {e}")
        print("If you need to update the schema, you may need to delete the database and recreate it.")


def drop_db():
    """
    Supprime toutes les tables (utile pour les tests).
    ATTENTION: Perte de donnees!
    """
    SQLModel.metadata.drop_all(engine)


# ============================================================================
# SESSIONS
# ============================================================================

def get_session() -> Generator[Session, None, None]:
    """
    Generateur de session pour les dependances FastAPI.

    Usage:
        @router.get("/api/example")
        async def example(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


@contextmanager
def get_session_context() -> Generator[Session, None, None]:
    """
    Context manager pour utilisation hors FastAPI.

    Usage:
        with get_session_context() as session:
            flipbook = session.get(Flipbook, "abc123")
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================================
# HELPERS
# ============================================================================

def execute_with_session(func):
    """
    Decorateur pour executer une fonction avec une session.

    Usage:
        @execute_with_session
        def create_flipbook(session: Session, title: str):
            flipbook = Flipbook(title=title)
            session.add(flipbook)
            return flipbook
    """
    def wrapper(*args, **kwargs):
        with get_session_context() as session:
            return func(session, *args, **kwargs)
    return wrapper
