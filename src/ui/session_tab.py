"""
Onglet de session EPP interactive.

Fournit un environnement complet pour tester les commandes EPP :
- Constructeur de commandes (formulaire → XML)
- Éditeur XML brut (modifiable avant envoi)
- Affichage de la réponse avec code retour coloré
- Barre d'outils : Connecter, Login, Logout, Déconnecter, Poll
- Validation XSD optionnelle avant envoi
"""

import threading
import time
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.utils.constants import get_code_info
from src.utils.logger import get_logger, mask_sensitive

logger = get_logger("epp_tester.session_tab")

# Couleurs pour l'affichage des réponses
COLOR_SUCCESS = "#00cc00"
COLOR_ERROR = "#ff4444"
COLOR_INFO = "#aaaaaa"
COLOR_SEND = "#4fc3f7"
COLOR_RECV = "#ffcc02"

# Types de commandes disponibles dans le sélecteur
COMMAND_TYPES = [
    ("--- Session ---", None),
    ("hello", "hello"),
    ("login", "login"),
    ("logout", "logout"),
    ("poll:req", "poll_req"),
    ("poll:ack", "poll_ack"),
    ("--- Domaine ---", None),
    ("domain:check", "domain_check"),
    ("domain:info", "domain_info"),
    ("domain:create", "domain_create"),
    ("domain:update", "domain_update"),
    ("domain:delete", "domain_delete"),
    ("domain:renew", "domain_renew"),
    ("domain:transfer", "domain_transfer"),
    ("--- Contact ---", None),
    ("contact:check", "contact_check"),
    ("contact:info", "contact_info"),
    ("contact:create", "contact_create"),
    ("contact:update", "contact_update"),
    ("contact:delete", "contact_delete"),
    ("--- Host ---", None),
    ("host:check", "host_check"),
    ("host:info", "host_info"),
    ("host:create", "host_create"),
    ("host:update", "host_update"),
    ("host:delete", "host_delete"),
]


class _WorkerSignals(QObject):
    """Signaux thread-safe pour les opérations réseau EPP."""
    connected = pyqtSignal(str)              # greeting XML
    disconnected = pyqtSignal()
    response = pyqtSignal(str, str, int)     # (request_xml, response_xml, duration_ms)
    error = pyqtSignal(str)                  # message d'erreur


class SessionTab(QWidget):
    """Onglet de session EPP interactive.

    Chaque onglet gère une connexion EPP indépendante vers un profil.
    Les opérations réseau s'exécutent dans des threads séparés pour
    ne pas bloquer l'interface graphique.
    """

    # Signal vers la console principale de la MainWindow
    log_message = pyqtSignal(str, str)

    def __init__(self, profile: dict, parent=None) -> None:
        """
        Args:
            profile: dict avec les clés 'name', 'host', 'port', 'login',
                     'password_encrypted', 'tls_cert_path', 'tls_key_path',
                     'environment', 'id' (optionnel)
        """
        super().__init__(parent)
        self._profile = profile
        self._connected = False
        self._logged_in = False
        self._signals = _WorkerSignals()

        # Connexion des signaux worker → slots UI
        self._signals.connected.connect(self._on_connected)
        self._signals.disconnected.connect(self._on_disconnected)
        self._signals.response.connect(self._on_response_received)
        self._signals.error.connect(self._on_worker_error)

        self._build_ui()
        self._update_toolbar_state()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construit l'interface complète de l'onglet de session."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # --- Barre d'outils ---
        self._toolbar = self._build_toolbar()
        layout.addWidget(self._toolbar)

        # --- Splitter horizontal : panneau commande / éditeur XML + réponse ---
        h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panneau gauche : constructeur de commandes
        cmd_panel = self._build_command_panel()
        h_splitter.addWidget(cmd_panel)

        # Panneau droit : éditeur XML + réponse (splitter vertical)
        v_splitter = QSplitter(Qt.Orientation.Vertical)

        xml_panel = self._build_xml_editor_panel()
        v_splitter.addWidget(xml_panel)

        response_panel = self._build_response_panel()
        v_splitter.addWidget(response_panel)

        v_splitter.setSizes([300, 300])
        h_splitter.addWidget(v_splitter)

        # Proportions : 350px gauche, reste à droite
        h_splitter.setSizes([350, 800])
        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)

        layout.addWidget(h_splitter)

        # --- Barre de statut locale ---
        self._status_label = QLabel(
            f"Profil : {self._profile.get('name', '?')} — "
            f"{self._profile.get('host', '?')}:{self._profile.get('port', 700)} — "
            "Déconnecté"
        )
        self._status_label.setStyleSheet("color: #888; padding: 2px 4px; font-size: 11px;")
        layout.addWidget(self._status_label)

    def _build_toolbar(self) -> QToolBar:
        """Construit la barre d'outils de la session."""
        toolbar = QToolBar()
        toolbar.setMovable(False)

        self._btn_connect = toolbar.addAction("Connecter")
        self._btn_connect.setToolTip("Établir la connexion TLS EPP")
        self._btn_connect.triggered.connect(self._on_connect)

        self._btn_disconnect = toolbar.addAction("Déconnecter")
        self._btn_disconnect.setToolTip("Fermer la connexion TLS")
        self._btn_disconnect.triggered.connect(self._on_disconnect)

        toolbar.addSeparator()

        self._btn_login = toolbar.addAction("Login")
        self._btn_login.setToolTip("Envoyer la commande login EPP")
        self._btn_login.triggered.connect(self._on_quick_login)

        self._btn_logout = toolbar.addAction("Logout")
        self._btn_logout.setToolTip("Envoyer la commande logout EPP")
        self._btn_logout.triggered.connect(self._on_quick_logout)

        toolbar.addSeparator()

        self._btn_poll = toolbar.addAction("Poll")
        self._btn_poll.setToolTip("Interroger la file de messages (poll:req)")
        self._btn_poll.triggered.connect(self._on_quick_poll)

        toolbar.addSeparator()

        self._btn_validate = toolbar.addAction("Valider XSD")
        self._btn_validate.setToolTip("Valider la syntaxe XML de la commande")
        self._btn_validate.triggered.connect(self._on_validate_xsd)

        self._btn_export = toolbar.addAction("Exporter")
        self._btn_export.setToolTip("Exporter l'historique en CSV ou JSON")
        self._btn_export.triggered.connect(self._on_export)

        return toolbar

    def _build_command_panel(self) -> QGroupBox:
        """Construit le panneau de construction de commandes."""
        group = QGroupBox("Constructeur de commandes")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        # Sélecteur de type de commande
        self._cmd_combo = QComboBox()
        for label, key in COMMAND_TYPES:
            self._cmd_combo.addItem(label, key)
            if key is None:
                # Section header — désactiver
                idx = self._cmd_combo.count() - 1
                self._cmd_combo.model().item(idx).setEnabled(False)
                self._cmd_combo.model().item(idx).setForeground(QColor("#888"))

        self._cmd_combo.currentIndexChanged.connect(self._on_command_type_changed)
        layout.addWidget(QLabel("Type de commande :"))
        layout.addWidget(self._cmd_combo)

        # Formulaire dynamique
        self._params_form = QFormLayout()
        self._params_form.setSpacing(4)
        layout.addLayout(self._params_form)

        # Champs du formulaire (créés une fois, affichés/cachés selon la commande)
        self._field_name = self._add_form_field("Nom / ID :", "ex: example.mg")
        self._field_names = self._add_form_field("Noms (séparés ,) :", "ex: a.mg, b.mg")
        self._field_period = self._add_form_spin("Durée :", 1, 10, 1)
        self._field_exp_date = self._add_form_field("Date exp. actuelle :", "YYYY-MM-DD")
        self._field_ns = self._add_form_field("NS (séparés ,) :", "ex: ns1.mg, ns2.mg")
        self._field_registrant = self._add_form_field("Registrant :", "ex: C-001")
        self._field_admin = self._add_form_field("Admin contact :", "ex: C-ADM")
        self._field_tech = self._add_form_field("Tech contact :", "ex: C-TECH")
        self._field_auth_pw = self._add_form_field("authInfo/pw :", "Mot de passe authInfo")
        self._field_auth_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._field_op = self._add_form_combo("Opération :", [
            "request", "query", "approve", "reject", "cancel"
        ])
        self._field_msg_id = self._add_form_field("Message ID :", "ex: 12345")
        self._field_new_auth_pw = self._add_form_field("Nouveau authInfo :", "Nouveau mot de passe")
        self._field_new_auth_pw.setEchoMode(QLineEdit.EchoMode.Password)
        # Champs contact
        self._field_contact_name = self._add_form_field("Nom complet :", "Jean Dupont")
        self._field_street = self._add_form_field("Adresse :", "1 Rue de la Paix")
        self._field_city = self._add_form_field("Ville :", "Antananarivo")
        self._field_cc = self._add_form_field("Code pays :", "MG")
        self._field_email = self._add_form_field("Email :", "contact@example.mg")
        self._field_voice = self._add_form_field("Téléphone :", "+261.123456789")
        # Champs host
        self._field_ipv4 = self._add_form_field("IPv4 (séparées ,) :", "ex: 196.0.4.1")
        self._field_ipv6 = self._add_form_field("IPv6 (séparées ,) :", "ex: 2001:db8::1")

        # Bouton de construction XML
        self._btn_build = QPushButton("Construire XML →")
        self._btn_build.setStyleSheet(
            "QPushButton { background: #1565c0; color: white; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background: #1976d2; }"
        )
        self._btn_build.clicked.connect(self._on_build_xml)
        layout.addWidget(self._btn_build)

        layout.addStretch()

        # Init : sélectionner domain:check par défaut
        for i in range(self._cmd_combo.count()):
            if self._cmd_combo.itemData(i) == "domain_check":
                self._cmd_combo.setCurrentIndex(i)
                break

        return group

    def _add_form_field(self, label: str, placeholder: str = "") -> QLineEdit:
        """Ajoute un QLineEdit au formulaire et retourne le widget."""
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        lbl = QLabel(label)
        self._params_form.addRow(lbl, edit)
        return edit

    def _add_form_spin(self, label: str, min_val: int, max_val: int, default: int) -> QSpinBox:
        """Ajoute un QSpinBox au formulaire et retourne le widget."""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        lbl = QLabel(label)
        self._params_form.addRow(lbl, spin)
        return spin

    def _add_form_combo(self, label: str, items: list[str]) -> QComboBox:
        """Ajoute un QComboBox au formulaire et retourne le widget."""
        combo = QComboBox()
        combo.addItems(items)
        lbl = QLabel(label)
        self._params_form.addRow(lbl, combo)
        return combo

    def _build_xml_editor_panel(self) -> QGroupBox:
        """Construit le panneau d'édition XML."""
        group = QGroupBox("Requête XML")
        layout = QVBoxLayout(group)

        self._xml_editor = QTextEdit()
        self._xml_editor.setFont(QFont("Consolas", 9))
        self._xml_editor.setStyleSheet("background: #1a1a2e; color: #e0e0e0; border: 1px solid #333;")
        self._xml_editor.setPlaceholderText(
            "Construisez une commande via le panneau gauche\n"
            "ou saisissez directement du XML EPP ici…"
        )
        layout.addWidget(self._xml_editor)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_clear = QPushButton("Effacer")
        self._btn_clear.clicked.connect(self._xml_editor.clear)
        btn_row.addWidget(self._btn_clear)

        self._btn_send = QPushButton("Envoyer →")
        self._btn_send.setStyleSheet(
            "QPushButton { background: #2e7d32; color: white; padding: 6px 16px; border-radius: 4px; }"
            "QPushButton:hover { background: #388e3c; }"
            "QPushButton:disabled { background: #444; color: #888; }"
        )
        self._btn_send.clicked.connect(self._on_send_command)
        btn_row.addWidget(self._btn_send)

        layout.addLayout(btn_row)
        return group

    def _build_response_panel(self) -> QGroupBox:
        """Construit le panneau d'affichage de la réponse."""
        group = QGroupBox("Réponse EPP")
        layout = QVBoxLayout(group)

        self._response_text = QTextEdit()
        self._response_text.setReadOnly(True)
        self._response_text.setFont(QFont("Consolas", 9))
        self._response_text.setStyleSheet(
            "background: #0d1117; color: #c9d1d9; border: 1px solid #333;"
        )
        layout.addWidget(self._response_text)

        # Indicateur du code retour
        code_row = QHBoxLayout()
        self._code_label = QLabel("")
        self._code_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        code_row.addWidget(self._code_label)
        code_row.addStretch()
        self._duration_label = QLabel("")
        self._duration_label.setStyleSheet("color: #888; font-size: 11px;")
        code_row.addWidget(self._duration_label)
        layout.addLayout(code_row)

        return group

    # ------------------------------------------------------------------
    # Logique du constructeur de commandes
    # ------------------------------------------------------------------

    def _on_command_type_changed(self) -> None:
        """Affiche/cache les champs du formulaire selon la commande sélectionnée."""
        cmd_key = self._cmd_combo.currentData()
        if cmd_key is None:
            return
        self._update_form_visibility(cmd_key)

    def _update_form_visibility(self, cmd_key: str) -> None:
        """Gère la visibilité des champs du formulaire."""
        # Tous les champs et leurs labels
        all_fields = [
            self._field_name, self._field_names, self._field_period,
            self._field_exp_date, self._field_ns, self._field_registrant,
            self._field_admin, self._field_tech, self._field_auth_pw,
            self._field_op, self._field_msg_id, self._field_new_auth_pw,
            self._field_contact_name, self._field_street, self._field_city,
            self._field_cc, self._field_email, self._field_voice,
            self._field_ipv4, self._field_ipv6,
        ]

        # Champs visibles selon la commande
        visible: set = set()

        if cmd_key == "poll_ack":
            visible = {self._field_msg_id}
        elif cmd_key in ("domain_check", "host_check", "contact_check"):
            visible = {self._field_names}
        elif cmd_key in ("domain_info",):
            visible = {self._field_name, self._field_auth_pw}
        elif cmd_key in ("domain_delete", "host_info", "host_delete",
                         "contact_info", "contact_delete"):
            visible = {self._field_name}
        elif cmd_key == "domain_create":
            visible = {self._field_name, self._field_period, self._field_ns,
                       self._field_registrant, self._field_admin, self._field_tech,
                       self._field_auth_pw}
        elif cmd_key == "domain_update":
            visible = {self._field_name, self._field_ns, self._field_new_auth_pw}
        elif cmd_key == "domain_renew":
            visible = {self._field_name, self._field_exp_date, self._field_period}
        elif cmd_key in ("domain_transfer", "contact_transfer"):
            visible = {self._field_name, self._field_op, self._field_auth_pw}
        elif cmd_key == "contact_create":
            visible = {self._field_name, self._field_contact_name, self._field_street,
                       self._field_city, self._field_cc, self._field_email,
                       self._field_voice, self._field_auth_pw}
        elif cmd_key == "contact_update":
            visible = {self._field_name, self._field_new_auth_pw}
        elif cmd_key == "host_create":
            visible = {self._field_name, self._field_ipv4, self._field_ipv6}
        elif cmd_key == "host_update":
            visible = {self._field_name, self._field_ipv4, self._field_ipv6}

        # Applique la visibilité
        for i in range(self._params_form.rowCount()):
            label_item = self._params_form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            field_item = self._params_form.itemAt(i, QFormLayout.ItemRole.FieldRole)
            if label_item and field_item:
                widget = field_item.widget()
                label_widget = label_item.widget()
                is_visible = widget in visible
                if widget:
                    widget.setVisible(is_visible)
                if label_widget:
                    label_widget.setVisible(is_visible)

    def _on_build_xml(self) -> None:
        """Construit le XML EPP depuis le formulaire et l'affiche dans l'éditeur."""
        cmd_key = self._cmd_combo.currentData()
        if cmd_key is None:
            return
        try:
            xml = self._build_xml_from_form(cmd_key)
            if xml:
                self._xml_editor.setPlainText(xml)
        except Exception as exc:
            QMessageBox.warning(self, "Erreur de construction", str(exc))

    def _build_xml_from_form(self, cmd_key: str) -> Optional[str]:
        """Construit le XML EPP à partir des valeurs du formulaire."""
        from src.epp import commands as C
        from src.epp import domain_commands as D
        from src.epp import contact_commands as CO
        from src.epp import host_commands as H

        def names_list() -> list[str]:
            return [n.strip() for n in self._field_names.text().split(",") if n.strip()]

        def name() -> str:
            return self._field_name.text().strip()

        def auth_pw() -> Optional[str]:
            pw = self._field_auth_pw.text()
            return pw if pw else None

        # --- Session ---
        if cmd_key == "hello":
            return C.build_hello()
        if cmd_key == "login":
            login = self._profile.get("login", "")
            # Déchiffrement du mot de passe depuis le profil
            encrypted_pw = self._profile.get("password_encrypted", "")
            try:
                from src.security.crypto import CredentialManager
                cm = CredentialManager()
                password = cm.decrypt(encrypted_pw) if encrypted_pw else ""
            except Exception:
                password = ""
            return C.build_login(login, password)
        if cmd_key == "logout":
            return C.build_logout()
        if cmd_key == "poll_req":
            return C.build_poll_request()
        if cmd_key == "poll_ack":
            msg_id = self._field_msg_id.text().strip()
            if not msg_id:
                raise ValueError("Message ID requis pour poll:ack")
            return C.build_poll_ack(msg_id)

        # --- Domaine ---
        if cmd_key == "domain_check":
            ns = names_list()
            if not ns:
                raise ValueError("Au moins un nom de domaine requis")
            return D.build_domain_check(ns)
        if cmd_key == "domain_info":
            return D.build_domain_info(name(), auth_pw=auth_pw())
        if cmd_key == "domain_create":
            ns_hosts = [n.strip() for n in self._field_ns.text().split(",") if n.strip()]
            return D.build_domain_create(
                name=name(),
                period=self._field_period.value(),
                ns_hosts=ns_hosts or None,
                registrant=self._field_registrant.text().strip() or None,
                admin_contact=self._field_admin.text().strip() or None,
                tech_contact=self._field_tech.text().strip() or None,
                auth_pw=self._field_auth_pw.text(),
            )
        if cmd_key == "domain_update":
            ns_list = [n.strip() for n in self._field_ns.text().split(",") if n.strip()]
            new_pw = self._field_new_auth_pw.text() or None
            return D.build_domain_update(name(), add_ns=ns_list or None, new_auth_pw=new_pw)
        if cmd_key == "domain_delete":
            return D.build_domain_delete(name())
        if cmd_key == "domain_renew":
            return D.build_domain_renew(
                name(), self._field_exp_date.text().strip(),
                period=self._field_period.value()
            )
        if cmd_key == "domain_transfer":
            return D.build_domain_transfer(
                name(), self._field_op.currentText(), auth_pw=auth_pw()
            )

        # --- Contact ---
        if cmd_key == "contact_check":
            ids = names_list()
            if not ids:
                raise ValueError("Au moins un identifiant contact requis")
            return CO.build_contact_check(ids)
        if cmd_key == "contact_info":
            return CO.build_contact_info(name(), auth_pw=auth_pw())
        if cmd_key == "contact_create":
            return CO.build_contact_create(
                contact_id=name(),
                name=self._field_contact_name.text().strip(),
                streets=[self._field_street.text().strip()],
                city=self._field_city.text().strip(),
                cc=self._field_cc.text().strip() or "MG",
                auth_pw=self._field_auth_pw.text(),
                voice=self._field_voice.text().strip() or None,
                email=self._field_email.text().strip(),
            )
        if cmd_key == "contact_update":
            new_pw = self._field_new_auth_pw.text() or None
            return CO.build_contact_update(name(), new_auth_pw=new_pw)
        if cmd_key == "contact_delete":
            return CO.build_contact_delete(name())
        if cmd_key == "contact_transfer":
            return CO.build_contact_transfer(name(), self._field_op.currentText(), auth_pw())

        # --- Host ---
        if cmd_key == "host_check":
            ns = names_list()
            if not ns:
                raise ValueError("Au moins un nom d'hôte requis")
            return H.build_host_check(ns)
        if cmd_key == "host_info":
            return H.build_host_info(name())
        if cmd_key == "host_create":
            ipv4 = [a.strip() for a in self._field_ipv4.text().split(",") if a.strip()]
            ipv6 = [a.strip() for a in self._field_ipv6.text().split(",") if a.strip()]
            return H.build_host_create(name(), ipv4_addresses=ipv4 or None, ipv6_addresses=ipv6 or None)
        if cmd_key == "host_update":
            ipv4 = [a.strip() for a in self._field_ipv4.text().split(",") if a.strip()]
            return H.build_host_update(name(), add_ipv4=ipv4 or None)
        if cmd_key == "host_delete":
            return H.build_host_delete(name())

        return None

    # ------------------------------------------------------------------
    # Actions de la barre d'outils
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        """Établit la connexion TLS EPP dans un thread."""
        if self._connected:
            self._append_response("Déjà connecté.", COLOR_INFO)
            return

        self._set_busy(True)
        self._append_response(
            f"Connexion vers {self._profile.get('host')}:{self._profile.get('port', 700)}…",
            COLOR_INFO
        )
        threading.Thread(target=self._worker_connect, daemon=True).start()

    def _worker_connect(self) -> None:
        """Thread : connexion TLS + lecture du greeting."""
        from src.epp.client import EppClient, EppConnectionError
        self._epp_client = EppClient()
        try:
            self._epp_client.connect(
                host=self._profile.get("host", ""),
                port=self._profile.get("port", 700),
                certfile=self._profile.get("tls_cert_path") or None,
                keyfile=self._profile.get("tls_key_path") or None,
                timeout=30,
            )
            greeting = self._epp_client.get_greeting()
            self._signals.connected.emit(greeting)
        except EppConnectionError as exc:
            self._signals.error.emit(f"Connexion échouée : {exc}")
        except Exception as exc:
            self._signals.error.emit(f"Erreur inattendue : {exc}")

    def _on_disconnect(self) -> None:
        """Ferme la connexion EPP."""
        if hasattr(self, "_epp_client"):
            threading.Thread(
                target=lambda: self._epp_client.disconnect(), daemon=True
            ).start()
        self._signals.disconnected.emit()

    def _on_quick_login(self) -> None:
        """Envoie rapidement une commande login avec les credentials du profil."""
        from src.epp.commands import build_login
        from src.security.crypto import CredentialManager

        login = self._profile.get("login", "")
        encrypted_pw = self._profile.get("password_encrypted", "")
        try:
            cm = CredentialManager()
            password = cm.decrypt(encrypted_pw) if encrypted_pw else ""
        except Exception:
            password = ""

        xml = build_login(login, password)
        self._xml_editor.setPlainText(xml)
        self._on_send_command()

    def _on_quick_logout(self) -> None:
        """Envoie rapidement une commande logout."""
        from src.epp.commands import build_logout
        self._xml_editor.setPlainText(build_logout())
        self._on_send_command()

    def _on_quick_poll(self) -> None:
        """Envoie rapidement une commande poll:req."""
        from src.epp.commands import build_poll_request
        self._xml_editor.setPlainText(build_poll_request())
        self._on_send_command()

    def _on_send_command(self) -> None:
        """Envoie la commande XML depuis l'éditeur."""
        if not self._connected:
            QMessageBox.warning(
                self, "Non connecté",
                "Connectez-vous d'abord au serveur EPP (bouton Connecter)."
            )
            return

        xml = self._xml_editor.toPlainText().strip()
        if not xml:
            return

        self._set_busy(True)
        threading.Thread(
            target=self._worker_send, args=(xml,), daemon=True
        ).start()

    def _worker_send(self, xml: str) -> None:
        """Thread : envoi de la commande et réception de la réponse."""
        t_start = time.monotonic()
        try:
            response = self._epp_client.send_command(xml)
            duration_ms = int((time.monotonic() - t_start) * 1000)
            self._signals.response.emit(xml, response, duration_ms)
        except Exception as exc:
            self._signals.error.emit(f"Erreur d'envoi : {exc}")

    def _on_validate_xsd(self) -> None:
        """Valide la syntaxe XML de la commande dans l'éditeur."""
        from src.epp.validator import EppValidator
        xml = self._xml_editor.toPlainText().strip()
        if not xml:
            return
        validator = EppValidator()
        result = validator.validate(xml)
        if result.is_valid:
            msg = result.summary()
            self._append_response(f"✓ {msg}", COLOR_SUCCESS)
        else:
            errors = "\n".join(f"  • {e}" for e in result.errors)
            self._append_response(f"✗ Validation XSD échouée :\n{errors}", COLOR_ERROR)

    def _on_export(self) -> None:
        """Ouvre un dialogue d'export de l'historique."""
        from PyQt6.QtWidgets import QFileDialog
        from src.utils.export import export_to_csv, export_to_json, query_logs_from_db

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exporter l'historique EPP",
            f"epp_history_{self._profile.get('name', 'export')}.csv",
            "CSV (*.csv);;JSON (*.json)",
        )
        if not file_path:
            return

        try:
            logs, profile_map = query_logs_from_db(
                profile_id=self._profile.get("id")
            )
            output = Path(file_path)
            if file_path.endswith(".json"):
                count = export_to_json(logs, output, profile_map)
            else:
                count = export_to_csv(logs, output, profile_map)
            QMessageBox.information(
                self, "Export terminé",
                f"{count} enregistrement(s) exporté(s) vers :\n{file_path}"
            )
        except RuntimeError:
            QMessageBox.warning(self, "Export", "Base de données non initialisée.")
        except Exception as exc:
            QMessageBox.critical(self, "Erreur d'export", str(exc))

    # ------------------------------------------------------------------
    # Slots worker → UI (thread-safe via signaux Qt)
    # ------------------------------------------------------------------

    def _on_connected(self, greeting: str) -> None:
        """Appelé dans le thread UI après une connexion réussie."""
        self._connected = True
        self._set_busy(False)
        self._update_toolbar_state()

        # Parse du greeting pour info
        try:
            from src.epp.parser import parse
            resp = parse(greeting)
            sv_id = resp.data.get("svID", "serveur EPP")
            self._append_response(
                f"✓ Connecté — Greeting reçu de : {sv_id}", COLOR_SUCCESS
            )
        except Exception:
            self._append_response("✓ Connecté — Greeting reçu", COLOR_SUCCESS)

        self._response_text.setPlainText(mask_sensitive(greeting))
        self._update_status("Connecté", "#00cc00")
        self.log_message.emit(
            f"[{self._profile.get('name')}] Connexion TLS établie", COLOR_SUCCESS
        )

    def _on_disconnected(self) -> None:
        """Appelé après déconnexion."""
        self._connected = False
        self._logged_in = False
        self._set_busy(False)
        self._update_toolbar_state()
        self._update_status("Déconnecté", "#888")
        self._append_response("Connexion fermée.", COLOR_INFO)
        self.log_message.emit(
            f"[{self._profile.get('name')}] Déconnecté", COLOR_INFO
        )

    def _on_response_received(self, request: str, response: str, duration_ms: int) -> None:
        """Affiche la réponse EPP dans le panneau de réponse."""
        self._set_busy(False)

        # Parse de la réponse pour l'affichage
        try:
            from src.epp.parser import parse
            resp = parse(response)
            code = resp.code
            info = get_code_info(code)
            color = COLOR_SUCCESS if resp.is_success() else COLOR_ERROR

            self._code_label.setText(f"Code {code} — {info['description']}")
            self._code_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            self._duration_label.setText(f"{duration_ms} ms")

            # Log dans la console principale
            self.log_message.emit(
                f"[{self._profile.get('name')}] {resp.command_type if hasattr(resp, 'command_type') else ''} → {code} {info['description']} ({duration_ms}ms)",
                color
            )

            # Si logout réussi, passer à déconnecté
            if code == 1500:
                self._logged_in = False
                self._append_response("Session EPP terminée (logout).", COLOR_INFO)

        except Exception as exc:
            code = 0
            self._code_label.setText(f"Erreur de parse : {exc}")
            self._code_label.setStyleSheet(f"color: {COLOR_ERROR};")

        # Affichage XML masqué
        masked_response = mask_sensitive(response)
        self._response_text.setPlainText(masked_response)

        # Log dans la session
        self._save_session_log(request, response, code, duration_ms)

    def _on_worker_error(self, message: str) -> None:
        """Affiche une erreur réseau."""
        self._set_busy(False)
        self._connected = False
        self._logged_in = False
        self._update_toolbar_state()
        self._update_status("Erreur", COLOR_ERROR)
        self._append_response(f"✗ {message}", COLOR_ERROR)
        self._code_label.setText(message)
        self._code_label.setStyleSheet(f"color: {COLOR_ERROR};")
        self.log_message.emit(
            f"[{self._profile.get('name')}] ERREUR : {message}", COLOR_ERROR
        )

    # ------------------------------------------------------------------
    # Méthodes utilitaires UI
    # ------------------------------------------------------------------

    def _append_response(self, text: str, color: str = COLOR_INFO) -> None:
        """Ajoute un message coloré dans la zone de réponse."""
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._response_text.append(f'<span style="color:{color}">{safe}</span>')
        self._response_text.moveCursor(QTextCursor.MoveOperation.End)

    def _update_status(self, text: str, color: str) -> None:
        """Met à jour la barre de statut locale."""
        profile_name = self._profile.get("name", "?")
        host = self._profile.get("host", "?")
        port = self._profile.get("port", 700)
        self._status_label.setText(
            f"Profil : {profile_name} — {host}:{port} — "
            f'<span style="color:{color}">{text}</span>'
        )
        self._status_label.setTextFormat(Qt.TextFormat.RichText)

    def _update_toolbar_state(self) -> None:
        """Active/désactive les boutons selon l'état de la connexion."""
        self._btn_connect.setEnabled(not self._connected)
        self._btn_disconnect.setEnabled(self._connected)
        self._btn_login.setEnabled(self._connected and not self._logged_in)
        self._btn_logout.setEnabled(self._connected)
        self._btn_poll.setEnabled(self._connected)
        self._btn_send.setEnabled(self._connected)

    def _set_busy(self, busy: bool) -> None:
        """Active/désactive le curseur d'attente."""
        if busy:
            from PyQt6.QtGui import QCursor
            from PyQt6.QtCore import Qt
            self.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.unsetCursor()

    def _save_session_log(
        self,
        xml_request: str,
        xml_response: str,
        return_code: int,
        duration_ms: int,
    ) -> None:
        """Enregistre la commande/réponse dans la base de données."""
        try:
            from src.db.database import get_session
            from src.db.models import SessionLog

            # Détection du type de commande depuis le XML
            cmd_type = self._detect_command_type(xml_request)

            session = get_session()
            log = SessionLog(
                profile_id=self._profile.get("id"),
                command_type=cmd_type,
                xml_request=mask_sensitive(xml_request),
                xml_response=mask_sensitive(xml_response),
                return_code=return_code,
                duration_ms=duration_ms,
                success=(1000 <= return_code < 2000) if return_code else False,
            )
            session.add(log)
            session.commit()
            session.close()
        except Exception as exc:
            logger.warning("Impossible de sauvegarder le log de session : %s", exc)

    @staticmethod
    def _detect_command_type(xml: str) -> str:
        """Extrait le type de commande EPP depuis le XML."""
        try:
            from lxml import etree
            root = etree.fromstring(xml.encode("utf-8"))
            # Cherche le premier élément sous <command>
            ns = "urn:ietf:params:xml:ns:epp-1.0"
            command_el = root.find(f"{{{ns}}}command")
            if command_el is None:
                return "hello"
            for child in command_el:
                tag = etree.QName(child).localname
                if tag not in ("clTRID", "extension"):
                    # Cherche le sous-namespace pour les commandes objet
                    for grandchild in child:
                        grand_ns = etree.QName(grandchild).namespace
                        grand_tag = etree.QName(grandchild).localname
                        if grand_ns and grand_ns != ns:
                            obj_ns_map = {
                                "urn:ietf:params:xml:ns:domain-1.0": "domain",
                                "urn:ietf:params:xml:ns:contact-1.0": "contact",
                                "urn:ietf:params:xml:ns:host-1.0": "host",
                            }
                            prefix = obj_ns_map.get(grand_ns, "")
                            if prefix:
                                return f"{prefix}:{grand_tag}"
                    return tag
        except Exception:
            pass
        return "unknown"


# Import manquant pour _on_export
from pathlib import Path
