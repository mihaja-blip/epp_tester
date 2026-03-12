"""
Dialogue de création/édition d'un profil de connexion EPP.

Permet de saisir les paramètres de connexion, de tester la connexion
et de sauvegarder le profil (mot de passe chiffré) en SQLite.
"""

import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.logger import get_logger

logger = get_logger("epp_tester.ui.profile_dialog")


class _ConnectionTestSignals(QObject):
    """Signaux Qt pour remonter le résultat du test de connexion (thread-safe)."""
    success = pyqtSignal(str)
    failure = pyqtSignal(str)


class ProfileDialog(QDialog):
    """Dialogue de création d'un profil de connexion EPP."""

    def __init__(self, parent=None, profile_id: Optional[int] = None) -> None:
        super().__init__(parent)
        self._profile_id = profile_id  # None = nouveau profil
        self._signals = _ConnectionTestSignals()
        self._signals.success.connect(self._on_test_success)
        self._signals.failure.connect(self._on_test_failure)

        self.setWindowTitle("Nouveau profil de connexion EPP")
        self.setMinimumWidth(520)
        self.setModal(True)

        self._build_ui()
        self._connect_signals()

        if profile_id is not None:
            self._load_profile(profile_id)

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construit tous les widgets du dialogue."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # --- Groupe Identification ---
        id_group = QGroupBox("Identification")
        id_form = QFormLayout(id_group)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("ex : Production NIC-MG")
        id_form.addRow("Nom du profil *", self._name_edit)

        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("ex : epp.nic.mg")
        id_form.addRow("Hôte EPP *", self._host_edit)

        self._port_edit = QLineEdit("700")
        self._port_edit.setValidator(QIntValidator(1, 65535))
        self._port_edit.setMaximumWidth(80)
        id_form.addRow("Port *", self._port_edit)

        self._login_edit = QLineEdit()
        self._login_edit.setPlaceholderText("Identifiant registrar")
        id_form.addRow("Login *", self._login_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText("Mot de passe EPP")
        id_form.addRow("Mot de passe *", self._password_edit)

        main_layout.addWidget(id_group)

        # --- Groupe TLS ---
        tls_group = QGroupBox("Certificats TLS (optionnel)")
        tls_form = QFormLayout(tls_group)

        self._cert_edit, cert_row = self._build_file_row("Parcourir…", "*.pem *.crt *.cer")
        tls_form.addRow("Certificat client", cert_row)

        self._key_edit, key_row = self._build_file_row("Parcourir…", "*.pem *.key")
        tls_form.addRow("Clé privée", key_row)

        main_layout.addWidget(tls_group)

        # --- Groupe Environnement ---
        env_group = QGroupBox("Configuration")
        env_form = QFormLayout(env_group)

        self._env_combo = QComboBox()
        self._env_combo.addItem("Sandbox", "sandbox")
        self._env_combo.addItem("Production", "production")
        env_form.addRow("Environnement", self._env_combo)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("ex : nic-mg, test, registrar")
        env_form.addRow("Tags (séparés par virgule)", self._tags_edit)

        main_layout.addWidget(env_group)

        # --- Test de connexion ---
        test_group = QGroupBox("Test de connexion")
        test_layout = QVBoxLayout(test_group)

        self._test_btn = QPushButton("Tester la connexion")
        self._test_btn.setToolTip("Envoie un <hello> EPP pour vérifier l'accessibilité")
        test_layout.addWidget(self._test_btn)

        self._test_result_label = QLabel("")
        self._test_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._test_result_label.setFont(QFont("Segoe UI", 9))
        self._test_result_label.setWordWrap(True)
        test_layout.addWidget(self._test_result_label)

        main_layout.addWidget(test_group)

        # --- Champs obligatoires légende ---
        note = QLabel("* Champs obligatoires")
        note.setStyleSheet("color: #888;")
        main_layout.addWidget(note)

        # --- Boutons Annuler / Sauvegarder ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Sauvegarder")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def _build_file_row(self, btn_label: str, file_filter: str) -> tuple[QLineEdit, QWidget]:
        """Crée une ligne avec QLineEdit + bouton Parcourir.

        Returns:
            (line_edit, container_widget)
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Chemin vers le fichier…")
        layout.addWidget(line_edit)

        btn = QPushButton(btn_label)
        btn.setMaximumWidth(90)
        btn.clicked.connect(lambda: self._browse_file(line_edit, file_filter))
        layout.addWidget(btn)

        return line_edit, container

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._test_btn.clicked.connect(self._on_test_connection)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse_file(self, target: QLineEdit, file_filter: str) -> None:
        """Ouvre un sélecteur de fichier et remplit le champ cible."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier",
            str(Path.home()),
            f"Fichiers ({file_filter});;Tous les fichiers (*)",
        )
        if path:
            target.setText(path)

    def _on_test_connection(self) -> None:
        """Lance le test de connexion EPP dans un thread séparé."""
        host = self._host_edit.text().strip()
        port_str = self._port_edit.text().strip()

        if not host or not port_str:
            self._test_result_label.setText("Hôte et port requis pour tester la connexion.")
            self._test_result_label.setStyleSheet("color: #ff4444;")
            return

        try:
            port = int(port_str)
        except ValueError:
            self._test_result_label.setText("Port invalide.")
            self._test_result_label.setStyleSheet("color: #ff4444;")
            return

        self._test_btn.setEnabled(False)
        self._test_result_label.setText("Test en cours…")
        self._test_result_label.setStyleSheet("color: #aaaaaa;")

        certfile = self._cert_edit.text().strip() or None
        keyfile = self._key_edit.text().strip() or None

        # Lance le test dans un thread pour ne pas bloquer l'UI
        thread = threading.Thread(
            target=self._run_connection_test,
            args=(host, port, certfile, keyfile),
            daemon=True,
        )
        thread.start()

    def _run_connection_test(
        self,
        host: str,
        port: int,
        certfile: Optional[str],
        keyfile: Optional[str],
    ) -> None:
        """Effectue le test de connexion EPP (exécuté dans un thread)."""
        from src.epp.client import EppClient, EppConnectionError
        from src.epp.parser import parse

        client = EppClient()
        try:
            client.connect(host, port, certfile=certfile, keyfile=keyfile, timeout=10)
            greeting = client.get_greeting()
            resp = parse(greeting)
            client.disconnect()
            self._signals.success.emit(
                f"Connexion réussie — {resp.message or 'Greeting reçu'} ({host}:{port})"
            )
        except EppConnectionError as exc:
            self._signals.failure.emit(f"Erreur de connexion : {exc}")
        except Exception as exc:
            self._signals.failure.emit(f"Erreur inattendue : {exc}")
        finally:
            try:
                client.disconnect()
            except Exception:
                pass

    def _on_test_success(self, message: str) -> None:
        """Met à jour l'UI après un test réussi (slot Qt, thread-safe)."""
        self._test_result_label.setText(f"✓ {message}")
        self._test_result_label.setStyleSheet("color: #00cc00; font-weight: bold;")
        self._test_btn.setEnabled(True)

    def _on_test_failure(self, message: str) -> None:
        """Met à jour l'UI après un test échoué (slot Qt, thread-safe)."""
        self._test_result_label.setText(f"✗ {message}")
        self._test_result_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        self._test_btn.setEnabled(True)

    def _on_save(self) -> None:
        """Valide les champs et sauvegarde le profil en base de données."""
        if not self._validate_fields():
            return

        try:
            self._save_to_db()
            self.accept()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erreur de sauvegarde",
                f"Impossible de sauvegarder le profil :\n{exc}",
            )

    # ------------------------------------------------------------------
    # Validation et sauvegarde
    # ------------------------------------------------------------------

    def _validate_fields(self) -> bool:
        """Vérifie que tous les champs obligatoires sont remplis.

        Returns:
            True si la validation passe, False sinon.
        """
        errors = []

        if not self._name_edit.text().strip():
            errors.append("• Nom du profil")
        if not self._host_edit.text().strip():
            errors.append("• Hôte EPP")
        if not self._port_edit.text().strip():
            errors.append("• Port")
        if not self._login_edit.text().strip():
            errors.append("• Login")
        if not self._password_edit.text():
            errors.append("• Mot de passe")

        # Vérifie la cohérence cert/clé
        cert = self._cert_edit.text().strip()
        key = self._key_edit.text().strip()
        if cert and not key:
            errors.append("• Clé privée (requise si un certificat est fourni)")
        if key and not cert:
            errors.append("• Certificat (requis si une clé privée est fournie)")

        if errors:
            QMessageBox.warning(
                self,
                "Champs obligatoires manquants",
                "Veuillez remplir les champs suivants :\n" + "\n".join(errors),
            )
            return False

        return True

    def _save_to_db(self) -> None:
        """Chiffre le mot de passe et sauvegarde le profil en SQLite."""
        from src.security.crypto import CredentialManager
        from src.db.database import get_session
        from src.db.models import EppProfile

        # Chiffrement du mot de passe — jamais stocké en clair
        cm = CredentialManager()
        encrypted_pw = cm.encrypt(self._password_edit.text())

        session = get_session()
        try:
            if self._profile_id is not None:
                # Mode édition : met à jour le profil existant
                profile = session.get(EppProfile, self._profile_id)
                if profile is None:
                    raise ValueError(f"Profil ID={self._profile_id} introuvable")
            else:
                # Mode création
                profile = EppProfile()
                session.add(profile)

            profile.name = self._name_edit.text().strip()
            profile.host = self._host_edit.text().strip()
            profile.port = int(self._port_edit.text().strip())
            profile.login = self._login_edit.text().strip()
            profile.password_encrypted = encrypted_pw
            profile.tls_cert_path = self._cert_edit.text().strip() or None
            profile.tls_key_path = self._key_edit.text().strip() or None
            profile.environment = self._env_combo.currentData()
            profile.tags = self._tags_edit.text().strip() or None

            session.commit()
            logger.info(
                "Profil '%s' sauvegardé (env=%s, host=%s:%s)",
                profile.name,
                profile.environment,
                profile.host,
                profile.port,
            )
        finally:
            session.close()

    def _load_profile(self, profile_id: int) -> None:
        """Charge les données d'un profil existant dans le formulaire."""
        from src.db.database import get_session
        from src.db.models import EppProfile

        session = get_session()
        try:
            profile = session.get(EppProfile, profile_id)
            if profile is None:
                return
            self.setWindowTitle(f"Modifier le profil : {profile.name}")
            self._name_edit.setText(profile.name)
            self._host_edit.setText(profile.host)
            self._port_edit.setText(str(profile.port))
            self._login_edit.setText(profile.login)
            self._password_edit.setPlaceholderText("(inchangé — laisser vide pour conserver)")
            if profile.tls_cert_path:
                self._cert_edit.setText(profile.tls_cert_path)
            if profile.tls_key_path:
                self._key_edit.setText(profile.tls_key_path)
            idx = self._env_combo.findData(profile.environment)
            if idx >= 0:
                self._env_combo.setCurrentIndex(idx)
            if profile.tags:
                self._tags_edit.setText(profile.tags)
        finally:
            session.close()
