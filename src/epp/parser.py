"""
Parseur de réponses EPP (RFC 5730).

Extrait le code retour, le message et les données métier
d'une réponse XML EPP.
"""

from dataclasses import dataclass, field
from lxml import etree

# Namespace EPP — utilisé pour toutes les recherches XPath
EPP_NS = "urn:ietf:params:xml:ns:epp-1.0"
_NS = {"epp": EPP_NS}


@dataclass
class EppResponse:
    """Représentation structurée d'une réponse EPP.

    Attributes:
        code: code retour numérique EPP (ex: 1000, 2303)
        message: texte du message de résultat
        raw_xml: trame XML brute reçue du serveur
        data: données métier extraites (resData, msgQ, svID…)
    """

    code: int
    message: str
    raw_xml: str
    data: dict = field(default_factory=dict)

    def is_success(self) -> bool:
        """Retourne True si la réponse indique un succès (code 1xxx)."""
        return 1000 <= self.code < 2000

    def is_error(self) -> bool:
        """Retourne True si la réponse indique une erreur (code 2xxx)."""
        return self.code >= 2000

    def __str__(self) -> str:
        status = "OK" if self.is_success() else "ERR"
        return f"EppResponse[{status} {self.code}] {self.message}"


def parse(xml_str: str) -> EppResponse:
    """Parse une réponse XML EPP et retourne un EppResponse.

    Extrait :
    - <result code="..."> : code retour numérique
    - <msg> : texte du message
    - <msgQ> : informations sur la file de messages (si présente)
    - <svTRID> : identifiant transaction serveur (si présent)
    - <resData> : données métier de la réponse (si présentes)

    Args:
        xml_str: chaîne XML brute reçue du serveur EPP

    Returns:
        EppResponse parsée

    Raises:
        ValueError: si le XML est invalide ou manque de structure EPP
    """
    if not xml_str or not xml_str.strip():
        raise ValueError("Réponse XML EPP vide")

    try:
        root = etree.fromstring(xml_str.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"XML EPP invalide : {exc}") from exc

    # Cherche l'élément <response> — peut être direct ou imbriqué dans <epp>
    response_el = root.find("epp:response", _NS)
    if response_el is None:
        # Certains serveurs retournent <response> à la racine sans <epp>
        if root.tag == f"{{{EPP_NS}}}response":
            response_el = root
        else:
            # Peut-être un greeting (<greeting>) — retourner code 1000 par convention
            greeting_el = root.find("epp:greeting", _NS)
            if greeting_el is not None:
                sv_id = _extract_text(greeting_el, "epp:svID", _NS) or "unknown"
                # Extrait les objURI et extURI annoncés dans le svcMenu
                svc_menu = greeting_el.find("epp:svcMenu", _NS)
                obj_uris: list[str] = []
                ext_uris: list[str] = []
                if svc_menu is not None:
                    obj_uris = [
                        el.text.strip()
                        for el in svc_menu.findall("epp:objURI", _NS)
                        if el.text
                    ]
                    svc_ext = svc_menu.find("epp:svcExtension", _NS)
                    if svc_ext is not None:
                        ext_uris = [
                            el.text.strip()
                            for el in svc_ext.findall("epp:extURI", _NS)
                            if el.text
                        ]
                return EppResponse(
                    code=1000,
                    message="Greeting reçu",
                    raw_xml=xml_str,
                    data={
                        "svID": sv_id,
                        "type": "greeting",
                        "objURIs": obj_uris,
                        "extURIs": ext_uris,
                    },
                )
            raise ValueError("Réponse EPP sans élément <response> ni <greeting>")

    # Extraction du code et message depuis <result code="..."><msg>
    result_el = response_el.find("epp:result", _NS)
    if result_el is None:
        raise ValueError("Réponse EPP sans élément <result>")

    code_str = result_el.get("code", "0")
    try:
        code = int(code_str)
    except ValueError:
        raise ValueError(f"Code retour EPP invalide : {code_str!r}")

    msg_el = result_el.find("epp:msg", _NS)
    message = msg_el.text.strip() if msg_el is not None and msg_el.text else ""

    # Extraction des données supplémentaires
    data: dict = {}

    # <svTRID> : identifiant transaction serveur
    sv_trid = _extract_text(response_el, "epp:trID/epp:svTRID", _NS)
    if sv_trid:
        data["svTRID"] = sv_trid

    # <clTRID> : identifiant transaction client
    cl_trid = _extract_text(response_el, "epp:trID/epp:clTRID", _NS)
    if cl_trid:
        data["clTRID"] = cl_trid

    # <msgQ> : file de messages (présente dans les réponses poll 1301)
    msg_q_el = response_el.find("epp:msgQ", _NS)
    if msg_q_el is not None:
        data["msgQ"] = {
            "count": msg_q_el.get("count"),
            "id": msg_q_el.get("id"),
        }
        # Message de la file
        q_msg_el = msg_q_el.find("epp:msg", _NS)
        if q_msg_el is not None and q_msg_el.text:
            data["msgQ"]["msg"] = q_msg_el.text.strip()

    # <resData> : données métier (check, info, create…)
    res_data_el = response_el.find("epp:resData", _NS)
    if res_data_el is not None:
        # Sérialise resData pour l'exploiter ultérieurement
        data["resData"] = etree.tostring(res_data_el, encoding="unicode")

    # <extValue> : valeurs d'erreur étendues
    ext_values = []
    for ext_val in result_el.findall("epp:extValue", _NS):
        reason_el = ext_val.find("epp:reason", _NS)
        value_el = ext_val.find("epp:value", _NS)
        ext_values.append({
            "reason": reason_el.text.strip() if reason_el is not None and reason_el.text else "",
            "value": etree.tostring(value_el, encoding="unicode") if value_el is not None else "",
        })
    if ext_values:
        data["extValue"] = ext_values

    return EppResponse(code=code, message=message, raw_xml=xml_str, data=data)


def _extract_text(element: etree._Element, xpath: str, ns: dict) -> str | None:
    """Extrait le texte d'un élément via XPath, retourne None si absent."""
    found = element.find(xpath, ns)
    if found is not None and found.text:
        return found.text.strip()
    return None
