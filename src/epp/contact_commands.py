"""
Constructeurs de commandes XML EPP pour les objets contact (RFC 5733).

Les contacts EPP représentent des personnes ou organisations associées
aux noms de domaine (registrant, admin, tech, billing).
"""

from typing import Optional
from lxml import etree

from src.epp.commands import EPP_NS, _new_cltr_id, _to_xml_str

# Namespace contact EPP (RFC 5733)
CONTACT_NS = "urn:ietf:params:xml:ns:contact-1.0"

_NSMAP = {None: EPP_NS, "contact": CONTACT_NS}


def C(tag: str) -> str:
    """Raccourci Clark notation pour les éléments du namespace contact."""
    return f"{{{CONTACT_NS}}}{tag}"


def _epp_root() -> etree._Element:
    """Crée l'élément racine <epp> avec les namespaces EPP et contact."""
    return etree.Element("epp", nsmap=_NSMAP)


def _build_postal_info(
    parent: etree._Element,
    postal_type: str,
    name: str,
    org: Optional[str],
    streets: list[str],
    city: str,
    sp: Optional[str],
    pc: Optional[str],
    cc: str,
) -> None:
    """Construit l'élément <contact:postalInfo> et ses sous-éléments.

    Args:
        parent: élément parent auquel attacher postalInfo
        postal_type: "loc" (local) ou "int" (international)
        name: nom complet de la personne ou organisation
        org: nom de l'organisation (optionnel)
        streets: liste de lignes d'adresse (1 à 3 lignes)
        city: ville
        sp: état/province (optionnel)
        pc: code postal (optionnel)
        cc: code pays ISO 3166-1 alpha-2 (ex: "MG", "FR")
    """
    postal_info = etree.SubElement(parent, C("postalInfo"))
    postal_info.set("type", postal_type)

    etree.SubElement(postal_info, C("name")).text = name

    if org:
        etree.SubElement(postal_info, C("org")).text = org

    addr = etree.SubElement(postal_info, C("addr"))
    for street in streets[:3]:  # Max 3 lignes selon RFC 5733
        etree.SubElement(addr, C("street")).text = street
    etree.SubElement(addr, C("city")).text = city
    if sp:
        etree.SubElement(addr, C("sp")).text = sp
    if pc:
        etree.SubElement(addr, C("pc")).text = pc
    etree.SubElement(addr, C("cc")).text = cc


# ---------------------------------------------------------------------------
# contact:check — Vérification de disponibilité (RFC 5733 § 3.1.1)
# ---------------------------------------------------------------------------

def build_contact_check(contact_ids: list[str]) -> str:
    """Construit une commande EPP <contact:check>.

    Args:
        contact_ids: liste d'identifiants contact à vérifier

    Returns:
        Chaîne XML de la commande contact:check.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    check = etree.SubElement(command, "check")
    contact_check = etree.SubElement(check, C("check"))

    for cid in contact_ids:
        etree.SubElement(contact_check, C("id")).text = cid

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# contact:info — Consultation (RFC 5733 § 3.1.2)
# ---------------------------------------------------------------------------

def build_contact_info(
    contact_id: str,
    auth_pw: Optional[str] = None,
) -> str:
    """Construit une commande EPP <contact:info>.

    Args:
        contact_id: identifiant du contact à consulter
        auth_pw: authInfo optionnel

    Returns:
        Chaîne XML de la commande contact:info.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    info = etree.SubElement(command, "info")
    contact_info = etree.SubElement(info, C("info"))

    etree.SubElement(contact_info, C("id")).text = contact_id

    if auth_pw is not None:
        auth_info = etree.SubElement(contact_info, C("authInfo"))
        etree.SubElement(auth_info, C("pw")).text = auth_pw

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# contact:create — Création d'un contact (RFC 5733 § 3.2.1)
# ---------------------------------------------------------------------------

def build_contact_create(
    contact_id: str,
    name: str,
    streets: list[str],
    city: str,
    cc: str,
    auth_pw: str,
    org: Optional[str] = None,
    sp: Optional[str] = None,
    pc: Optional[str] = None,
    postal_type: str = "loc",
    voice: Optional[str] = None,
    fax: Optional[str] = None,
    email: str = "",
) -> str:
    """Construit une commande EPP <contact:create>.

    Args:
        contact_id: identifiant unique du contact (ex: "C-MG-001")
        name: nom complet
        streets: adresse (1 à 3 lignes)
        city: ville
        cc: code pays ISO 3166-1 alpha-2
        auth_pw: mot de passe authInfo du contact
        org: organisation (optionnel)
        sp: état/province (optionnel)
        pc: code postal (optionnel)
        postal_type: "loc" ou "int" (défaut: "loc")
        voice: numéro de téléphone E.164 (ex: "+261.123456789")
        fax: numéro de fax E.164 (optionnel)
        email: adresse email

    Returns:
        Chaîne XML de la commande contact:create.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    create = etree.SubElement(command, "create")
    contact_create = etree.SubElement(create, C("create"))

    etree.SubElement(contact_create, C("id")).text = contact_id

    _build_postal_info(contact_create, postal_type, name, org, streets, city, sp, pc, cc)

    if voice:
        etree.SubElement(contact_create, C("voice")).text = voice
    if fax:
        etree.SubElement(contact_create, C("fax")).text = fax
    if email:
        etree.SubElement(contact_create, C("email")).text = email

    auth_info = etree.SubElement(contact_create, C("authInfo"))
    etree.SubElement(auth_info, C("pw")).text = auth_pw

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# contact:update — Mise à jour (RFC 5733 § 3.2.3)
# ---------------------------------------------------------------------------

def build_contact_update(
    contact_id: str,
    add_statuses: Optional[list[str]] = None,
    rem_statuses: Optional[list[str]] = None,
    new_name: Optional[str] = None,
    new_org: Optional[str] = None,
    new_streets: Optional[list[str]] = None,
    new_city: Optional[str] = None,
    new_cc: Optional[str] = None,
    new_sp: Optional[str] = None,
    new_pc: Optional[str] = None,
    postal_type: str = "loc",
    new_voice: Optional[str] = None,
    new_email: Optional[str] = None,
    new_auth_pw: Optional[str] = None,
) -> str:
    """Construit une commande EPP <contact:update>.

    Args:
        contact_id: identifiant du contact à modifier
        add_statuses: statuts à ajouter
        rem_statuses: statuts à retirer
        new_name: nouveau nom (si postalInfo modifiée)
        new_org: nouvelle organisation
        new_streets: nouvelle adresse
        new_city: nouvelle ville
        new_cc: nouveau code pays
        new_sp: nouvel état/province
        new_pc: nouveau code postal
        postal_type: type de postalInfo modifiée
        new_voice: nouveau numéro de téléphone
        new_email: nouvelle adresse email
        new_auth_pw: nouveau mot de passe authInfo

    Returns:
        Chaîne XML de la commande contact:update.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    update = etree.SubElement(command, "update")
    contact_update = etree.SubElement(update, C("update"))

    etree.SubElement(contact_update, C("id")).text = contact_id

    # Section <add> : ajout de statuts
    if add_statuses:
        add_el = etree.SubElement(contact_update, C("add"))
        for status in add_statuses:
            s_el = etree.SubElement(add_el, C("status"))
            s_el.set("s", status)

    # Section <rem> : retrait de statuts
    if rem_statuses:
        rem_el = etree.SubElement(contact_update, C("rem"))
        for status in rem_statuses:
            s_el = etree.SubElement(rem_el, C("status"))
            s_el.set("s", status)

    # Section <chg> : modification des données
    has_chg = any([
        new_name, new_voice, new_email, new_auth_pw is not None
    ])
    if has_chg:
        chg_el = etree.SubElement(contact_update, C("chg"))

        if new_name and new_streets and new_city and new_cc:
            _build_postal_info(
                chg_el, postal_type, new_name, new_org,
                new_streets, new_city, new_sp, new_pc, new_cc
            )
        if new_voice:
            etree.SubElement(chg_el, C("voice")).text = new_voice
        if new_email:
            etree.SubElement(chg_el, C("email")).text = new_email
        if new_auth_pw is not None:
            auth_info = etree.SubElement(chg_el, C("authInfo"))
            etree.SubElement(auth_info, C("pw")).text = new_auth_pw

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# contact:delete — Suppression (RFC 5733 § 3.2.2)
# ---------------------------------------------------------------------------

def build_contact_delete(contact_id: str) -> str:
    """Construit une commande EPP <contact:delete>.

    Args:
        contact_id: identifiant du contact à supprimer

    Returns:
        Chaîne XML de la commande contact:delete.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    delete = etree.SubElement(command, "delete")
    contact_delete = etree.SubElement(delete, C("delete"))
    etree.SubElement(contact_delete, C("id")).text = contact_id

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# contact:transfer — Transfert (RFC 5733 § 3.2.5)
# ---------------------------------------------------------------------------

def build_contact_transfer(
    contact_id: str,
    op: str,
    auth_pw: Optional[str] = None,
) -> str:
    """Construit une commande EPP <contact:transfer>.

    Args:
        contact_id: identifiant du contact
        op: opération — "request", "approve", "reject", "cancel", "query"
        auth_pw: authInfo du contact (requis pour op=request)

    Returns:
        Chaîne XML de la commande contact:transfer.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    transfer = etree.SubElement(command, "transfer")
    transfer.set("op", op)
    contact_transfer = etree.SubElement(transfer, C("transfer"))

    etree.SubElement(contact_transfer, C("id")).text = contact_id

    if auth_pw is not None:
        auth_info = etree.SubElement(contact_transfer, C("authInfo"))
        etree.SubElement(auth_info, C("pw")).text = auth_pw

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)
