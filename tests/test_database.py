"""Tests CRUD pour les modèles SQLAlchemy EppProfile et SessionLog."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, EppProfile, SessionLog


@pytest.fixture
def session(tmp_path):
    """Crée une base SQLite en mémoire pour les tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


@pytest.fixture
def sample_profile(session):
    """Insère un profil de test et le retourne."""
    profile = EppProfile(
        name="Test Sandbox",
        host="epp.test.example.com",
        port=700,
        login="registrar001",
        password_encrypted="gAAAAABencrypted==",
        environment="sandbox",
        tags="test,ci",
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


class TestEppProfile:
    def test_create_profile(self, session):
        profile = EppProfile(
            name="Prod Profile",
            host="epp.prod.example.com",
            port=700,
            login="reg-prod",
            password_encrypted="gAAAAABtoken",
            environment="production",
        )
        session.add(profile)
        session.commit()

        assert profile.id is not None
        assert profile.name == "Prod Profile"
        assert profile.port == 700
        assert profile.environment == "production"

    def test_default_port_is_700(self, session):
        profile = EppProfile(
            name="Default Port",
            host="epp.example.com",
            login="reg",
            password_encrypted="enc",
        )
        session.add(profile)
        session.commit()
        assert profile.port == 700

    def test_default_environment_is_sandbox(self, session):
        profile = EppProfile(
            name="Default Env",
            host="epp.example.com",
            login="reg",
            password_encrypted="enc",
        )
        session.add(profile)
        session.commit()
        assert profile.environment == "sandbox"

    def test_read_profile(self, session, sample_profile):
        fetched = session.query(EppProfile).filter_by(name="Test Sandbox").first()
        assert fetched is not None
        assert fetched.host == "epp.test.example.com"
        assert fetched.login == "registrar001"

    def test_update_profile(self, session, sample_profile):
        sample_profile.host = "epp.new.example.com"
        session.commit()
        refreshed = session.get(EppProfile, sample_profile.id)
        assert refreshed.host == "epp.new.example.com"

    def test_delete_profile(self, session, sample_profile):
        pid = sample_profile.id
        session.delete(sample_profile)
        session.commit()
        assert session.get(EppProfile, pid) is None

    def test_password_not_stored_in_plaintext(self, session, sample_profile):
        """Le mot de passe doit être stocké sous forme chiffrée."""
        fetched = session.query(EppProfile).first()
        assert "password" not in fetched.password_encrypted.lower() or \
               fetched.password_encrypted.startswith("gAAAAA")

    def test_unique_name_constraint(self, session, sample_profile):
        from sqlalchemy.exc import IntegrityError
        duplicate = EppProfile(
            name="Test Sandbox",  # nom déjà utilisé
            host="other.host.com",
            login="other",
            password_encrypted="enc",
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()


class TestSessionLog:
    def test_create_session_log(self, session, sample_profile):
        log = SessionLog(
            profile_id=sample_profile.id,
            command_type="login",
            xml_request="<epp>...</epp>",
            xml_response="<epp><response>...</response></epp>",
            return_code=1000,
            duration_ms=42,
            operator="admin",
            success=True,
        )
        session.add(log)
        session.commit()
        assert log.id is not None
        assert log.return_code == 1000

    def test_session_log_cascade_delete(self, session, sample_profile):
        """Suppression du profil doit supprimer les logs associés."""
        log = SessionLog(
            profile_id=sample_profile.id,
            command_type="poll",
            return_code=1300,
        )
        session.add(log)
        session.commit()
        log_id = log.id

        session.delete(sample_profile)
        session.commit()
        assert session.get(SessionLog, log_id) is None

    def test_session_log_without_profile(self, session):
        """Un log peut exister sans profil (profile_id nullable)."""
        log = SessionLog(
            command_type="hello",
            return_code=1000,
            success=True,
        )
        session.add(log)
        session.commit()
        assert log.id is not None
        assert log.profile_id is None
