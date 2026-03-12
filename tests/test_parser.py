"""Tests du parseur de réponses EPP."""

import pytest
from src.epp.parser import parse, EppResponse

# Réponses EPP de test
XML_LOGIN_OK = """<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <response>
    <result code="1000">
      <msg>Command completed successfully</msg>
    </result>
    <trID>
      <clTRID>EPP-ABC123</clTRID>
      <svTRID>SRV-20240101-001</svTRID>
    </trID>
  </response>
</epp>"""

XML_POLL_NO_MESSAGES = """<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <response>
    <result code="1301">
      <msg>Command completed successfully; ack to dequeue</msg>
    </result>
    <msgQ count="5" id="12345">
      <msg>Transfer requested.</msg>
    </msgQ>
    <trID>
      <svTRID>SRV-20240101-002</svTRID>
    </trID>
  </response>
</epp>"""

XML_AUTH_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <response>
    <result code="2200">
      <msg>Authentication error</msg>
    </result>
    <trID>
      <svTRID>SRV-20240101-003</svTRID>
    </trID>
  </response>
</epp>"""

XML_OBJECT_NOT_FOUND = """<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <response>
    <result code="2303">
      <msg>Object does not exist</msg>
    </result>
    <trID>
      <svTRID>SRV-20240101-004</svTRID>
    </trID>
  </response>
</epp>"""

XML_GREETING = """<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <greeting>
    <svID>Example EPP server epp.example.com</svID>
    <svDate>2024-01-01T00:00:00.0Z</svDate>
  </greeting>
</epp>"""


class TestParseLoginOk:
    def test_parse_returns_epp_response(self):
        resp = parse(XML_LOGIN_OK)
        assert isinstance(resp, EppResponse)

    def test_parse_code_1000(self):
        resp = parse(XML_LOGIN_OK)
        assert resp.code == 1000

    def test_parse_message(self):
        resp = parse(XML_LOGIN_OK)
        assert "completed successfully" in resp.message

    def test_is_success_true(self):
        resp = parse(XML_LOGIN_OK)
        assert resp.is_success()

    def test_is_error_false(self):
        resp = parse(XML_LOGIN_OK)
        assert not resp.is_error()

    def test_raw_xml_preserved(self):
        resp = parse(XML_LOGIN_OK)
        assert "1000" in resp.raw_xml

    def test_sv_trid_extracted(self):
        resp = parse(XML_LOGIN_OK)
        assert resp.data.get("svTRID") == "SRV-20240101-001"

    def test_cl_trid_extracted(self):
        resp = parse(XML_LOGIN_OK)
        assert resp.data.get("clTRID") == "EPP-ABC123"


class TestParsePollMessages:
    def test_code_1301(self):
        resp = parse(XML_POLL_NO_MESSAGES)
        assert resp.code == 1301

    def test_is_success(self):
        resp = parse(XML_POLL_NO_MESSAGES)
        assert resp.is_success()

    def test_msg_q_extracted(self):
        resp = parse(XML_POLL_NO_MESSAGES)
        assert "msgQ" in resp.data
        assert resp.data["msgQ"]["count"] == "5"
        assert resp.data["msgQ"]["id"] == "12345"
        assert resp.data["msgQ"]["msg"] == "Transfer requested."


class TestParseAuthError:
    def test_code_2200(self):
        resp = parse(XML_AUTH_ERROR)
        assert resp.code == 2200

    def test_is_error_true(self):
        resp = parse(XML_AUTH_ERROR)
        assert resp.is_error()

    def test_is_success_false(self):
        resp = parse(XML_AUTH_ERROR)
        assert not resp.is_success()

    def test_message_auth_error(self):
        resp = parse(XML_AUTH_ERROR)
        assert "Authentication" in resp.message or "authentication" in resp.message.lower()


class TestParseObjectNotFound:
    def test_code_2303(self):
        resp = parse(XML_OBJECT_NOT_FOUND)
        assert resp.code == 2303

    def test_is_error(self):
        resp = parse(XML_OBJECT_NOT_FOUND)
        assert resp.is_error()

    def test_message_object_not_found(self):
        resp = parse(XML_OBJECT_NOT_FOUND)
        assert "exist" in resp.message.lower() or "not found" in resp.message.lower()


class TestParseGreeting:
    def test_greeting_returns_code_1000(self):
        resp = parse(XML_GREETING)
        assert resp.code == 1000

    def test_greeting_type_in_data(self):
        resp = parse(XML_GREETING)
        assert resp.data.get("type") == "greeting"

    def test_greeting_is_success(self):
        resp = parse(XML_GREETING)
        assert resp.is_success()


class TestParseErrors:
    def test_empty_xml_raises(self):
        with pytest.raises(ValueError, match="vide"):
            parse("")

    def test_invalid_xml_raises(self):
        with pytest.raises(ValueError, match="invalide"):
            parse("<not valid xml>>>")

    def test_no_response_element_raises(self):
        xml = '<?xml version="1.0"?><epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><unknown/></epp>'
        with pytest.raises(ValueError):
            parse(xml)


class TestEppResponseStr:
    def test_str_success(self):
        resp = EppResponse(code=1000, message="OK", raw_xml="<epp/>")
        assert "OK" in str(resp)
        assert "1000" in str(resp)

    def test_str_error(self):
        resp = EppResponse(code=2303, message="Not found", raw_xml="<epp/>")
        assert "ERR" in str(resp)
        assert "2303" in str(resp)
