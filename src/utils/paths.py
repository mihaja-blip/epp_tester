"""
Gestion des chemins de données applicatives.

En développement (venv actif) : fichiers dans le répertoire courant.
En production (exe PyInstaller) : fichiers dans %APPDATA%/EPP_Tester_Platform/.
"""

import os
import sys
from pathlib import Path

APP_NAME = "EPP_Tester_Platform"


def get_app_data_dir() -> Path:
    """Retourne le répertoire de données de l'application, le crée si nécessaire.

    - Windows : %APPDATA%/EPP_Tester_Platform/
    - Linux/macOS : ~/.local/share/EPP_Tester_Platform/

    Returns:
        Chemin absolu vers le répertoire de données.
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        xdg = os.environ.get("XDG_DATA_HOME", "")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"

    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def is_frozen() -> bool:
    """Retourne True si l'application tourne en tant qu'exe PyInstaller."""
    return getattr(sys, "frozen", False)
