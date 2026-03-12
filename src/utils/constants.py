"""
Codes retour EPP complets (RFC 5730 section 3) avec descriptions en français.
Chaque entrée décrit le code, la cause probable et la solution recommandée.
"""

from typing import TypedDict


class EppCodeInfo(TypedDict):
    description: str
    cause: str
    solution: str


# Dictionnaire complet des codes retour EPP
EPP_RETURN_CODES: dict[int, EppCodeInfo] = {
    # =========================================================================
    # 1xxx — Succès
    # =========================================================================
    1000: {
        "description": "Commande réussie",
        "cause": "La commande a été traitée avec succès.",
        "solution": "Aucune action requise.",
    },
    1001: {
        "description": "Commande réussie ; action en attente",
        "cause": "La commande a été acceptée mais son traitement est différé "
                 "(ex. : transfert en attente d'approbation du registrar perdant).",
        "solution": "Interroger le statut ultérieurement via poll ou info.",
    },
    1300: {
        "description": "Commande réussie ; aucun message en attente",
        "cause": "La commande poll a abouti mais la file de messages est vide.",
        "solution": "Aucun message à traiter. Réinterroger plus tard.",
    },
    1301: {
        "description": "Commande réussie ; message(s) en attente",
        "cause": "La commande poll a abouti et des messages sont disponibles.",
        "solution": "Lire les messages via poll:req et acquitter via poll:ack.",
    },
    1500: {
        "description": "Commande réussie ; déconnexion en cours",
        "cause": "La commande logout a été acceptée. La session est terminée.",
        "solution": "Fermer la connexion TCP.",
    },
    # =========================================================================
    # 2xxx — Erreurs
    # =========================================================================
    2000: {
        "description": "Erreur de commande inconnue",
        "cause": "Le serveur ne reconnaît pas la commande reçue.",
        "solution": "Vérifier la syntaxe XML et le namespace EPP utilisé.",
    },
    2001: {
        "description": "Erreur de syntaxe de commande",
        "cause": "Le XML de la commande ne respecte pas le schéma EPP.",
        "solution": "Valider le XML contre les schémas XSD EPP avant envoi.",
    },
    2002: {
        "description": "Utilisation de commande incorrecte",
        "cause": "La commande est syntaxiquement correcte mais utilisée hors contexte "
                 "(ex. : login après login).",
        "solution": "Vérifier le flux de session EPP : login → commandes → logout.",
    },
    2003: {
        "description": "Paramètre obligatoire manquant",
        "cause": "Un champ requis est absent de la commande.",
        "solution": "Consulter la RFC ou le schéma XSD pour les champs obligatoires.",
    },
    2004: {
        "description": "Valeur de paramètre hors limites",
        "cause": "La valeur d'un champ dépasse les contraintes définies "
                 "(longueur, format, plage).",
        "solution": "Corriger la valeur selon les contraintes du schéma.",
    },
    2005: {
        "description": "Valeur de paramètre syntaxiquement incorrecte",
        "cause": "La valeur d'un champ ne respecte pas le format attendu "
                 "(ex. : date invalide, ROID malformé).",
        "solution": "Vérifier le format de la valeur fournie.",
    },
    2100: {
        "description": "Version du protocole non implémentée",
        "cause": "Le client demande une version EPP non supportée par le serveur.",
        "solution": "Utiliser la version EPP 1.0 standard.",
    },
    2101: {
        "description": "Service non implémenté",
        "cause": "L'objet ou l'extension demandé n'est pas supporté par ce serveur.",
        "solution": "Vérifier le greeting pour la liste des services disponibles.",
    },
    2102: {
        "description": "Option non implémentée",
        "cause": "Une option demandée dans le login n'est pas supportée.",
        "solution": "Retirer l'option non supportée de la commande login.",
    },
    2103: {
        "description": "Extension de commande non implémentée",
        "cause": "L'extension utilisée n'est pas reconnue par le serveur.",
        "solution": "Vérifier les extensions annoncées dans le greeting.",
    },
    2104: {
        "description": "Politique de facturation non implémentée",
        "cause": "L'opération demandée nécessite un accord de facturation absent.",
        "solution": "Contacter le registre pour les conditions contractuelles.",
    },
    2200: {
        "description": "Erreur d'authentification",
        "cause": "Identifiant ou mot de passe incorrect.",
        "solution": "Vérifier les credentials. Après plusieurs échecs, "
                    "le compte peut être verrouillé.",
    },
    2201: {
        "description": "Erreur d'autorisation",
        "cause": "Le registrar n'est pas autorisé à effectuer cette opération "
                 "sur cet objet.",
        "solution": "Vérifier que le registrar est le sponsoring registrar "
                    "ou dispose des droits nécessaires.",
    },
    2202: {
        "description": "Erreur d'autorisation invalide",
        "cause": "L'authInfo fourni est incorrect ou expiré.",
        "solution": "Demander un nouveau code authInfo au détenteur de l'objet.",
    },
    2300: {
        "description": "Transfert interdit",
        "cause": "L'objet ne peut pas être transféré (statut clientTransferProhibited "
                 "ou serverTransferProhibited).",
        "solution": "Lever le verrou de transfert avant de soumettre la demande.",
    },
    2301: {
        "description": "Objet non transférable",
        "cause": "Le type d'objet ne supporte pas l'opération de transfert.",
        "solution": "Vérifier la politique du registre pour ce type d'objet.",
    },
    2302: {
        "description": "Objet déjà existant",
        "cause": "Un create a été tenté pour un objet dont le nom existe déjà.",
        "solution": "Choisir un nom différent ou utiliser update si vous possédez l'objet.",
    },
    2303: {
        "description": "Objet non trouvé",
        "cause": "L'objet référencé dans la commande n'existe pas dans le registre.",
        "solution": "Vérifier l'identifiant/le nom de l'objet. "
                    "Utiliser check avant d'autres opérations.",
    },
    2304: {
        "description": "Statut de l'objet interdit l'opération",
        "cause": "L'objet possède un statut qui empêche l'opération demandée "
                 "(ex. : clientDeleteProhibited).",
        "solution": "Retirer le statut bloquant via update avant de réessayer.",
    },
    2305: {
        "description": "Dépendance d'objet interdisant la suppression",
        "cause": "L'objet ne peut pas être supprimé car d'autres objets en dépendent "
                 "(ex. : host utilisé par un domaine).",
        "solution": "Supprimer ou modifier les objets dépendants d'abord.",
    },
    2306: {
        "description": "Paramètre de politique non applicable",
        "cause": "Un paramètre fourni est valide syntaxiquement mais contraire "
                 "à la politique du registre.",
        "solution": "Consulter la politique du registre pour les valeurs autorisées.",
    },
    2307: {
        "description": "Violation de l'unicité de l'objet",
        "cause": "Une contrainte d'unicité a été violée (ex. : doublon d'attribut).",
        "solution": "Corriger la valeur dupliquée.",
    },
    2308: {
        "description": "Paramètre de politique de l'objet non applicable",
        "cause": "La valeur fournie ne respecte pas les règles du registre "
                 "pour ce type d'objet.",
        "solution": "Consulter la documentation du registre.",
    },
    2400: {
        "description": "Erreur interne du serveur",
        "cause": "Le serveur EPP a rencontré une erreur interne inattendue.",
        "solution": "Réessayer plus tard. Si le problème persiste, contacter le registre.",
    },
    2500: {
        "description": "Erreur de dépassement de capacité",
        "cause": "Le serveur EPP est surchargé ou en maintenance.",
        "solution": "Attendre et réessayer. Implémenter un backoff exponentiel.",
    },
    2501: {
        "description": "Délai d'attente de traitement dépassé",
        "cause": "Le traitement de la commande a pris trop de temps côté serveur.",
        "solution": "Vérifier le statut de l'objet via info. Réessayer si nécessaire.",
    },
    2502: {
        "description": "Session non autorisée — limite de sessions atteinte",
        "cause": "Le registrar a atteint le nombre maximum de sessions simultanées.",
        "solution": "Fermer des sessions inactives. Vérifier la limite avec le registre.",
    },
}


def get_code_info(code: int) -> EppCodeInfo:
    """Retourne les informations pour un code retour EPP.

    Args:
        code: code retour EPP (ex: 1000, 2303)

    Returns:
        Dictionnaire avec description, cause et solution.
        Si le code est inconnu, retourne une entrée générique.
    """
    return EPP_RETURN_CODES.get(
        code,
        {
            "description": f"Code inconnu ({code})",
            "cause": "Ce code n'est pas répertorié dans le dictionnaire EPP.",
            "solution": "Consulter la RFC 5730 ou la documentation du registre.",
        },
    )


def is_success_code(code: int) -> bool:
    """Retourne True si le code indique un succès (1xxx)."""
    return 1000 <= code < 2000


def is_error_code(code: int) -> bool:
    """Retourne True si le code indique une erreur (2xxx)."""
    return code >= 2000
