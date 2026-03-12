"""
Fenêtre principale de EPP Tester Platform.

Architecture :
- Panneau gauche : liste des profils avec indicateur de connexion
- Zone centrale : onglets de sessions EPP
- Console bas : logs en temps réel
- Menus : Fichier, Connexion, Aide
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.utils.constants import EPP_RETURN_CODES, get_code_info
from src.utils.logger import get_logger

logger = get_logger("epp_tester.ui")

# Couleurs console
COLOR_SUCCESS = "#00ff00"   # vert — codes 1xxx
COLOR_ERROR = "#ff4444"     # rouge — codes 2xxx
COLOR_INFO = "#aaaaaa"      # gris — logs généraux
COLOR_SEND = "#4fc3f7"      # bleu clair — trames envoyées
COLOR_RECV = "#ffcc02"      # jaune — trames reçues

# Indicateurs de statut connexion
INDICATOR_CONNECTED = "● "
INDICATOR_DISCONNECTED = "● "


class MainWindow(QMainWindow):
    """Fenêtre principale EPP Tester Platform."""

    def __init__(self) -> None:
        super().__init__()
        self._setup_window()
        self._build_ui()
        self._build_menus()
        self._build_status_bar()
        self._refresh_profiles_from_db()
        logger.info("EPP Tester Platform démarré")

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        """Configure les propriétés de base de la fenêtre."""
        self.setWindowTitle("EPP Tester Platform v1.0")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        # Icône de la fenêtre (logo ETP)
        try:
            from src.ui.logo import create_etp_icon
            self.setWindowIcon(create_etp_icon(32))
        except Exception:
            pass

    def _build_ui(self) -> None:
        """Construit l'interface principale avec splitters."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Splitter principal horizontal (panneau gauche / zone centrale)
        self._h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Panneau gauche : liste des profils ---
        left_panel = self._build_profile_panel()
        self._h_splitter.addWidget(left_panel)

        # --- Zone centrale : onglets de session ---
        self._tab_widget = self._build_tab_widget()
        self._h_splitter.addWidget(self._tab_widget)

        # Proportions : 220px à gauche, le reste au centre
        self._h_splitter.setSizes([220, 980])
        self._h_splitter.setStretchFactor(0, 0)
        self._h_splitter.setStretchFactor(1, 1)

        # Splitter vertical : zone principale / console logs
        self._v_splitter = QSplitter(Qt.Orientation.Vertical)
        self._v_splitter.addWidget(self._h_splitter)

        # --- Console logs bas ---
        self._console = self._build_console()
        self._v_splitter.addWidget(self._console)

        # Proportions : 60% / 40%
        self._v_splitter.setSizes([500, 300])
        self._v_splitter.setStretchFactor(0, 1)
        self._v_splitter.setStretchFactor(1, 0)

        main_layout.addWidget(self._v_splitter)

    def _build_profile_panel(self) -> QWidget:
        """Construit le panneau gauche avec la liste des profils."""
        panel = QWidget()
        panel.setMinimumWidth(180)
        panel.setMaximumWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Titre
        title = QLabel("Profils EPP")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Liste des profils
        self._profile_list = QListWidget()
        self._profile_list.setToolTip(
            "Double-clic pour ouvrir une session\n"
            "Clic droit pour Modifier / Supprimer"
        )
        self._profile_list.itemDoubleClicked.connect(self._on_profile_double_click)
        self._profile_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._profile_list.customContextMenuRequested.connect(
            self._on_profile_context_menu
        )
        layout.addWidget(self._profile_list)

        # Légende indicateurs
        legend = QLabel(
            f'<span style="color:#00cc00">{INDICATOR_CONNECTED}</span>Connecté  '
            f'<span style="color:#888888">{INDICATOR_DISCONNECTED}</span>Déconnecté'
        )
        legend.setTextFormat(Qt.TextFormat.RichText)
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(legend)

        return panel

    def _build_tab_widget(self) -> QTabWidget:
        """Construit la zone d'onglets de sessions EPP."""
        tabs = QTabWidget()
        tabs.setTabsClosable(True)
        tabs.tabCloseRequested.connect(self._on_tab_close)

        # Onglet de bienvenue (non fermable)
        welcome = self._build_welcome_tab()
        tabs.addTab(welcome, "Bienvenue")
        tabs.tabBar().setTabButton(0, tabs.tabBar().ButtonPosition.RightSide, None)

        return tabs

    def _build_welcome_tab(self) -> QWidget:
        """Construit l'onglet de bienvenue avec logo et instructions."""
        from PyQt6.QtWidgets import QHBoxLayout
        from src.ui.logo import create_etp_pixmap

        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- Bandeau logo + titre ---
        header = QWidget()
        header.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0d47a1, stop:1 #1565c0);"
            "border-radius: 8px;"
        )
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(16, 12, 16, 12)

        logo_lbl = QLabel()
        try:
            logo_lbl.setPixmap(create_etp_pixmap(72))
        except Exception:
            logo_lbl.setText("EPP")
        hdr_layout.addWidget(logo_lbl)

        title_lbl = QLabel(
            "<span style='color:white; font-size:22px; font-weight:bold;'>"
            "EPP Tester Platform</span><br>"
            "<span style='color:#90caf9; font-size:12px;'>"
            "Test &amp; diagnostic du protocole EPP — RFC 5730/5731/5732/5734"
            "</span>"
        )
        title_lbl.setTextFormat(Qt.TextFormat.RichText)
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch()

        outer.addWidget(header)

        # --- Instructions ---
        instructions = QLabel(
            "<hr>"
            "<h3>Démarrage rapide</h3>"
            "<ol>"
            "<li><b>Fichier → Nouveau Profil</b> (Ctrl+N) : créer un profil de connexion</li>"
            "<li>Double-cliquer sur un profil pour ouvrir une session</li>"
            "<li>Clic droit sur un profil pour le <b>modifier</b> ou le <b>supprimer</b></li>"
            "<li><b>Connexion → Connecter</b> (Ctrl+L) : établir la connexion TLS</li>"
            "<li>Construire des commandes EPP et les envoyer — exporter en XML / JSON / Texte</li>"
            "</ol>"
            "<h3>Raccourcis clavier</h3>"
            "<ul>"
            "<li><b>Ctrl+N</b> : Nouveau profil</li>"
            "<li><b>Ctrl+L</b> : Connecter la session active</li>"
            "<li><b>Ctrl+Q</b> : Quitter</li>"
            "</ul>"
            "<hr>"
            "<p style='color:#888'>Les logs de session apparaissent dans la console ci-dessous.</p>"
        )
        instructions.setTextFormat(Qt.TextFormat.RichText)
        instructions.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        instructions.setWordWrap(True)
        instructions.setMargin(20)
        outer.addWidget(instructions)
        outer.addStretch()
        return widget

    def _build_console(self) -> QTextEdit:
        """Construit la console de logs (read-only, fond noir)."""
        console = QTextEdit()
        console.setReadOnly(True)
        console.setFont(QFont("Consolas", 9))
        console.setStyleSheet(
            "background-color: #1e1e1e; color: #aaaaaa; border: 1px solid #444;"
        )
        console.setMinimumHeight(100)
        console.setPlaceholderText("Console de logs EPP…")
        return console

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

    def _build_menus(self) -> None:
        """Construit la barre de menus."""
        menubar = self.menuBar()

        # Menu Fichier
        file_menu = menubar.addMenu("&Fichier")

        act_new_profile = QAction("&Nouveau Profil", self)
        act_new_profile.setShortcut(QKeySequence("Ctrl+N"))
        act_new_profile.setStatusTip("Créer un nouveau profil de connexion EPP")
        act_new_profile.triggered.connect(self._on_new_profile)
        file_menu.addAction(act_new_profile)

        file_menu.addSeparator()

        act_export = QAction("&Exporter historique…", self)
        act_export.setStatusTip("Exporter l'historique des sessions en CSV ou JSON")
        act_export.triggered.connect(self._on_export_history)
        file_menu.addAction(act_export)

        file_menu.addSeparator()

        act_settings = QAction("&Paramètres", self)
        act_settings.setStatusTip("Paramètres de l'application")
        act_settings.triggered.connect(self._on_settings)
        file_menu.addAction(act_settings)

        file_menu.addSeparator()

        act_quit = QAction("&Quitter", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.setStatusTip("Quitter l'application")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Action directe Test Ping (dans la barre de menus, pas de sous-menu)
        act_ping = QAction("⚡ Test Ping", self)
        act_ping.setStatusTip(
            "Envoyer un <hello> EPP sur la session active pour tester la connectivité"
        )
        act_ping.triggered.connect(self._on_ping)
        menubar.addAction(act_ping)

        # Menu Aide
        help_menu = menubar.addMenu("&Aide")

        act_epp_codes = QAction("&Codes EPP", self)
        act_epp_codes.setStatusTip("Afficher le dictionnaire des codes retour EPP")
        act_epp_codes.triggered.connect(self._on_show_epp_codes)
        help_menu.addAction(act_epp_codes)

        act_about = QAction("À &propos", self)
        act_about.setStatusTip("À propos de EPP Tester Platform")
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------
    # Barre de statut
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        """Construit la barre de statut permanente."""
        status_bar = self.statusBar()
        status_bar.setStyleSheet("QStatusBar { border-top: 1px solid #444; }")

        self._status_connection = QLabel("Déconnecté")
        self._status_connection.setStyleSheet("color: #888888; padding: 2px 8px;")

        self._status_last_code = QLabel("")
        self._status_last_code.setStyleSheet("padding: 2px 8px;")

        status_bar.addPermanentWidget(self._status_connection)
        status_bar.addPermanentWidget(QLabel("|"))
        status_bar.addPermanentWidget(self._status_last_code)

    # ------------------------------------------------------------------
    # API publique — console et statut
    # ------------------------------------------------------------------

    def log_to_console(self, message: str, color: str = COLOR_INFO) -> None:
        """Ajoute un message coloré à la console de logs.

        Args:
            message: texte à afficher
            color: couleur HTML (#rrggbb)
        """
        # Escape HTML pour éviter les injections
        safe_msg = (
            message.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        self._console.append(
            f'<span style="color:{color}">{safe_msg}</span>'
        )
        # Auto-scroll vers le bas
        self._console.moveCursor(QTextCursor.MoveOperation.End)

    def update_status(self, connected: bool, profile_name: str = "", code: int = 0) -> None:
        """Met à jour la barre de statut.

        Args:
            connected: True si une connexion est active
            profile_name: nom du profil connecté
            code: dernier code retour EPP (0 = aucun)
        """
        if connected:
            self._status_connection.setText(
                f'<span style="color:#00cc00">●</span> Connecté — {profile_name}'
            )
            self._status_connection.setTextFormat(Qt.TextFormat.RichText)
        else:
            self._status_connection.setText("● Déconnecté")
            self._status_connection.setStyleSheet("color: #888888; padding: 2px 8px;")

        if code:
            info = get_code_info(code)
            color = "#00cc00" if 1000 <= code < 2000 else "#ff4444"
            self._status_last_code.setText(
                f'<span style="color:{color}">Code {code}</span> — {info["description"]}'
            )
            self._status_last_code.setTextFormat(Qt.TextFormat.RichText)

    def refresh_profile_list(self, profiles: list[dict]) -> None:
        """Rafraîchit la liste des profils dans le panneau gauche.

        Args:
            profiles: liste de dicts avec 'name', 'connected' (bool)
        """
        self._profile_list.clear()
        for profile in profiles:
            name = profile.get("name", "?")
            connected = profile.get("connected", False)
            item = QListWidgetItem(name)
            if connected:
                item.setText(f"{INDICATOR_CONNECTED}{name}")
                item.setForeground(QColor("#00cc00"))
            else:
                item.setText(f"{INDICATOR_DISCONNECTED}{name}")
                item.setForeground(QColor("#888888"))
            item.setData(Qt.ItemDataRole.UserRole, profile)
            self._profile_list.addItem(item)

    # ------------------------------------------------------------------
    # Slots (actions)
    # ------------------------------------------------------------------

    def _on_new_profile(self) -> None:
        """Ouvre le dialogue de création de profil."""
        from src.ui.profile_dialog import ProfileDialog
        dialog = ProfileDialog(parent=self)
        if dialog.exec():
            self.log_to_console("Nouveau profil sauvegardé.", COLOR_SUCCESS)
            # Rafraîchir la liste depuis la DB
            self._refresh_profiles_from_db()

    def _on_export_history(self) -> None:
        """Exporte l'historique global des sessions."""
        from PyQt6.QtWidgets import QFileDialog
        from src.utils.export import export_to_csv, export_to_json, query_logs_from_db

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter l'historique EPP",
            "epp_history_global.csv",
            "CSV (*.csv);;JSON (*.json)",
        )
        if not file_path:
            return
        try:
            from pathlib import Path
            logs, profile_map = query_logs_from_db()
            output = Path(file_path)
            if file_path.endswith(".json"):
                count = export_to_json(logs, output, profile_map)
            else:
                count = export_to_csv(logs, output, profile_map)
            self.log_to_console(
                f"Export terminé : {count} enregistrement(s) → {file_path}",
                COLOR_SUCCESS
            )
        except RuntimeError:
            self.log_to_console("Base de données non initialisée.", COLOR_ERROR)
        except Exception as exc:
            self.log_to_console(f"Erreur d'export : {exc}", COLOR_ERROR)

    def _on_settings(self) -> None:
        self.log_to_console("Paramètres : non implémenté.", COLOR_INFO)

    def _get_active_session_tab(self):
        """Retourne le SessionTab actif, ou None si l'onglet courant n'en est pas un."""
        from src.ui.session_tab import SessionTab
        current = self._tab_widget.currentWidget()
        if isinstance(current, SessionTab):
            return current
        return None

    def _on_connect(self) -> None:
        """Connecte la session active, ou ouvre une nouvelle session depuis le profil sélectionné."""
        tab = self._get_active_session_tab()
        if tab:
            tab._on_connect()
            return
        # Aucune session active : ouvrir la session du profil sélectionné
        item = self._profile_list.currentItem()
        if item:
            self._on_profile_double_click(item)
        else:
            self.statusBar().showMessage(
                "Sélectionnez un profil ou ouvrez une session.", 3000
            )

    def _on_disconnect(self) -> None:
        """Déconnecte la session EPP active."""
        tab = self._get_active_session_tab()
        if tab:
            tab._on_disconnect()
        else:
            self.statusBar().showMessage("Aucune session active.", 3000)

    def _on_ping(self) -> None:
        """Envoie un <hello> EPP sur la session active."""
        tab = self._get_active_session_tab()
        if tab:
            from src.epp.commands import build_hello
            tab._xml_editor.setPlainText(build_hello())
            tab._on_send_command()
        else:
            self.log_to_console("Test ping : ouvrez une session d'abord.", COLOR_INFO)

    def _on_show_epp_codes(self) -> None:
        """Affiche le dictionnaire des codes retour EPP dans un onglet."""
        # Vérifie si l'onglet est déjà ouvert
        for i in range(self._tab_widget.count()):
            if self._tab_widget.tabText(i) == "Codes EPP":
                self._tab_widget.setCurrentIndex(i)
                return

        widget = self._build_epp_codes_tab()
        idx = self._tab_widget.addTab(widget, "Codes EPP")
        self._tab_widget.setCurrentIndex(idx)

    def _build_epp_codes_tab(self) -> QWidget:
        """Construit l'onglet du dictionnaire des codes EPP."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Consolas", 9))

        html_parts = [
            "<h2>Dictionnaire des codes retour EPP</h2>"
            "<table border='1' cellpadding='4'>"
        ]
        html_parts.append(
            "<tr><th>Code</th><th>Description</th><th>Cause</th><th>Solution</th></tr>"
        )
        for code, info in sorted(EPP_RETURN_CODES.items()):
            if code < 2000:
                cell_bg = "#e8f5e9"
                cell_fg = "#1b5e20"
            else:
                cell_bg = "#f0f0f0"
                cell_fg = "#546e7a"
            html_parts.append(
                f"<tr>"
                f"<td style='background-color:{cell_bg};'>"
                f"<b style='color:{cell_fg}'>{code}</b></td>"
                f"<td>{info['description']}</td>"
                f"<td>{info['cause']}</td>"
                f"<td>{info['solution']}</td>"
                f"</tr>"
            )
        html_parts.append("</table>")
        text.setHtml("".join(html_parts))
        layout.addWidget(text)
        return widget

    def _on_about(self) -> None:
        """Affiche la boîte de dialogue À propos."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "À propos — EPP Tester Platform",
            "<h3>EPP Tester Platform v1.0</h3>"
            "<p>Application desktop Windows pour tester et diagnostiquer "
            "le protocole EPP (RFC 5730/5731/5732/5734).</p>"
            "<p><b>Stack :</b> Python 3.11+, PyQt6, SQLite, lxml, cryptography</p>"
            "<p>© 2024 — NIC-MG</p>",
        )

    def _on_profile_double_click(self, item: QListWidgetItem) -> None:
        """Ouvre un onglet de session EPP pour le profil double-cliqué."""
        profile_data = item.data(Qt.ItemDataRole.UserRole)
        if not profile_data:
            return

        name = profile_data.get("name", "?")

        # Vérifie si un onglet pour ce profil est déjà ouvert
        for i in range(self._tab_widget.count()):
            if self._tab_widget.tabText(i) == name:
                self._tab_widget.setCurrentIndex(i)
                return

        # Charge les données complètes du profil depuis la DB
        profile_full = self._load_profile_data(profile_data.get("id"))
        if profile_full is None:
            self.log_to_console(f"Profil '{name}' introuvable en base.", COLOR_ERROR)
            return

        # Crée l'onglet de session
        from src.ui.session_tab import SessionTab
        tab = SessionTab(profile=profile_full, parent=self)
        tab.log_message.connect(self.log_to_console)

        idx = self._tab_widget.addTab(tab, name)
        self._tab_widget.setCurrentIndex(idx)
        self.log_to_console(f"Session ouverte pour : {name}", COLOR_INFO)

    def _load_profile_data(self, profile_id: int) -> dict | None:
        """Charge les données complètes d'un profil depuis la base de données."""
        if profile_id is None:
            return None
        try:
            from src.db.database import get_session
            from src.db.models import EppProfile
            session = get_session()
            profile = session.get(EppProfile, profile_id)
            if profile is None:
                session.close()
                return None
            data = {
                "id": profile.id,
                "name": profile.name,
                "host": profile.host,
                "port": profile.port,
                "login": profile.login,
                "password_encrypted": profile.password_encrypted,
                "tls_cert_path": profile.tls_cert_path,
                "tls_key_path": profile.tls_key_path,
                "environment": profile.environment,
                "tags": profile.tags,
            }
            session.close()
            return data
        except Exception as exc:
            logger.warning("Erreur de chargement du profil %s : %s", profile_id, exc)
            return None

    def _on_tab_close(self, index: int) -> None:
        """Ferme l'onglet demandé (sauf l'onglet Bienvenue index=0)."""
        if index == 0:
            return
        self._tab_widget.removeTab(index)

    def _on_profile_context_menu(self, pos) -> None:
        """Affiche le menu contextuel clic-droit sur la liste des profils."""
        item = self._profile_list.itemAt(pos)
        if item is None:
            return

        menu = QMenu(self)
        act_open = menu.addAction("Ouvrir une session")
        menu.addSeparator()
        act_edit = menu.addAction("Modifier le profil…")
        act_delete = menu.addAction("Supprimer le profil")

        act_open.triggered.connect(lambda: self._on_profile_double_click(item))
        act_edit.triggered.connect(lambda: self._on_edit_profile(item))
        act_delete.triggered.connect(lambda: self._on_delete_profile(item))

        menu.exec(self._profile_list.mapToGlobal(pos))

    def _on_edit_profile(self, item: QListWidgetItem) -> None:
        """Ouvre le dialogue d'édition du profil sélectionné."""
        profile_data = item.data(Qt.ItemDataRole.UserRole)
        if not profile_data:
            return
        from src.ui.profile_dialog import ProfileDialog
        dialog = ProfileDialog(parent=self, profile_id=profile_data.get("id"))
        if dialog.exec():
            self.log_to_console("Profil modifié.", COLOR_SUCCESS)
            self._refresh_profiles_from_db()

    def _on_delete_profile(self, item: QListWidgetItem) -> None:
        """Supprime le profil après confirmation."""
        profile_data = item.data(Qt.ItemDataRole.UserRole)
        if not profile_data:
            return
        name = profile_data.get("name", "?")
        reply = QMessageBox.question(
            self,
            "Supprimer le profil",
            f"Supprimer le profil « {name} » ?\n"
            "Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from src.db.database import get_session
            from src.db.models import EppProfile
            session = get_session()
            profile = session.get(EppProfile, profile_data.get("id"))
            if profile:
                session.delete(profile)
                session.commit()
            session.close()
            self.log_to_console(f"Profil '{name}' supprimé.", COLOR_INFO)
            self._refresh_profiles_from_db()
        except Exception as exc:
            self.log_to_console(f"Erreur suppression : {exc}", COLOR_ERROR)

    def _refresh_profiles_from_db(self) -> None:
        """Recharge la liste des profils depuis la base de données."""
        try:
            from src.db.database import get_session
            from src.db.models import EppProfile
            session = get_session()
            profiles = session.query(EppProfile).all()
            profile_dicts = [
                {"name": p.name, "connected": False, "id": p.id}
                for p in profiles
            ]
            session.close()
            self.refresh_profile_list(profile_dicts)
        except RuntimeError:
            # DB non initialisée — normal au premier lancement
            pass
