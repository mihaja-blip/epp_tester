"""
Export de l'historique des sessions EPP en CSV ou JSON.

Permet d'exporter les SessionLog depuis la base de données
vers des fichiers CSV ou JSON pour archivage ou analyse.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger, mask_sensitive

logger = get_logger("epp_tester.export")

# Colonnes exportées pour le CSV/JSON
_EXPORT_FIELDS = [
    "id",
    "timestamp",
    "profile_name",
    "command_type",
    "return_code",
    "duration_ms",
    "success",
    "operator",
    "xml_request",
    "xml_response",
]


def _log_to_dict(log, profile_name: str = "", mask_xml: bool = True) -> dict:
    """Convertit un SessionLog en dictionnaire exportable.

    Args:
        log: instance SessionLog SQLAlchemy
        profile_name: nom du profil associé
        mask_xml: si True, masque les credentials dans les trames XML

    Returns:
        Dictionnaire avec les champs définis dans _EXPORT_FIELDS.
    """
    # Formatage de la date en ISO 8601
    ts = log.timestamp
    timestamp_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)

    # Masquage des credentials dans les trames
    xml_req = log.xml_request or ""
    xml_resp = log.xml_response or ""
    if mask_xml:
        xml_req = mask_sensitive(xml_req)
        xml_resp = mask_sensitive(xml_resp)

    return {
        "id": log.id,
        "timestamp": timestamp_str,
        "profile_name": profile_name,
        "command_type": log.command_type or "",
        "return_code": log.return_code,
        "duration_ms": log.duration_ms,
        "success": log.success,
        "operator": log.operator or "",
        "xml_request": xml_req,
        "xml_response": xml_resp,
    }


def export_to_csv(
    logs: list,
    output_path: Path,
    profile_map: Optional[dict[int, str]] = None,
    mask_xml: bool = True,
) -> int:
    """Exporte une liste de SessionLog en CSV.

    Args:
        logs: liste d'instances SessionLog
        output_path: chemin du fichier CSV de sortie
        profile_map: dictionnaire {profile_id: profile_name}
        mask_xml: si True, masque les credentials (défaut: True)

    Returns:
        Nombre de lignes exportées.

    Raises:
        IOError: si l'écriture du fichier échoue.
    """
    profile_map = profile_map or {}
    rows = []
    for log in logs:
        profile_name = profile_map.get(log.profile_id, "") if log.profile_id else ""
        rows.append(_log_to_dict(log, profile_name, mask_xml))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Export CSV : %d lignes → %s", len(rows), output_path)
    return len(rows)


def export_to_json(
    logs: list,
    output_path: Path,
    profile_map: Optional[dict[int, str]] = None,
    mask_xml: bool = True,
    indent: int = 2,
) -> int:
    """Exporte une liste de SessionLog en JSON.

    Args:
        logs: liste d'instances SessionLog
        output_path: chemin du fichier JSON de sortie
        profile_map: dictionnaire {profile_id: profile_name}
        mask_xml: si True, masque les credentials (défaut: True)
        indent: indentation JSON (défaut: 2)

    Returns:
        Nombre d'enregistrements exportés.

    Raises:
        IOError: si l'écriture du fichier échoue.
    """
    profile_map = profile_map or {}
    records = []
    for log in logs:
        profile_name = profile_map.get(log.profile_id, "") if log.profile_id else ""
        records.append(_log_to_dict(log, profile_name, mask_xml))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export_data = {
        "export_date": datetime.now().isoformat(),
        "total_records": len(records),
        "records": records,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=indent)

    logger.info("Export JSON : %d enregistrements → %s", len(records), output_path)
    return len(records)


def query_logs_from_db(
    profile_id: Optional[int] = None,
    command_type: Optional[str] = None,
    limit: int = 1000,
) -> tuple[list, dict[int, str]]:
    """Interroge la base de données pour récupérer les SessionLog.

    Args:
        profile_id: filtrer par profil (None = tous les profils)
        command_type: filtrer par type de commande (None = toutes)
        limit: nombre maximum de logs à retourner

    Returns:
        Tuple (liste de SessionLog, dict {profile_id: profile_name})

    Raises:
        RuntimeError: si la base n'est pas initialisée.
    """
    from src.db.database import get_session
    from src.db.models import SessionLog, EppProfile

    session = get_session()
    try:
        # Construction de la requête
        query = session.query(SessionLog)
        if profile_id is not None:
            query = query.filter(SessionLog.profile_id == profile_id)
        if command_type:
            query = query.filter(SessionLog.command_type == command_type)
        query = query.order_by(SessionLog.timestamp.desc()).limit(limit)
        logs = query.all()

        # Construction du mapping profile_id → name
        profile_ids = {log.profile_id for log in logs if log.profile_id}
        profiles = (
            session.query(EppProfile)
            .filter(EppProfile.id.in_(profile_ids))
            .all()
        ) if profile_ids else []
        profile_map = {p.id: p.name for p in profiles}

        return logs, profile_map
    finally:
        session.close()
