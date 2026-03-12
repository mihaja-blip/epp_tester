"""
Constructeurs de commandes XML EPP pour les objets host (RFC 5732).

Les hôtes EPP représentent les serveurs de noms (nameservers) gérés
par le registre (hôtes délégués ou sous-délégués).
"""

from typing import Optional
from lxml import etree

from src.epp.commands import EPP_NS, _new_cltr_id, _to_xml_str

# Namespace host EPP (RFC 5732)
HOST_NS = "urn:ietf:params:xml:ns:host-1.0"

_NSMAP = {None: EPP_NS, "host": HOST_NS}

# Types d'adresse IP valides pour les hôtes EPP
IP_TYPE_V4 = "v4"
IP_TYPE_V6 = "v6"


def H(tag: str) -> str:
    """Raccourci Clark notation pour les éléments du namespace host."""
    return f"{{{HOST_NS}}}{tag}"


def _epp_root() -> etree._Element:
    """Crée l'élément racine <epp> avec les namespaces EPP et host."""
    return etree.Element("epp", nsmap=_NSMAP)


# ---------------------------------------------------------------------------
# host:check — Vérification de disponibilité (RFC 5732 § 3.1.1)
# ---------------------------------------------------------------------------

def build_host_check(names: list[str]) -> str:
    """Construit une commande EPP <host:check>.

    Args:
        names: liste de noms d'hôtes à vérifier (ex: ["ns1.example.mg"])

    Returns:
        Chaîne XML de la commande host:check.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    check = etree.SubElement(command, "check")
    host_check = etree.SubElement(check, H("check"))

    for name in names:
        etree.SubElement(host_check, H("name")).text = name

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# host:info — Consultation (RFC 5732 § 3.1.2)
# ---------------------------------------------------------------------------

def build_host_info(name: str) -> str:
    """Construit une commande EPP <host:info>.

    Args:
        name: nom de l'hôte à consulter

    Returns:
        Chaîne XML de la commande host:info.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    info = etree.SubElement(command, "info")
    host_info = etree.SubElement(info, H("info"))
    etree.SubElement(host_info, H("name")).text = name

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# host:create — Création d'un hôte (RFC 5732 § 3.2.1)
# ---------------------------------------------------------------------------

def build_host_create(
    name: str,
    ipv4_addresses: Optional[list[str]] = None,
    ipv6_addresses: Optional[list[str]] = None,
) -> str:
    """Construit une commande EPP <host:create>.

    Les adresses IP ne sont requises que pour les hôtes délégués (glue records),
    c'est-à-dire les hôtes dont le nom est sous le domaine qu'ils servent.

    Args:
        name: nom de l'hôte à créer (ex: "ns1.example.mg")
        ipv4_addresses: liste d'adresses IPv4 (ex: ["196.0.4.1"])
        ipv6_addresses: liste d'adresses IPv6 (ex: ["2001:db8::1"])

    Returns:
        Chaîne XML de la commande host:create.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    create = etree.SubElement(command, "create")
    host_create = etree.SubElement(create, H("create"))

    etree.SubElement(host_create, H("name")).text = name

    # Adresses IPv4
    if ipv4_addresses:
        for addr in ipv4_addresses:
            addr_el = etree.SubElement(host_create, H("addr"))
            addr_el.set("ip", IP_TYPE_V4)
            addr_el.text = addr

    # Adresses IPv6
    if ipv6_addresses:
        for addr in ipv6_addresses:
            addr_el = etree.SubElement(host_create, H("addr"))
            addr_el.set("ip", IP_TYPE_V6)
            addr_el.text = addr

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# host:update — Mise à jour d'un hôte (RFC 5732 § 3.2.3)
# ---------------------------------------------------------------------------

def build_host_update(
    name: str,
    add_ipv4: Optional[list[str]] = None,
    add_ipv6: Optional[list[str]] = None,
    rem_ipv4: Optional[list[str]] = None,
    rem_ipv6: Optional[list[str]] = None,
    add_statuses: Optional[list[str]] = None,
    rem_statuses: Optional[list[str]] = None,
    new_name: Optional[str] = None,
) -> str:
    """Construit une commande EPP <host:update>.

    Args:
        name: nom de l'hôte à modifier
        add_ipv4: adresses IPv4 à ajouter
        add_ipv6: adresses IPv6 à ajouter
        rem_ipv4: adresses IPv4 à retirer
        rem_ipv6: adresses IPv6 à retirer
        add_statuses: statuts à ajouter (ex: ["clientDeleteProhibited"])
        rem_statuses: statuts à retirer
        new_name: nouveau nom de l'hôte (renommage)

    Returns:
        Chaîne XML de la commande host:update.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    update = etree.SubElement(command, "update")
    host_update = etree.SubElement(update, H("update"))

    etree.SubElement(host_update, H("name")).text = name

    # Section <add> : ajout d'adresses et statuts
    add_items = bool(add_ipv4 or add_ipv6 or add_statuses)
    if add_items:
        add_el = etree.SubElement(host_update, H("add"))
        if add_ipv4:
            for addr in add_ipv4:
                a = etree.SubElement(add_el, H("addr"))
                a.set("ip", IP_TYPE_V4)
                a.text = addr
        if add_ipv6:
            for addr in add_ipv6:
                a = etree.SubElement(add_el, H("addr"))
                a.set("ip", IP_TYPE_V6)
                a.text = addr
        if add_statuses:
            for status in add_statuses:
                s = etree.SubElement(add_el, H("status"))
                s.set("s", status)

    # Section <rem> : retrait d'adresses et statuts
    rem_items = bool(rem_ipv4 or rem_ipv6 or rem_statuses)
    if rem_items:
        rem_el = etree.SubElement(host_update, H("rem"))
        if rem_ipv4:
            for addr in rem_ipv4:
                a = etree.SubElement(rem_el, H("addr"))
                a.set("ip", IP_TYPE_V4)
                a.text = addr
        if rem_ipv6:
            for addr in rem_ipv6:
                a = etree.SubElement(rem_el, H("addr"))
                a.set("ip", IP_TYPE_V6)
                a.text = addr
        if rem_statuses:
            for status in rem_statuses:
                s = etree.SubElement(rem_el, H("status"))
                s.set("s", status)

    # Section <chg> : renommage de l'hôte
    if new_name:
        chg_el = etree.SubElement(host_update, H("chg"))
        etree.SubElement(chg_el, H("name")).text = new_name

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)


# ---------------------------------------------------------------------------
# host:delete — Suppression d'un hôte (RFC 5732 § 3.2.2)
# ---------------------------------------------------------------------------

def build_host_delete(name: str) -> str:
    """Construit une commande EPP <host:delete>.

    Un hôte ne peut être supprimé que s'il n'est plus référencé
    par aucun domaine (erreur 2305 sinon).

    Args:
        name: nom de l'hôte à supprimer

    Returns:
        Chaîne XML de la commande host:delete.
    """
    root = _epp_root()
    command = etree.SubElement(root, "command")
    delete = etree.SubElement(command, "delete")
    host_delete = etree.SubElement(delete, H("delete"))
    etree.SubElement(host_delete, H("name")).text = name

    cl_trid = etree.SubElement(command, "clTRID")
    cl_trid.text = _new_cltr_id()
    return _to_xml_str(root)
