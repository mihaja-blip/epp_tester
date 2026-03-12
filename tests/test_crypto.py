"""Tests du module de chiffrement des credentials EPP."""

import pytest
from src.security.crypto import CredentialManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """Crée un CredentialManager isolé avec une clé temporaire."""
    # Redirige le fichier de clé vers le répertoire temporaire
    import src.security.crypto as crypto_module
    monkeypatch.setattr(crypto_module, "KEY_FILE", tmp_path / ".epp_key_test")
    return CredentialManager()


class TestCredentialManager:
    def test_encrypt_returns_non_empty_string(self, manager):
        token = manager.encrypt("secret_password")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_encrypt_does_not_store_plaintext(self, manager):
        token = manager.encrypt("secret_password")
        assert "secret_password" not in token

    def test_round_trip_simple(self, manager):
        plaintext = "MyP@ssw0rd!"
        assert manager.decrypt(manager.encrypt(plaintext)) == plaintext

    def test_round_trip_unicode(self, manager):
        plaintext = "pâssw0rd_éàü_日本語"
        assert manager.decrypt(manager.encrypt(plaintext)) == plaintext

    def test_round_trip_long_password(self, manager):
        plaintext = "A" * 512
        assert manager.decrypt(manager.encrypt(plaintext)) == plaintext

    def test_encrypt_empty_returns_empty(self, manager):
        assert manager.encrypt("") == ""

    def test_decrypt_empty_returns_empty(self, manager):
        assert manager.decrypt("") == ""

    def test_two_encryptions_differ(self, manager):
        """Fernet génère un IV aléatoire — deux chiffrements du même texte diffèrent."""
        t1 = manager.encrypt("same_password")
        t2 = manager.encrypt("same_password")
        assert t1 != t2

    def test_two_managers_share_key(self, tmp_path, monkeypatch):
        """Deux instances avec la même clé peuvent déchiffrer mutuellement."""
        import src.security.crypto as crypto_module
        key_path = tmp_path / ".epp_key_shared"
        monkeypatch.setattr(crypto_module, "KEY_FILE", key_path)
        m1 = CredentialManager()
        token = m1.encrypt("shared_secret")
        # Recrée une instance — doit charger la même clé depuis le fichier
        m2 = CredentialManager()
        assert m2.decrypt(token) == "shared_secret"
