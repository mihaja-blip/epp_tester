"""
Chiffrement des credentials EPP avec Fernet (AES-256-CBC + HMAC-SHA256).
La clé est dérivée via PBKDF2HMAC et stockée localement dans .epp_key.
"""

import os
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from src.utils.paths import get_app_data_dir

# Fichier de stockage de la clé dérivée dans %APPDATA% (jamais dans le répertoire courant)
KEY_FILE = get_app_data_dir() / ".epp_key"
# Sel fixe pour la dérivation PBKDF2 — non secret, sert uniquement
# à différencier les clés entre installations
_SALT = b"epp_tester_salt_v1"
# Passphrase d'application (peut être surchargée via variable d'env)
_APP_PASSPHRASE = os.environ.get("EPP_KEY_PASSPHRASE", "epp_tester_default_v1").encode()


def _derive_key(passphrase: bytes = _APP_PASSPHRASE, salt: bytes = _SALT) -> bytes:
    """Dérive une clé Fernet 32 bytes via PBKDF2HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase))


def _load_or_create_key() -> bytes:
    """Charge la clé depuis .epp_key ou en génère une nouvelle."""
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes().strip()
    key = _derive_key()
    KEY_FILE.write_bytes(key)
    # Protège le fichier en lecture seule pour l'utilisateur courant
    KEY_FILE.chmod(0o600)
    return key


class CredentialManager:
    """Gestionnaire de chiffrement symétrique des credentials EPP.

    Utilise Fernet (AES-256-CBC + HMAC-SHA256) avec une clé
    dérivée de la passphrase applicative via PBKDF2HMAC.
    """

    def __init__(self) -> None:
        key = _load_or_create_key()
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Chiffre une chaîne et retourne le token base64url Fernet."""
        if not plaintext:
            return ""
        token: bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Déchiffre un token Fernet et retourne le texte clair."""
        if not ciphertext:
            return ""
        plaintext: bytes = self._fernet.decrypt(ciphertext.encode("ascii"))
        return plaintext.decode("utf-8")
