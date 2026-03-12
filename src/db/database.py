"""
Initialisation de la base de données SQLite via SQLAlchemy.
Fournit l'engine, la session factory et la fonction d'init.
"""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base
from src.utils.paths import get_app_data_dir

# Base SQLite dans %APPDATA%/EPP_Tester_Platform/ — persiste entre les sessions
DB_PATH = get_app_data_dir() / "epp_tester.db"
_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def init_db(db_path: Path = DB_PATH) -> Engine:
    """Initialise l'engine SQLite et crée toutes les tables si nécessaire.

    Args:
        db_path: chemin vers le fichier SQLite (défaut : epp_tester.db)

    Returns:
        L'engine SQLAlchemy configuré.
    """
    global _engine, _SessionLocal

    url = f"sqlite:///{db_path}"
    _engine = create_engine(url, connect_args={"check_same_thread": False})
    # Crée les tables définies dans models.py si elles n'existent pas
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_engine() -> Engine:
    """Retourne l'engine courant (init_db doit avoir été appelé)."""
    if _engine is None:
        raise RuntimeError("Base de données non initialisée — appelez init_db() d'abord.")
    return _engine


def get_session() -> Session:
    """Retourne une nouvelle session SQLAlchemy."""
    if _SessionLocal is None:
        raise RuntimeError("Base de données non initialisée — appelez init_db() d'abord.")
    return _SessionLocal()


def session_scope() -> Generator[Session, None, None]:
    """Context manager pour une session avec commit/rollback automatique.

    Usage::
        with session_scope() as session:
            session.add(profile)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
