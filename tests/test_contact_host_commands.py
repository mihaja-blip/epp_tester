"""Tests des constructeurs de commandes XML EPP contact et host."""

import pytest
from lxml import etree

from src.epp.contact_commands import (
    build_contact_check,
    build_contact_info,
    build_contact_create,
    build_contact_update,
    build_contact_delete,
    build_contact_transfer,
    CONTACT_NS,
)
from src.epp.host_commands import (
    build_host_check,
    build_host_info,
    build_host_create,
    build_host_update,
    build_host_delete,
    HOST_NS,
)
from src.epp.commands import EPP_NS

EPP = {"epp": EPP_NS, "c": CONTACT_NS, "h": HOST_NS}


def parse_xml(xml_str: str) -> etree._Element:
    return etree.fromstring(xml_str.encode("utf-8"))


# =============================================================================
# Tests contact:*
# =============================================================================

class TestContactCheck:
    def test_valid_xml(self):
        assert parse_xml(build_contact_check(["C-001"])) is not None

    def test_single_contact(self):
        root = parse_xml(build_contact_check(["C-001"]))
        ids = root.findall("epp:command/epp:check/c:check/c:id", EPP)
        assert len(ids) == 1
        assert ids[0].text == "C-001"

    def test_multiple_contacts(self):
        root = parse_xml(build_contact_check(["C-001", "C-002", "C-003"]))
        ids = root.findall("epp:command/epp:check/c:check/c:id", EPP)
        assert len(ids) == 3

    def test_has_cl_trid(self):
        root = parse_xml(build_contact_check(["C-001"]))
        assert root.find("epp:command/epp:clTRID", EPP) is not None


class TestContactInfo:
    def test_valid_xml(self):
        assert parse_xml(build_contact_info("C-001")) is not None

    def test_contact_id(self):
        root = parse_xml(build_contact_info("C-001"))
        cid = root.find("epp:command/epp:info/c:info/c:id", EPP)
        assert cid is not None
        assert cid.text == "C-001"

    def test_no_auth_by_default(self):
        root = parse_xml(build_contact_info("C-001"))
        assert root.find("epp:command/epp:info/c:info/c:authInfo", EPP) is None

    def test_auth_pw_when_provided(self):
        root = parse_xml(build_contact_info("C-001", auth_pw="secret"))
        pw = root.find("epp:command/epp:info/c:info/c:authInfo/c:pw", EPP)
        assert pw is not None
        assert pw.text == "secret"


class TestContactCreate:
    def _sample_create(self):
        return build_contact_create(
            contact_id="C-MG-001",
            name="Jean Dupont",
            streets=["1 Rue de la Paix"],
            city="Antananarivo",
            cc="MG",
            auth_pw="authpw123",
            org="Example Corp",
            pc="101",
            voice="+261.123456789",
            email="jean@example.mg",
        )

    def test_valid_xml(self):
        assert parse_xml(self._sample_create()) is not None

    def test_contact_id(self):
        root = parse_xml(self._sample_create())
        cid = root.find("epp:command/epp:create/c:create/c:id", EPP)
        assert cid.text == "C-MG-001"

    def test_postal_info_name(self):
        root = parse_xml(self._sample_create())
        name = root.find("epp:command/epp:create/c:create/c:postalInfo/c:name", EPP)
        assert name.text == "Jean Dupont"

    def test_postal_info_type(self):
        root = parse_xml(self._sample_create())
        postal = root.find("epp:command/epp:create/c:create/c:postalInfo", EPP)
        assert postal.get("type") == "loc"

    def test_postal_info_cc(self):
        root = parse_xml(self._sample_create())
        cc = root.find("epp:command/epp:create/c:create/c:postalInfo/c:addr/c:cc", EPP)
        assert cc.text == "MG"

    def test_city(self):
        root = parse_xml(self._sample_create())
        city = root.find("epp:command/epp:create/c:create/c:postalInfo/c:addr/c:city", EPP)
        assert city.text == "Antananarivo"

    def test_voice(self):
        root = parse_xml(self._sample_create())
        voice = root.find("epp:command/epp:create/c:create/c:voice", EPP)
        assert voice.text == "+261.123456789"

    def test_email(self):
        root = parse_xml(self._sample_create())
        email = root.find("epp:command/epp:create/c:create/c:email", EPP)
        assert email.text == "jean@example.mg"

    def test_auth_pw(self):
        root = parse_xml(self._sample_create())
        pw = root.find("epp:command/epp:create/c:create/c:authInfo/c:pw", EPP)
        assert pw.text == "authpw123"

    def test_multiple_streets(self):
        xml = build_contact_create(
            "C-001", "Test", ["Line1", "Line2", "Line3"], "City", "MG", "pw"
        )
        root = parse_xml(xml)
        streets = root.findall(
            "epp:command/epp:create/c:create/c:postalInfo/c:addr/c:street", EPP
        )
        assert len(streets) == 3

    def test_max_3_streets(self):
        """Selon RFC 5733, max 3 lignes d'adresse."""
        xml = build_contact_create(
            "C-001", "Test", ["L1", "L2", "L3", "L4", "L5"], "City", "MG", "pw"
        )
        root = parse_xml(xml)
        streets = root.findall(
            "epp:command/epp:create/c:create/c:postalInfo/c:addr/c:street", EPP
        )
        assert len(streets) == 3


class TestContactUpdate:
    def test_valid_xml(self):
        xml = build_contact_update("C-001", new_auth_pw="newpw")
        assert parse_xml(xml) is not None

    def test_contact_id(self):
        root = parse_xml(build_contact_update("C-001"))
        cid = root.find("epp:command/epp:update/c:update/c:id", EPP)
        assert cid.text == "C-001"

    def test_add_status(self):
        root = parse_xml(build_contact_update("C-001", add_statuses=["clientDeleteProhibited"]))
        statuses = root.findall("epp:command/epp:update/c:update/c:add/c:status", EPP)
        assert len(statuses) == 1
        assert statuses[0].get("s") == "clientDeleteProhibited"

    def test_rem_status(self):
        root = parse_xml(build_contact_update("C-001", rem_statuses=["clientHold"]))
        statuses = root.findall("epp:command/epp:update/c:update/c:rem/c:status", EPP)
        assert len(statuses) == 1

    def test_new_auth_pw(self):
        root = parse_xml(build_contact_update("C-001", new_auth_pw="newpw"))
        pw = root.find("epp:command/epp:update/c:update/c:chg/c:authInfo/c:pw", EPP)
        assert pw is not None
        assert pw.text == "newpw"


class TestContactDelete:
    def test_valid_xml(self):
        assert parse_xml(build_contact_delete("C-001")) is not None

    def test_contact_id(self):
        root = parse_xml(build_contact_delete("C-MG-001"))
        cid = root.find("epp:command/epp:delete/c:delete/c:id", EPP)
        assert cid.text == "C-MG-001"


class TestContactTransfer:
    def test_valid_xml(self):
        assert parse_xml(build_contact_transfer("C-001", "request", "pw")) is not None

    def test_op_attribute(self):
        root = parse_xml(build_contact_transfer("C-001", "approve"))
        transfer = root.find("epp:command/epp:transfer", EPP)
        assert transfer.get("op") == "approve"

    def test_auth_pw(self):
        root = parse_xml(build_contact_transfer("C-001", "request", "authpw"))
        pw = root.find("epp:command/epp:transfer/c:transfer/c:authInfo/c:pw", EPP)
        assert pw.text == "authpw"


# =============================================================================
# Tests host:*
# =============================================================================

class TestHostCheck:
    def test_valid_xml(self):
        assert parse_xml(build_host_check(["ns1.example.mg"])) is not None

    def test_single_host(self):
        root = parse_xml(build_host_check(["ns1.example.mg"]))
        names = root.findall("epp:command/epp:check/h:check/h:name", EPP)
        assert len(names) == 1
        assert names[0].text == "ns1.example.mg"

    def test_multiple_hosts(self):
        root = parse_xml(build_host_check(["ns1.ex.mg", "ns2.ex.mg"]))
        names = root.findall("epp:command/epp:check/h:check/h:name", EPP)
        assert len(names) == 2

    def test_has_cl_trid(self):
        root = parse_xml(build_host_check(["ns1.mg"]))
        assert root.find("epp:command/epp:clTRID", EPP) is not None


class TestHostInfo:
    def test_valid_xml(self):
        assert parse_xml(build_host_info("ns1.example.mg")) is not None

    def test_host_name(self):
        root = parse_xml(build_host_info("ns1.example.mg"))
        name = root.find("epp:command/epp:info/h:info/h:name", EPP)
        assert name.text == "ns1.example.mg"


class TestHostCreate:
    def test_valid_xml(self):
        assert parse_xml(build_host_create("ns1.example.mg")) is not None

    def test_host_name(self):
        root = parse_xml(build_host_create("ns1.example.mg"))
        name = root.find("epp:command/epp:create/h:create/h:name", EPP)
        assert name.text == "ns1.example.mg"

    def test_no_addresses_by_default(self):
        root = parse_xml(build_host_create("ns1.example.mg"))
        addrs = root.findall("epp:command/epp:create/h:create/h:addr", EPP)
        assert len(addrs) == 0

    def test_ipv4_addresses(self):
        root = parse_xml(build_host_create("ns1.mg", ipv4_addresses=["196.0.4.1"]))
        addrs = root.findall("epp:command/epp:create/h:create/h:addr", EPP)
        assert len(addrs) == 1
        assert addrs[0].get("ip") == "v4"
        assert addrs[0].text == "196.0.4.1"

    def test_ipv6_addresses(self):
        root = parse_xml(build_host_create("ns1.mg", ipv6_addresses=["2001:db8::1"]))
        addrs = root.findall("epp:command/epp:create/h:create/h:addr", EPP)
        assert len(addrs) == 1
        assert addrs[0].get("ip") == "v6"

    def test_mixed_addresses(self):
        root = parse_xml(build_host_create(
            "ns1.mg",
            ipv4_addresses=["196.0.4.1", "196.0.4.2"],
            ipv6_addresses=["2001:db8::1"],
        ))
        addrs = root.findall("epp:command/epp:create/h:create/h:addr", EPP)
        assert len(addrs) == 3
        ip_types = [a.get("ip") for a in addrs]
        assert ip_types.count("v4") == 2
        assert ip_types.count("v6") == 1


class TestHostUpdate:
    def test_valid_xml(self):
        assert parse_xml(build_host_update("ns1.mg", new_name="ns1-new.mg")) is not None

    def test_host_name(self):
        root = parse_xml(build_host_update("ns1.mg"))
        name = root.find("epp:command/epp:update/h:update/h:name", EPP)
        assert name.text == "ns1.mg"

    def test_add_ipv4(self):
        root = parse_xml(build_host_update("ns1.mg", add_ipv4=["1.2.3.4"]))
        addrs = root.findall("epp:command/epp:update/h:update/h:add/h:addr", EPP)
        assert addrs[0].get("ip") == "v4"
        assert addrs[0].text == "1.2.3.4"

    def test_rem_ipv4(self):
        root = parse_xml(build_host_update("ns1.mg", rem_ipv4=["1.2.3.4"]))
        addrs = root.findall("epp:command/epp:update/h:update/h:rem/h:addr", EPP)
        assert len(addrs) == 1

    def test_rename(self):
        root = parse_xml(build_host_update("ns1.mg", new_name="ns1-new.mg"))
        new_name = root.find("epp:command/epp:update/h:update/h:chg/h:name", EPP)
        assert new_name is not None
        assert new_name.text == "ns1-new.mg"

    def test_add_status(self):
        root = parse_xml(build_host_update("ns1.mg", add_statuses=["clientDeleteProhibited"]))
        statuses = root.findall("epp:command/epp:update/h:update/h:add/h:status", EPP)
        assert statuses[0].get("s") == "clientDeleteProhibited"


class TestHostDelete:
    def test_valid_xml(self):
        assert parse_xml(build_host_delete("ns1.mg")) is not None

    def test_host_name(self):
        root = parse_xml(build_host_delete("ns1.example.mg"))
        name = root.find("epp:command/epp:delete/h:delete/h:name", EPP)
        assert name.text == "ns1.example.mg"
