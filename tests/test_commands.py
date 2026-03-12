"""Tests des constructeurs de commandes XML EPP."""

import pytest
from lxml import etree

from src.epp.commands import (
    build_hello,
    build_login,
    build_logout,
    build_poll_request,
    build_poll_ack,
    EPP_NS,
)

NS = {"epp": EPP_NS}


def parse_xml(xml_str: str) -> etree._Element:
    """Parse un XML et retourne l'élément racine."""
    return etree.fromstring(xml_str.encode("utf-8"))


class TestBuildHello:
    def test_hello_is_valid_xml(self):
        xml = build_hello()
        root = parse_xml(xml)
        assert root is not None

    def test_hello_has_epp_namespace(self):
        xml = build_hello()
        root = parse_xml(xml)
        assert root.tag == f"{{{EPP_NS}}}epp"

    def test_hello_contains_hello_element(self):
        xml = build_hello()
        root = parse_xml(xml)
        hello_el = root.find("epp:hello", NS)
        assert hello_el is not None

    def test_hello_no_command_element(self):
        """<hello> n'est pas une commande — pas de <command> wrapping."""
        xml = build_hello()
        root = parse_xml(xml)
        assert root.find("epp:command", NS) is None


class TestBuildLogin:
    def test_login_is_valid_xml(self):
        xml = build_login("reg001", "password123")
        root = parse_xml(xml)
        assert root is not None

    def test_login_has_correct_namespace(self):
        xml = build_login("reg001", "password123")
        root = parse_xml(xml)
        assert root.tag == f"{{{EPP_NS}}}epp"

    def test_login_contains_command(self):
        xml = build_login("reg001", "password123")
        root = parse_xml(xml)
        assert root.find("epp:command", NS) is not None

    def test_login_contains_login_element(self):
        xml = build_login("reg001", "password123")
        root = parse_xml(xml)
        assert root.find("epp:command/epp:login", NS) is not None

    def test_login_cl_id(self):
        xml = build_login("registrar-001", "pwd")
        root = parse_xml(xml)
        cl_id = root.find("epp:command/epp:login/epp:clID", NS)
        assert cl_id is not None
        assert cl_id.text == "registrar-001"

    def test_login_pw_present(self):
        xml = build_login("reg", "secret_pw")
        root = parse_xml(xml)
        pw = root.find("epp:command/epp:login/epp:pw", NS)
        assert pw is not None
        assert pw.text == "secret_pw"

    def test_login_new_pw_optional(self):
        """newPW ne doit pas apparaître si non fourni."""
        xml = build_login("reg", "pwd")
        root = parse_xml(xml)
        assert root.find("epp:command/epp:login/epp:newPW", NS) is None

    def test_login_new_pw_when_provided(self):
        xml = build_login("reg", "old_pwd", new_password="new_pwd")
        root = parse_xml(xml)
        new_pw = root.find("epp:command/epp:login/epp:newPW", NS)
        assert new_pw is not None
        assert new_pw.text == "new_pwd"

    def test_login_version(self):
        xml = build_login("reg", "pwd", version="1.0")
        root = parse_xml(xml)
        version = root.find("epp:command/epp:login/epp:options/epp:version", NS)
        assert version is not None
        assert version.text == "1.0"

    def test_login_lang(self):
        xml = build_login("reg", "pwd", lang="fr")
        root = parse_xml(xml)
        lang = root.find("epp:command/epp:login/epp:options/epp:lang", NS)
        assert lang is not None
        assert lang.text == "fr"

    def test_login_default_obj_uris(self):
        xml = build_login("reg", "pwd")
        root = parse_xml(xml)
        obj_uris = root.findall("epp:command/epp:login/epp:svcs/epp:objURI", NS)
        assert len(obj_uris) == 3

    def test_login_has_cl_trid(self):
        xml = build_login("reg", "pwd")
        root = parse_xml(xml)
        cl_trid = root.find("epp:command/epp:clTRID", NS)
        assert cl_trid is not None
        assert cl_trid.text and len(cl_trid.text) > 0

    def test_login_cl_trid_unique(self):
        """Chaque commande doit avoir un clTRID différent."""
        xml1 = build_login("reg", "pwd")
        xml2 = build_login("reg", "pwd")
        root1 = parse_xml(xml1)
        root2 = parse_xml(xml2)
        t1 = root1.find("epp:command/epp:clTRID", NS).text
        t2 = root2.find("epp:command/epp:clTRID", NS).text
        assert t1 != t2


class TestBuildLogout:
    def test_logout_is_valid_xml(self):
        xml = build_logout()
        root = parse_xml(xml)
        assert root is not None

    def test_logout_contains_logout_element(self):
        xml = build_logout()
        root = parse_xml(xml)
        assert root.find("epp:command/epp:logout", NS) is not None

    def test_logout_has_cl_trid(self):
        xml = build_logout()
        root = parse_xml(xml)
        assert root.find("epp:command/epp:clTRID", NS) is not None


class TestBuildPollRequest:
    def test_poll_req_is_valid_xml(self):
        xml = build_poll_request()
        root = parse_xml(xml)
        assert root is not None

    def test_poll_req_op_attribute(self):
        xml = build_poll_request()
        root = parse_xml(xml)
        poll = root.find("epp:command/epp:poll", NS)
        assert poll is not None
        assert poll.get("op") == "req"

    def test_poll_req_has_cl_trid(self):
        xml = build_poll_request()
        root = parse_xml(xml)
        assert root.find("epp:command/epp:clTRID", NS) is not None


class TestBuildPollAck:
    def test_poll_ack_is_valid_xml(self):
        xml = build_poll_ack("12345")
        root = parse_xml(xml)
        assert root is not None

    def test_poll_ack_op_attribute(self):
        xml = build_poll_ack("12345")
        root = parse_xml(xml)
        poll = root.find("epp:command/epp:poll", NS)
        assert poll is not None
        assert poll.get("op") == "ack"

    def test_poll_ack_msg_id(self):
        xml = build_poll_ack("MSG-001")
        root = parse_xml(xml)
        poll = root.find("epp:command/epp:poll", NS)
        assert poll.get("msgID") == "MSG-001"

    def test_poll_ack_has_cl_trid(self):
        xml = build_poll_ack("1")
        root = parse_xml(xml)
        assert root.find("epp:command/epp:clTRID", NS) is not None
