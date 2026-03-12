"""
Point d'entrée de EPP Tester Platform.

Initialise la base de données SQLite, configure le logger,
lance l'application PyQt6 et gère la fermeture propre.
"""

import signal
import sys

from PyQt6.QtWidgets import QApplication

from src.db.database import init_db
from src.utils.logger import setup_logger


def main() -> None:
    """Lance l'application EPP Tester Platform."""
    # 1. Initialisation du logger
    logger = setup_logger("epp_tester")
    logger.info("Démarrage d'EPP Tester Platform")

    # 2. Initialisation de la base de données SQLite
    try:
        engine = init_db()
        logger.info("Base de données initialisée : %s", engine.url)
    except Exception as exc:
        logger.critical("Impossible d'initialiser la base de données : %s", exc)
        sys.exit(1)

    # 3. Lancement de l'application Qt
    app = QApplication(sys.argv)
    app.setApplicationName("EPP Tester Platform")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("NIC-MG")

    # Gestion de SIGINT (Ctrl+C terminal) pour fermeture propre
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    from src.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    logger.info("Interface graphique lancée")
    exit_code = app.exec()
    logger.info("EPP Tester Platform fermé (code=%d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
