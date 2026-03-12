"""
Logger centralisé pour EPP Tester Platform.

- Handler console (niveau INFO+)
- Handler fichier rotatif epp_tester.log (niveau DEBUG+)
- mask_sensitive() : masque automatiquement les credentials dans les trames XML
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path("epp_tester.log")
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 Mo par fichier
LOG_BACKUP_COUNT = 3

# Balises XML contenant des credentials à masquer
_SENSITIVE_TAGS = ["pw", "newPW"]
# Masque utilisé à la place des credentials
_MASK = "••••••••"

# Regex compilées pour chaque balise sensible
_SENSITIVE_PATTERNS = [
    re.compile(
        rf"(<{tag}(?:\s[^>]*)?>)([^<]*)(</{tag}>)",
        re.IGNORECASE | re.DOTALL,
    )
    for tag in _SENSITIVE_TAGS
]

# Regex pour <authInfo><pw>...</pw></authInfo>
_AUTH_INFO_PATTERN = re.compile(
    r"(<authInfo\s*>.*?<pw(?:\s[^>]*)?>)([^<]*)(</pw>.*?</authInfo>)",
    re.IGNORECASE | re.DOTALL,
)


def mask_sensitive(xml: str) -> str:
    """Remplace le contenu des balises sensibles par un masque.

    Traite les balises :
    - <pw>...</pw>
    - <newPW>...</newPW>
    - <authInfo><pw>...</pw></authInfo>

    Args:
        xml: trame XML EPP brute

    Returns:
        XML avec les credentials remplacés par '••••••••'.
    """
    if not xml:
        return xml

    # Masque <authInfo><pw>...</pw></authInfo> en priorité
    result = _AUTH_INFO_PATTERN.sub(rf"\g<1>{_MASK}\g<3>", xml)

    # Masque les autres balises sensibles
    for pattern in _SENSITIVE_PATTERNS:
        result = pattern.sub(rf"\g<1>{_MASK}\g<3>", result)

    return result


def setup_logger(name: str = "epp_tester", log_file: Path = LOG_FILE) -> logging.Logger:
    """Configure et retourne le logger applicatif.

    Args:
        name: nom du logger (défaut : 'epp_tester')
        log_file: chemin du fichier de log rotatif

    Returns:
        Logger configuré avec handlers console et fichier.
    """
    logger = logging.getLogger(name)

    # Eviter la duplication des handlers lors d'appels multiples
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Format commun
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler console : INFO+
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    # Handler fichier rotatif : DEBUG+
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "epp_tester") -> logging.Logger:
    """Retourne le logger applicatif (le crée s'il n'existe pas encore)."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
