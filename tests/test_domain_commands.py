"""Tests des constructeurs de commandes XML EPP domaine (RFC 5731)."""

import pytest
from lxml import etree

from src.epp.domain_commands import (
    build_domain_check,
    build_domain_info,
    build_domain_create,
    build_domain_update,
    build_domain_delete,
    build_domain_renew,
    build_domain_transfer,
    DOMAIN_NS,
)
from src.epp.commands import EPP_NS

EPP_NS_MAP = {"epp": EPP_NS, "d": DOMAIN_NS}


def parse_xml(xml_str: str) -> etree._Element:
    return etree.fromstring(xml_str.encode("utf-8"))


class TestDomainCheck:
    def test_is_valid_xml(self):
        assert parse_xml(build_domain_check(["example.mg"])) is not None

    def test_has_check_element(self):
        root = parse_xml(build_domain_check(["example.mg"]))
        assert root.find("epp:command/epp:check", EPP_NS_MAP) is not None

    def test_single_domain(self):
        root = parse_xml(build_domain_check(["example.mg"]))
        names = root.findall("epp:command/epp:check/d:check/d:name", EPP_NS_MAP)
        assert len(names) == 1
        assert names[0].text == "example.mg"

    def test_multiple_domains(self):
        root = parse_xml(build_domain_check(["a.mg", "b.mg", "c.mg"]))
        names = root.findall("epp:command/epp:check/d:check/d:name", EPP_NS_MAP)
        assert len(names) == 3
        assert [n.text for n in names] == ["a.mg", "b.mg", "c.mg"]

    def test_has_cl_trid(self):
        root = parse_xml(build_domain_check(["x.mg"]))
        assert root.find("epp:command/epp:clTRID", EPP_NS_MAP) is not None


class TestDomainInfo:
    def test_is_valid_xml(self):
        assert parse_xml(build_domain_info("example.mg")) is not None

    def test_has_info_element(self):
        root = parse_xml(build_domain_info("example.mg"))
        assert root.find("epp:command/epp:info", EPP_NS_MAP) is not None

    def test_domain_name(self):
        root = parse_xml(build_domain_info("example.mg"))
        name = root.find("epp:command/epp:info/d:info/d:name", EPP_NS_MAP)
        assert name is not None
        assert name.text == "example.mg"

    def test_default_hosts_all(self):
        root = parse_xml(build_domain_info("example.mg"))
        name = root.find("epp:command/epp:info/d:info/d:name", EPP_NS_MAP)
        assert name.get("hosts") == "all"

    def test_custom_hosts(self):
        root = parse_xml(build_domain_info("example.mg", hosts="del"))
        name = root.find("epp:command/epp:info/d:info/d:name", EPP_NS_MAP)
        assert name.get("hosts") == "del"

    def test_no_auth_pw_by_default(self):
        root = parse_xml(build_domain_info("example.mg"))
        assert root.find("epp:command/epp:info/d:info/d:authInfo", EPP_NS_MAP) is None

    def test_auth_pw_when_provided(self):
        root = parse_xml(build_domain_info("example.mg", auth_pw="secret"))
        pw = root.find("epp:command/epp:info/d:info/d:authInfo/d:pw", EPP_NS_MAP)
        assert pw is not None
        assert pw.text == "secret"


class TestDomainCreate:
    def test_is_valid_xml(self):
        xml = build_domain_create("example.mg", auth_pw="authpw")
        assert parse_xml(xml) is not None

    def test_has_create_element(self):
        root = parse_xml(build_domain_create("example.mg", auth_pw="pw"))
        assert root.find("epp:command/epp:create", EPP_NS_MAP) is not None

    def test_domain_name(self):
        root = parse_xml(build_domain_create("test.mg", auth_pw="pw"))
        name = root.find("epp:command/epp:create/d:create/d:name", EPP_NS_MAP)
        assert name is not None
        assert name.text == "test.mg"

    def test_period_default(self):
        root = parse_xml(build_domain_create("x.mg", auth_pw="pw"))
        period = root.find("epp:command/epp:create/d:create/d:period", EPP_NS_MAP)
        assert period is not None
        assert period.text == "1"
        assert period.get("unit") == "y"

    def test_period_custom(self):
        root = parse_xml(build_domain_create("x.mg", period=2, period_unit="y", auth_pw="pw"))
        period = root.find("epp:command/epp:create/d:create/d:period", EPP_NS_MAP)
        assert period.text == "2"

    def test_ns_hosts(self):
        root = parse_xml(build_domain_create(
            "x.mg", ns_hosts=["ns1.example.mg", "ns2.example.mg"], auth_pw="pw"
        ))
        hosts = root.findall("epp:command/epp:create/d:create/d:ns/d:hostObj", EPP_NS_MAP)
        assert len(hosts) == 2
        assert hosts[0].text == "ns1.example.mg"

    def test_registrant(self):
        root = parse_xml(build_domain_create("x.mg", registrant="C-001", auth_pw="pw"))
        reg = root.find("epp:command/epp:create/d:create/d:registrant", EPP_NS_MAP)
        assert reg is not None
        assert reg.text == "C-001"

    def test_contacts(self):
        root = parse_xml(build_domain_create(
            "x.mg", admin_contact="C-ADM", tech_contact="C-TECH", auth_pw="pw"
        ))
        contacts = root.findall("epp:command/epp:create/d:create/d:contact", EPP_NS_MAP)
        types = {c.get("type"): c.text for c in contacts}
        assert types.get("admin") == "C-ADM"
        assert types.get("tech") == "C-TECH"

    def test_auth_pw(self):
        root = parse_xml(build_domain_create("x.mg", auth_pw="myauthpw"))
        pw = root.find("epp:command/epp:create/d:create/d:authInfo/d:pw", EPP_NS_MAP)
        assert pw is not None
        assert pw.text == "myauthpw"

    def test_has_cl_trid(self):
        root = parse_xml(build_domain_create("x.mg", auth_pw="pw"))
        assert root.find("epp:command/epp:clTRID", EPP_NS_MAP) is not None


class TestDomainUpdate:
    def test_is_valid_xml(self):
        xml = build_domain_update("example.mg", new_auth_pw="newpw")
        assert parse_xml(xml) is not None

    def test_name(self):
        root = parse_xml(build_domain_update("example.mg"))
        name = root.find("epp:command/epp:update/d:update/d:name", EPP_NS_MAP)
        assert name.text == "example.mg"

    def test_add_ns(self):
        root = parse_xml(build_domain_update("x.mg", add_ns=["ns3.example.mg"]))
        hosts = root.findall("epp:command/epp:update/d:update/d:add/d:ns/d:hostObj", EPP_NS_MAP)
        assert len(hosts) == 1
        assert hosts[0].text == "ns3.example.mg"

    def test_rem_ns(self):
        root = parse_xml(build_domain_update("x.mg", rem_ns=["ns1.old.mg"]))
        hosts = root.findall("epp:command/epp:update/d:update/d:rem/d:ns/d:hostObj", EPP_NS_MAP)
        assert len(hosts) == 1

    def test_add_status(self):
        root = parse_xml(build_domain_update("x.mg", add_statuses=["clientHold"]))
        statuses = root.findall("epp:command/epp:update/d:update/d:add/d:status", EPP_NS_MAP)
        assert len(statuses) == 1
        assert statuses[0].get("s") == "clientHold"

    def test_new_auth_pw(self):
        root = parse_xml(build_domain_update("x.mg", new_auth_pw="newpw"))
        pw = root.find("epp:command/epp:update/d:update/d:chg/d:authInfo/d:pw", EPP_NS_MAP)
        assert pw is not None
        assert pw.text == "newpw"

    def test_no_sections_when_nothing(self):
        """Sans paramètres, les sections add/rem/chg ne doivent pas apparaître."""
        root = parse_xml(build_domain_update("x.mg"))
        assert root.find("epp:command/epp:update/d:update/d:add", EPP_NS_MAP) is None
        assert root.find("epp:command/epp:update/d:update/d:rem", EPP_NS_MAP) is None
        assert root.find("epp:command/epp:update/d:update/d:chg", EPP_NS_MAP) is None


class TestDomainDelete:
    def test_is_valid_xml(self):
        assert parse_xml(build_domain_delete("example.mg")) is not None

    def test_delete_element(self):
        root = parse_xml(build_domain_delete("example.mg"))
        assert root.find("epp:command/epp:delete", EPP_NS_MAP) is not None

    def test_domain_name(self):
        root = parse_xml(build_domain_delete("test.mg"))
        name = root.find("epp:command/epp:delete/d:delete/d:name", EPP_NS_MAP)
        assert name is not None
        assert name.text == "test.mg"


class TestDomainRenew:
    def test_is_valid_xml(self):
        xml = build_domain_renew("example.mg", "2024-12-31")
        assert parse_xml(xml) is not None

    def test_domain_name(self):
        root = parse_xml(build_domain_renew("example.mg", "2024-12-31"))
        name = root.find("epp:command/epp:renew/d:renew/d:name", EPP_NS_MAP)
        assert name.text == "example.mg"

    def test_cur_exp_date(self):
        root = parse_xml(build_domain_renew("x.mg", "2025-06-30"))
        exp = root.find("epp:command/epp:renew/d:renew/d:curExpDate", EPP_NS_MAP)
        assert exp.text == "2025-06-30"

    def test_period(self):
        root = parse_xml(build_domain_renew("x.mg", "2024-12-31", period=2))
        period = root.find("epp:command/epp:renew/d:renew/d:period", EPP_NS_MAP)
        assert period.text == "2"
        assert period.get("unit") == "y"


class TestDomainTransfer:
    def test_is_valid_xml(self):
        xml = build_domain_transfer("example.mg", "request", auth_pw="pw")
        assert parse_xml(xml) is not None

    def test_op_attribute(self):
        root = parse_xml(build_domain_transfer("x.mg", "request"))
        transfer = root.find("epp:command/epp:transfer", EPP_NS_MAP)
        assert transfer.get("op") == "request"

    def test_domain_name(self):
        root = parse_xml(build_domain_transfer("example.mg", "query"))
        name = root.find("epp:command/epp:transfer/d:transfer/d:name", EPP_NS_MAP)
        assert name.text == "example.mg"

    def test_auth_pw(self):
        root = parse_xml(build_domain_transfer("x.mg", "request", auth_pw="authsecret"))
        pw = root.find("epp:command/epp:transfer/d:transfer/d:authInfo/d:pw", EPP_NS_MAP)
        assert pw is not None
        assert pw.text == "authsecret"

    def test_approve_no_auth_pw(self):
        xml = build_domain_transfer("x.mg", "approve")
        root = parse_xml(xml)
        assert root.find("epp:command/epp:transfer/d:transfer/d:authInfo", EPP_NS_MAP) is None

    def test_all_ops_valid(self):
        for op in ["request", "approve", "reject", "cancel", "query"]:
            xml = build_domain_transfer("x.mg", op)
            root = parse_xml(xml)
            assert root.find("epp:command/epp:transfer", EPP_NS_MAP).get("op") == op
