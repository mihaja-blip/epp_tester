# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour EPP Tester Platform.

Génère un exe unique Windows (--onefile --windowed).
Exécuter depuis le répertoire racine du projet (venv activé) :
    pyinstaller EPP_Tester_Platform.spec
Le binaire final se trouve dans dist/EPP_Tester_Platform.exe
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Imports cachés nécessaires pour les bibliothèques dynamiques
hidden_imports = [
    # lxml : parseur C, nécessite les sous-modules explicitement
    "lxml.etree",
    "lxml._elementpath",
    "lxml.html",
    # SQLAlchemy : dialecte SQLite chargé dynamiquement
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    "sqlalchemy.pool",
    # cryptography : backends
    "cryptography.hazmat.backends.openssl",
    "cryptography.hazmat.primitives.kdf.pbkdf2",
    # PyQt6 : SIP binding
    "PyQt6.sip",
    # Module src (assure la découverte des sous-packages)
    "src.utils.paths",
    "src.utils.logger",
    "src.utils.constants",
    "src.utils.export",
    "src.security.crypto",
    "src.db.models",
    "src.db.database",
    "src.epp.client",
    "src.epp.commands",
    "src.epp.domain_commands",
    "src.epp.contact_commands",
    "src.epp.host_commands",
    "src.epp.parser",
    "src.epp.validator",
    "src.ui.main_window",
    "src.ui.session_tab",
    "src.ui.profile_dialog",
    "src.ui.logo",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Répertoire des schémas XSD EPP (peut être vide au premier build)
        ("resources/schemas", "resources/schemas"),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclut les modules de test et développement
        "pytest",
        "pytest_qt",
        "flake8",
        "black",
        "unittest",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EPP_Tester_Platform_v1.1",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # Compression UPX si disponible (réduit la taille)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # Pas de fenêtre console (application GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="resources/epp_tester.ico",  # Décommenter si une icône est disponible
)
