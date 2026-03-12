"""Configuration pytest — ajoute le répertoire racine au sys.path."""
import sys
from pathlib import Path

# Permet d'importer les modules src.* depuis les tests
sys.path.insert(0, str(Path(__file__).parent))
