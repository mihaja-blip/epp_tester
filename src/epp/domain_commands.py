"""
Constructeurs de commandes XML EPP pour les objets domaine (RFC 5731).

Toutes les fonctions retournent une chaîne XML valide avec les namespaces
EPP et domain corrects, prête à être envoyée via EppClient.
"""

from typing import Optional
from lxml import etree

from src.epp.commands import EPP_NS, _new_cltr_id, _to_xml_str

# Namespace domaine EPP (RFC 5731)
DOMAIN_NS = "urn:ietf:params:xml:ns:domain-1.0"

# Map des namespaces pour les commandes domaine
_NSMAP = {None: EPP_NS, "domain": DOMAIN_NS}


def D(tag: str) -> str:
    """Raccourci Clark notation pour les éléments du namespace domain."""
    return f"{{{DOMAIN_NS}}}{tag}"


def _epp_root() -> etree._Element:
    """Crée l'élément racine <epp> avec les namespaces EPP et domain."""
    return etree.Element("epp", nsmap=_NSMAP)


# ---------------------------------------------------------------------------
# domain:check — Vérification de disponibilité (RFC 5731 § 3.1.1)
# ---------------------------------------------------------------------------

def build_domain_check(names: list[str]) -> str:
    """Construit une commande EPP <domain:check> pour vérifier la disponibilité.

    Args:
        names: liste de noms de domaine à vérifier (ex: ["example.mg", "test.mg"])

    Returns:
        Chaîne XML de la commande domain:check.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    check = etree.SubElement(command, "check")
    domain_check = etree.SubElement(check, D("check"))

    for name in names:
        name_el = etree.SubElement(domain_check, D("name"))
        name_el.text = name

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# domain:info — Consultation des informations (RFC 5731 § 3.1.2)
# ---------------------------------------------------------------------------

def build_domain_info(
    name: str,
    hosts: str = "all",
    auth_pw: Optional[str] = None,
) -> str:
    """Construit une commande EPP <domain:info>.

    Args:
        name: nom de domaine à consulter
        hosts: mode d'inclusion des hôtes : "all", "del", "sub", "none"
        auth_pw: authInfo optionnel (requis si le domaine appartient à un autre registrar)

    Returns:
        Chaîne XML de la commande domain:info.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    info = etree.SubElement(command, "info")
    domain_info = etree.SubElement(info, D("info"))

    name_el = etree.SubElement(domain_info, D("name"))
    name_el.text = name
    name_el.set("hosts", hosts)

    if auth_pw is not None:
        auth_info = etree.SubElement(domain_info, D("authInfo"))
        pw_el = etree.SubElement(auth_info, D("pw"))
        pw_el.text = auth_pw

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# domain:create — Création d'un domaine (RFC 5731 § 3.2.1)
# ---------------------------------------------------------------------------

def build_domain_create(
    name: str,
    period: int = 1,
    period_unit: str = "y",
    ns_hosts: Optional[list[str]] = None,
    registrant: Optional[str] = None,
    admin_contact: Optional[str] = None,
    tech_contact: Optional[str] = None,
    billing_contact: Optional[str] = None,
    auth_pw: str = "",
) -> str:
    """Construit une commande EPP <domain:create>.

    Args:
        name: nom de domaine à créer
        period: durée d'enregistrement (défaut: 1)
        period_unit: unité de durée — "y" (années) ou "m" (mois)
        ns_hosts: liste des serveurs de noms (hostObj, ex: ["ns1.example.mg"])
        registrant: identifiant du contact registrant
        admin_contact: identifiant du contact administratif
        tech_contact: identifiant du contact technique
        billing_contact: identifiant du contact facturation (optionnel)
        auth_pw: mot de passe authInfo du domaine

    Returns:
        Chaîne XML de la commande domain:create.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    create = etree.SubElement(command, "create")
    domain_create = etree.SubElement(create, D("create"))

    # Nom de domaine
    name_el = etree.SubElement(domain_create, D("name"))
    name_el.text = name

    # Période d'enregistrement
    period_el = etree.SubElement(domain_create, D("period"))
    period_el.set("unit", period_unit)
    period_el.text = str(period)

    # Serveurs de noms (NS)
    if ns_hosts:
        ns_el = etree.SubElement(domain_create, D("ns"))
        for host in ns_hosts:
            host_obj = etree.SubElement(ns_el, D("hostObj"))
            host_obj.text = host

    # Contact registrant
    if registrant:
        registrant_el = etree.SubElement(domain_create, D("registrant"))
        registrant_el.text = registrant

    # Contacts associés
    for contact_type, contact_id in [
        ("admin", admin_contact),
        ("tech", tech_contact),
        ("billing", billing_contact),
    ]:
        if contact_id:
            contact_el = etree.SubElement(domain_create, D("contact"))
            contact_el.set("type", contact_type)
            contact_el.text = contact_id

    # AuthInfo (mot de passe du domaine)
    auth_info = etree.SubElement(domain_create, D("authInfo"))
    pw_el = etree.SubElement(auth_info, D("pw"))
    pw_el.text = auth_pw

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# domain:update — Mise à jour d'un domaine (RFC 5731 § 3.2.3)
# ---------------------------------------------------------------------------

def build_domain_update(
    name: str,
    add_ns: Optional[list[str]] = None,
    rem_ns: Optional[list[str]] = None,
    add_statuses: Optional[list[str]] = None,
    rem_statuses: Optional[list[str]] = None,
    add_contacts: Optional[list[tuple[str, str]]] = None,
    rem_contacts: Optional[list[tuple[str, str]]] = None,
    new_registrant: Optional[str] = None,
    new_auth_pw: Optional[str] = None,
) -> str:
    """Construit une commande EPP <domain:update>.

    Args:
        name: nom de domaine à modifier
        add_ns: serveurs de noms à ajouter (hostObj)
        rem_ns: serveurs de noms à retirer
        add_statuses: statuts à ajouter (ex: ["clientHold"])
        rem_statuses: statuts à retirer
        add_contacts: contacts à ajouter [(type, id), ...] ex: [("tech", "C-001")]
        rem_contacts: contacts à retirer
        new_registrant: nouveau registrant
        new_auth_pw: nouveau mot de passe authInfo

    Returns:
        Chaîne XML de la commande domain:update.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    update = etree.SubElement(command, "update")
    domain_update = etree.SubElement(update, D("update"))

    name_el = etree.SubElement(domain_update, D("name"))
    name_el.text = name

    # Section <add> : ajout de NS, contacts, statuts
    add_items = bool(add_ns or add_statuses or add_contacts)
    if add_items:
        add_el = etree.SubElement(domain_update, D("add"))
        if add_ns:
            ns_el = etree.SubElement(add_el, D("ns"))
            for host in add_ns:
                etree.SubElement(ns_el, D("hostObj")).text = host
        if add_contacts:
            for ctype, cid in add_contacts:
                c_el = etree.SubElement(add_el, D("contact"))
                c_el.set("type", ctype)
                c_el.text = cid
        if add_statuses:
            for status in add_statuses:
                s_el = etree.SubElement(add_el, D("status"))
                s_el.set("s", status)

    # Section <rem> : retrait de NS, contacts, statuts
    rem_items = bool(rem_ns or rem_statuses or rem_contacts)
    if rem_items:
        rem_el = etree.SubElement(domain_update, D("rem"))
        if rem_ns:
            ns_el = etree.SubElement(rem_el, D("ns"))
            for host in rem_ns:
                etree.SubElement(ns_el, D("hostObj")).text = host
        if rem_contacts:
            for ctype, cid in rem_contacts:
                c_el = etree.SubElement(rem_el, D("contact"))
                c_el.set("type", ctype)
                c_el.text = cid
        if rem_statuses:
            for status in rem_statuses:
                s_el = etree.SubElement(rem_el, D("status"))
                s_el.set("s", status)

    # Section <chg> : modification de registrant ou authInfo
    chg_items = bool(new_registrant or new_auth_pw is not None)
    if chg_items:
        chg_el = etree.SubElement(domain_update, D("chg"))
        if new_registrant:
            etree.SubElement(chg_el, D("registrant")).text = new_registrant
        if new_auth_pw is not None:
            auth_info = etree.SubElement(chg_el, D("authInfo"))
            etree.SubElement(auth_info, D("pw")).text = new_auth_pw

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# domain:delete — Suppression d'un domaine (RFC 5731 § 3.2.2)
# ---------------------------------------------------------------------------

def build_domain_delete(name: str) -> str:
    """Construit une commande EPP <domain:delete>.

    Args:
        name: nom de domaine à supprimer

    Returns:
        Chaîne XML de la commande domain:delete.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    delete = etree.SubElement(command, "delete")
    domain_delete = etree.SubElement(delete, D("delete"))
    etree.SubElement(domain_delete, D("name")).text = name

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# domain:renew — Renouvellement d'un domaine (RFC 5731 § 3.2.4)
# ---------------------------------------------------------------------------

def build_domain_renew(
    name: str,
    cur_exp_date: str,
    period: int = 1,
    period_unit: str = "y",
) -> str:
    """Construit une commande EPP <domain:renew>.

    Args:
        name: nom de domaine à renouveler
        cur_exp_date: date d'expiration courante au format YYYY-MM-DD
        period: durée de renouvellement (défaut: 1)
        period_unit: unité — "y" (années) ou "m" (mois)

    Returns:
        Chaîne XML de la commande domain:renew.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    renew = etree.SubElement(command, "renew")
    domain_renew = etree.SubElement(renew, D("renew"))

    etree.SubElement(domain_renew, D("name")).text = name

    exp_el = etree.SubElement(domain_renew, D("curExpDate"))
    exp_el.text = cur_exp_date

    period_el = etree.SubElement(domain_renew, D("period"))
    period_el.set("unit", period_unit)
    period_el.text = str(period)

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# domain:transfer — Transfert de registrar (RFC 5731 § 3.2.5)
# ---------------------------------------------------------------------------

def build_domain_transfer(
    name: str,
    op: str,
    auth_pw: Optional[str] = None,
    period: Optional[int] = None,
    period_unit: str = "y",
) -> str:
    """Construit une commande EPP <domain:transfer>.

    Args:
        name: nom de domaine
        op: opération — "request", "approve", "reject", "cancel", "query"
        auth_pw: authInfo du domaine (requis pour op=request)
        period: durée supplémentaire lors du transfert (optionnel)
        period_unit: unité de la période — "y" ou "m"

    Returns:
        Chaîne XML de la commande domain:transfer.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    transfer = etree.SubElement(command, "transfer")
    transfer.set("op", op)
    domain_transfer = etree.SubElement(transfer, D("transfer"))

    etree.SubElement(domain_transfer, D("name")).text = name

    if period is not None:
        period_el = etree.SubElement(domain_transfer, D("period"))
        period_el.set("unit", period_unit)
        period_el.text = str(period)

    if auth_pw is not None:
        auth_info = etree.SubElement(domain_transfer, D("authInfo"))
        etree.SubElement(auth_info, D("pw")).text = auth_pw

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)
