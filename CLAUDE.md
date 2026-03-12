# CLAUDE.md — EPP Tester Platform

## Contexte du projet
Application desktop Windows (Python 3.11+ / PyQt6) pour tester et diagnostiquer
le protocole EPP (Extensible Provisioning Protocol, RFC 5730/5731/5732/5734)
entre un registre et des registrars.

## Architecture
```
src/
  ui/          Fenêtres et dialogues PyQt6
  epp/         Client TCP/TLS + constructeurs/parseur XML EPP
  db/          Modèles SQLAlchemy + init SQLite
  security/    Chiffrement Fernet des credentials
  utils/       Constantes codes-retour EPP + logger centralisé
tests/         pytest — 100% pass avant chaque commit
resources/schemas/  Schémas XSD EPP (validation XML)
main.py        Point d'entrée application
```

## Règles absolues
- `pytest tests/ -v` doit passer à 100% avant chaque commit
- Ne JAMAIS stocker de credentials en clair (code, logs, DB)
- Tout XML logué passe par `mask_sensitive()` du logger
- Commits atomiques : une fonctionnalité = un commit
- Format commit : `type(scope): description courte`
- Si un fichier dépasse 300 lignes → découper en modules
- Commenter en français les parties logique métier EPP complexes

## Standards de code
- Formateur : black
- Linter : flake8
- Python 3.11+, type hints partout
- lxml.etree pour tout le XML (pas xml.etree.ElementTree)
- Namespace EPP racine : `urn:ietf:params:xml:ns:epp-1.0`
- Framing RFC 5734 : 4 octets big-endian (header 4 bytes inclus) + payload

## Sécurité
- TLS 1.2 minimum, vérification du certificat serveur
- Mot de passe chiffré Fernet (AES-256-CBC + HMAC-SHA256)
- Clé dérivée PBKDF2HMAC stockée dans `.epp_key` (gitignored)
- Aucun secret dans les logs ni dans Git

## Phase 1 (en cours)
- [x] crypto.py
- [x] models.py + database.py
- [x] client.py
- [x] commands.py
- [x] parser.py
- [x] constants.py
- [x] logger.py
- [x] main_window.py
- [x] profile_dialog.py
- [x] main.py

## Phase 2 (à venir)
- Commandes domaine : check, create, info, update, delete, renew, transfer
- Commandes contact et host
- Session tab avec éditeur XML brut
- Export historique CSV/JSON
- Validation XSD des trames
