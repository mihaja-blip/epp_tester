"""
Validateur XSD pour les trames XML EPP.

Valide les trames EPP contre les schémas XSD officiels (RFC 5730-5733).
Les schémas sont chargés depuis resources/schemas/ au premier appel.
"""

from pathlib import Path
from typing import Optional
from lxml import etree

from src.utils.logger import get_logger

logger = get_logger("epp_tester.validator")

# Répertoire des schémas XSD
SCHEMAS_DIR = Path("resources/schemas")

# Correspondance namespace → fichier XSD
_SCHEMA_FILES = {
    "urn:ietf:params:xml:ns:epp-1.0":     "epp-1.0.xsd",
    "urn:ietf:params:xml:ns:domain-1.0":  "domain-1.0.xsd",
    "urn:ietf:params:xml:ns:contact-1.0": "contact-1.0.xsd",
    "urn:ietf:params:xml:ns:host-1.0":    "host-1.0.xsd",
}

# Cache des schémas chargés
_schema_cache: dict[str, etree.XMLSchema] = {}


class ValidationError(Exception):
    """Erreur de validation XSD d'une trame EPP."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class EppValidator:
    """Validateur de trames XML EPP contre les schémas XSD RFC.

    Usage::
        validator = EppValidator()
        result = validator.validate(xml_string)
        if not result.is_valid:
            print(result.errors)
    """

    def __init__(self, schemas_dir: Path = SCHEMAS_DIR) -> None:
        self._schemas_dir = schemas_dir

    def validate(self, xml_str: str, namespace: Optional[str] = None) -> "ValidationResult":
        """Valide une trame XML EPP contre le schéma XSD approprié.

        Détecte automatiquement le namespace principal si non fourni.

        Args:
            xml_str: trame XML EPP à valider
            namespace: namespace à utiliser pour choisir le schéma
                       (si None, détecté depuis le XML)

        Returns:
            ValidationResult avec is_valid et la liste des erreurs.
        """
        if not xml_str or not xml_str.strip():
            return ValidationResult(False, ["Trame XML vide"])

        # Parse du XML
        try:
            root = etree.fromstring(xml_str.encode("utf-8"))
        except etree.XMLSyntaxError as exc:
            return ValidationResult(False, [f"XML invalide : {exc}"])

        # Détection du namespace si non fourni
        if namespace is None:
            namespace = self._detect_namespace(root)

        if namespace is None:
            return ValidationResult(
                False,
                ["Namespace EPP non reconnu — schéma XSD introuvable"]
            )

        # Chargement du schéma
        schema = self._load_schema(namespace)
        if schema is None:
            return ValidationResult(
                True,
                [],
                warning=f"Schéma XSD non disponible pour {namespace} — validation ignorée"
            )

        # Validation
        is_valid = schema.validate(root)
        if is_valid:
            return ValidationResult(True, [])

        # Collecte des erreurs de validation
        errors = [str(err) for err in schema.error_log]
        return ValidationResult(False, errors)

    def validate_xml_syntax(self, xml_str: str) -> "ValidationResult":
        """Valide uniquement la syntaxe XML (sans schéma XSD).

        Utile pour vérifier rapidement qu'une trame est du XML valide.

        Args:
            xml_str: trame XML à vérifier

        Returns:
            ValidationResult.
        """
        if not xml_str or not xml_str.strip():
            return ValidationResult(False, ["Trame XML vide"])
        try:
            etree.fromstring(xml_str.encode("utf-8"))
            return ValidationResult(True, [])
        except etree.XMLSyntaxError as exc:
            return ValidationResult(False, [f"Erreur de syntaxe XML : {exc}"])

    def _detect_namespace(self, root: etree._Element) -> Optional[str]:
        """Détecte le namespace principal d'une trame EPP.

        Le namespace de la racine (<epp>) est toujours EPP.
        Pour les sous-commandes, on cherche le premier namespace enfant connu.
        """
        # Namespace de l'élément racine
        root_ns = etree.QName(root).namespace
        if root_ns in _SCHEMA_FILES:
            return root_ns

        # Cherche dans les enfants
        for elem in root.iter():
            ns = etree.QName(elem).namespace
            if ns and ns in _SCHEMA_FILES:
                return ns

        return None

    def _load_schema(self, namespace: str) -> Optional[etree.XMLSchema]:
        """Charge et met en cache le schéma XSD pour un namespace.

        Args:
            namespace: namespace EPP

        Returns:
            XMLSchema chargé, ou None si le fichier est absent.
        """
        if namespace in _schema_cache:
            return _schema_cache[namespace]

        schema_file = _SCHEMA_FILES.get(namespace)
        if not schema_file:
            return None

        schema_path = self._schemas_dir / schema_file
        if not schema_path.exists():
            logger.debug("Schéma XSD absent : %s", schema_path)
            return None

        try:
            schema_doc = etree.parse(str(schema_path))
            schema = etree.XMLSchema(schema_doc)
            _schema_cache[namespace] = schema
            logger.debug("Schéma XSD chargé : %s", schema_path)
            return schema
        except etree.XMLSchemaParseError as exc:
            logger.warning("Erreur de chargement du schéma %s : %s", schema_path, exc)
            return None


class ValidationResult:
    """Résultat d'une validation XSD.

    Attributes:
        is_valid: True si la validation passe
        errors: liste des messages d'erreur
        warning: avertissement non bloquant (ex: schéma absent)
    """

    def __init__(
        self,
        is_valid: bool,
        errors: list[str],
        warning: Optional[str] = None,
    ) -> None:
        self.is_valid = is_valid
        self.errors = errors
        self.warning = warning

    def __bool__(self) -> bool:
        return self.is_valid

    def summary(self) -> str:
        """Retourne un résumé lisible du résultat."""
        if self.is_valid:
            msg = "Validation XSD : OK"
            if self.warning:
                msg += f" ({self.warning})"
            return msg
        return "Validation XSD : ECHEC\n" + "\n".join(f"  • {e}" for e in self.errors)
