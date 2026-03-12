"""
Constructeurs de commandes XML EPP (RFC 5730).

Toutes les fonctions retournent une chaîne XML valide avec les namespaces
EPP corrects, prête à être envoyée via EppClient.send_command().
"""

import uuid
from lxml import etree

# Namespace EPP racine (RFC 5730)
EPP_NS = "urn:ietf:params:xml:ns:epp-1.0"
# Namespace domaine EPP (RFC 5731)
DOMAIN_NS = "urn:ietf:params:xml:ns:domain-1.0"
# Namespace contact EPP (RFC 5733)
CONTACT_NS = "urn:ietf:params:xml:ns:contact-1.0"
# Namespace host EPP (RFC 5732)
HOST_NS = "urn:ietf:params:xml:ns:host-1.0"

# Map des namespaces pour éviter les préfixes ns0, ns1…
_NSMAP = {None: EPP_NS}


def _new_cltr_id() -> str:
    """Génère un clTRID unique pour chaque commande."""
    return f"EPP-{uuid.uuid4().hex[:12].upper()}"


def _epp_root() -> etree._Element:
    """Crée l'élément racine <epp> avec le namespace EPP standard."""
    return etree.Element("epp", nsmap=_NSMAP)


def _to_xml_str(root: etree._Element) -> str:
    """Sérialise un élément lxml en chaîne XML avec déclaration UTF-8."""
    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode("utf-8")


def build_hello() -> str:
    """Construit la commande EPP <hello>.

    Permet de solliciter un greeting du serveur sans s'authentifier.
    RFC 5730 § 2.4.
    """
    root = _epp_root()
    etree.SubElement(root, "hello")
    return _to_xml_str(root)


def build_login(
    cl_id: str,
    password: str,
    new_password: str | None = None,
    version: str = "1.0",
    lang: str = "en",
    obj_uris: list[str] | None = None,
    ext_uris: list[str] | None = None,
) -> str:
    """Construit la commande EPP <login>.

    Args:
        cl_id: identifiant registrar (clID)
        password: mot de passe (pw) — sera masqué dans les logs
        new_password: nouveau mot de passe (newPW) optionnel
        version: version EPP (défaut: "1.0")
        lang: langue (défaut: "en")
        obj_uris: URIs d'objets à activer (défaut: domaine, contact, host)
        ext_uris: URIs d'extensions à activer (optionnel)

    Returns:
        Chaîne XML de la commande login.
    """
    if obj_uris is None:
        obj_uris = [DOMAIN_NS, CONTACT_NS, HOST_NS]

    root = _epp_root()
    command = etree.SubElement(root, "command")
    login = etree.SubElement(command, "login")

    # Identifiant registrar
    cl_id_el = etree.SubElement(login, "clID")
    cl_id_el.text = cl_id

    # Mot de passe (sera masqué par mask_sensitive dans le logger)
    pw_el = etree.SubElement(login, "pw")
    pw_el.text = password

    # Nouveau mot de passe optionnel
    if new_password:
        new_pw_el = etree.SubElement(login, "newPW")
        new_pw_el.text = new_password

    # Options : version et langue
    options = etree.SubElement(login, "options")
    ver_el = etree.SubElement(options, "version")
    ver_el.text = version
    lang_el = etree.SubElement(options, "lang")
    lang_el.text = lang

    # Services objets
    svcs = etree.SubElement(login, "svcs")
    for uri in obj_uris:
        obj_uri_el = etree.SubElement(svcs, "objURI")
        obj_uri_el.text = uri

    # Extensions optionnelles
    if ext_uris:
        svc_ext = etree.SubElement(svcs, "svcExtension")
        for uri in ext_uris:
            ext_uri_el = etree.SubElement(svc_ext, "extURI")
            ext_uri_el.text = uri

    # Identifiant transaction client
    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()

    return _to_xml_str(root)


def build_logout() -> str:
    """Construit la commande EPP <logout>. RFC 5730 § 2.9.2."""
    root = _epp_root()
    command = etree.SubElement(root, "command")
    etree.SubElement(command, "logout")
    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


def build_poll_request() -> str:
    """Construit la commande EPP <poll op="req">.

    Demande le prochain message disponible dans la file de messages.
    RFC 5730 § 2.9.2.3.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    poll = etree.SubElement(command, "poll")
    poll.set("op", "req")
    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


def build_poll_ack(msg_id: str) -> str:
    """Construit la commande EPP <poll op="ack"> pour acquitter un message.

    Args:
        msg_id: identifiant du message à acquitter (attribut msgID)

    RFC 5730 § 2.9.2.3.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    poll = etree.SubElement(command, "poll")
    poll.set("op", "ack")
    poll.set("msgID", msg_id)
    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)
