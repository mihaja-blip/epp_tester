"""
Modèles SQLAlchemy pour EPP Tester Platform.

- EppProfile  : profil de connexion à un serveur EPP
- SessionLog  : historique des commandes/réponses EPP
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class EppProfile(Base):
    """Profil de connexion EPP — credentials stockés chiffrés."""

    __tablename__ = "epp_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=700)
    login: Mapped[str] = mapped_column(String(100), nullable=False)
    # Mot de passe chiffré via CredentialManager — jamais en clair
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    tls_cert_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tls_key_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Environnement : 'production' ou 'sandbox'
    environment: Mapped[str] = mapped_column(String(20), nullable=False, default="sandbox")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Tags séparés par virgule, ex: "nic-mg,test,critical"
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relation vers les logs de session
    session_logs: Mapped[list["SessionLog"]] = relationship(
        "SessionLog", back_populates="profile", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EppProfile id={self.id} name={self.name!r} host={self.host}:{self.port}>"


class SessionLog(Base):
    """Historique des commandes EPP envoyées et réponses reçues."""

    __tablename__ = "session_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("epp_profiles.id", ondelete="SET NULL"), nullable=True
    )
    command_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # XML brut — les credentials sont masqués avant insertion
    xml_request: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    xml_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    return_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    operator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    profile: Mapped[Optional["EppProfile"]] = relationship(
        "EppProfile", back_populates="session_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<SessionLog id={self.id} cmd={self.command_type!r} "
            f"code={self.return_code} ts={self.timestamp}>"
        )
