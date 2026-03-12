# EPP Tester Platform

Application desktop Windows (Python/PyQt6) pour tester et diagnostiquer le protocole EPP (Extensible Provisioning Protocol, RFC 5730) entre un registre et des registrars.

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| UI | Python 3.11+ / PyQt6 6.6+ |
| Base de données | SQLite via SQLAlchemy 2.0 |
| XML EPP | lxml 5.1+ |
| Chiffrement | cryptography 42+ (Fernet AES-256) |
| Tests | pytest 8+ / pytest-qt |

## Installation

### Prérequis
- Python 3.11 ou supérieur
- Windows 10/11 (développé et testé sur Windows)

### Mise en place

```bash
# Cloner le dépôt
git clone https://github.com/mihaja-blip/epp_tester.git
cd epp_tester

# Créer et activer l'environnement virtuel
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/macOS

# Installer les dépendances
pip install -r requirements.txt
```

## Lancement

```bash
# Depuis le répertoire racine du projet, venv activé
python main.py
```

## Tests

```bash
# Lancer tous les tests
pytest tests/ -v

# Avec couverture
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Architecture

```
epp_tester/
├── src/
│   ├── ui/            # Fenêtres et dialogues PyQt6
│   ├── epp/           # Client TLS + XML builders + parser
│   ├── db/            # Modèles SQLAlchemy + init SQLite
│   ├── security/      # Chiffrement Fernet des credentials
│   └── utils/         # Constantes codes EPP + logger
├── tests/             # Suite de tests pytest
├── resources/schemas/ # Schémas XSD EPP
├── docs/
├── main.py            # Point d'entrée
└── requirements.txt
```

## Sécurité

- Les mots de passe EPP sont chiffrés avec **Fernet (AES-256-CBC + HMAC-SHA256)**
- La clé de chiffrement est dérivée via **PBKDF2HMAC-SHA256** et stockée dans `.epp_key` (gitignored)
- Toutes les trames XML loggées passent par `mask_sensitive()` — les balises `<pw>`, `<newPW>` et `<authInfo>` sont masquées automatiquement
- Connexion **TLS 1.2 minimum** (RFC 5734)

## Codes retour EPP

Le menu **Aide → Codes EPP** affiche le dictionnaire complet des codes retour EPP 1xxx/2xxx avec description, cause probable et solution recommandée (en français).

## Licence

Usage interne NIC-MG.
