"""Tests du validateur XSD et du module d'export CSV/JSON."""

import csv
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock

from src.epp.validator import EppValidator, ValidationResult
from src.utils.export import export_to_csv, export_to_json, _log_to_dict


# =============================================================================
# Tests EppValidator
# =============================================================================

# XML EPP valides et invalides pour les tests
VALID_EPP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <command>
    <logout/>
    <clTRID>EPP-001</clTRID>
  </command>
</epp>"""

INVALID_XML = "<not valid xml>>>"
EMPTY_XML = ""

VALID_DOMAIN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"
     xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
  <command>
    <check>
      <domain:check>
        <domain:name>example.mg</domain:name>
      </domain:check>
    </check>
    <clTRID>EPP-002</clTRID>
  </command>
</epp>"""


class TestEppValidatorSyntax:
    """Tests de la validation syntaxique XML (sans schéma)."""

    @pytest.fixture
    def validator(self):
        return EppValidator()

    def test_valid_xml_syntax(self, validator):
        result = validator.validate_xml_syntax(VALID_EPP_XML)
        assert result.is_valid

    def test_invalid_xml_syntax(self, validator):
        result = validator.validate_xml_syntax(INVALID_XML)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_empty_xml(self, validator):
        result = validator.validate_xml_syntax(EMPTY_XML)
        assert not result.is_valid

    def test_result_bool_true(self, validator):
        result = validator.validate_xml_syntax(VALID_EPP_XML)
        assert bool(result) is True

    def test_result_bool_false(self, validator):
        result = validator.validate_xml_syntax(INVALID_XML)
        assert bool(result) is False


class TestEppValidatorXsd:
    """Tests de la validation XSD (graceful degradation si schéma absent)."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Validateur avec répertoire de schémas vide (dégradation gracieuse)."""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        return EppValidator(schemas_dir=schemas_dir)

    def test_valid_xml_no_schema_returns_warning(self, validator):
        """Sans schéma XSD, la validation doit passer avec un warning."""
        result = validator.validate(VALID_EPP_XML)
        assert result.is_valid
        assert result.warning is not None

    def test_invalid_xml_syntax_fails(self, validator):
        result = validator.validate(INVALID_XML)
        assert not result.is_valid

    def test_empty_xml_fails(self, validator):
        result = validator.validate(EMPTY_XML)
        assert not result.is_valid

    def test_domain_xml_no_schema_warning(self, validator):
        result = validator.validate(VALID_DOMAIN_XML)
        assert result.is_valid

    def test_with_real_schema(self, tmp_path):
        """Test avec un schéma XSD simplifié."""
        # Crée un schéma XSD minimal pour tester
        schema_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:epp="urn:ietf:params:xml:ns:epp-1.0"
           targetNamespace="urn:ietf:params:xml:ns:epp-1.0"
           elementFormDefault="qualified">
  <xs:element name="epp">
    <xs:complexType>
      <xs:choice>
        <xs:element name="hello"/>
        <xs:element name="greeting"/>
        <xs:element name="command" type="epp:commandType"/>
        <xs:element name="response"/>
      </xs:choice>
    </xs:complexType>
  </xs:element>
  <xs:complexType name="commandType">
    <xs:sequence>
      <xs:choice>
        <xs:element name="login"/>
        <xs:element name="logout"/>
        <xs:element name="check"/>
        <xs:element name="info"/>
        <xs:element name="create"/>
        <xs:element name="update"/>
        <xs:element name="delete"/>
        <xs:element name="renew"/>
        <xs:element name="transfer"/>
        <xs:element name="poll"/>
      </xs:choice>
      <xs:element name="clTRID" type="xs:token" minOccurs="0"/>
    </xs:sequence>
  </xs:complexType>
</xs:schema>'''
        schema_path = tmp_path / "epp-1.0.xsd"
        schema_path.write_text(schema_content, encoding="utf-8")

        validator = EppValidator(schemas_dir=tmp_path)
        result = validator.validate(VALID_EPP_XML)
        # Avec un schéma présent, la validation doit passer (pas de warning)
        assert result.is_valid


class TestValidationResult:
    def test_summary_valid(self):
        r = ValidationResult(True, [])
        assert "OK" in r.summary()

    def test_summary_invalid(self):
        r = ValidationResult(False, ["erreur 1", "erreur 2"])
        assert "ECHEC" in r.summary()
        assert "erreur 1" in r.summary()

    def test_summary_with_warning(self):
        r = ValidationResult(True, [], warning="schéma absent")
        assert "schéma absent" in r.summary()


# =============================================================================
# Tests export CSV/JSON
# =============================================================================

def _make_log(
    log_id: int = 1,
    profile_id: int = 1,
    command_type: str = "login",
    return_code: int = 1000,
    duration_ms: int = 50,
    success: bool = True,
    operator: str = "admin",
    xml_request: str = "<epp><command><login><pw>secret</pw></login></command></epp>",
    xml_response: str = "<epp><response><result code='1000'/></response></epp>",
    timestamp: datetime = None,
) -> MagicMock:
    """Crée un mock de SessionLog pour les tests."""
    log = MagicMock()
    log.id = log_id
    log.profile_id = profile_id
    log.command_type = command_type
    log.return_code = return_code
    log.duration_ms = duration_ms
    log.success = success
    log.operator = operator
    log.xml_request = xml_request
    log.xml_response = xml_response
    log.timestamp = timestamp or datetime(2024, 1, 15, 10, 30, 0)
    return log


class TestLogToDict:
    def test_basic_fields(self):
        log = _make_log()
        d = _log_to_dict(log, "Test Profile")
        assert d["id"] == 1
        assert d["command_type"] == "login"
        assert d["return_code"] == 1000
        assert d["profile_name"] == "Test Profile"
        assert d["success"] is True

    def test_credentials_masked_by_default(self):
        log = _make_log(xml_request="<epp><login><pw>secret_pw</pw></login></epp>")
        d = _log_to_dict(log)
        assert "secret_pw" not in d["xml_request"]
        assert "••••••••" in d["xml_request"]

    def test_credentials_not_masked_when_disabled(self):
        log = _make_log(xml_request="<epp><login><pw>secret_pw</pw></login></epp>")
        d = _log_to_dict(log, mask_xml=False)
        assert "secret_pw" in d["xml_request"]

    def test_timestamp_iso_format(self):
        log = _make_log(timestamp=datetime(2024, 6, 15, 12, 0, 0))
        d = _log_to_dict(log)
        assert "2024-06-15" in d["timestamp"]


class TestExportCsv:
    def test_creates_csv_file(self, tmp_path):
        logs = [_make_log(1), _make_log(2)]
        output = tmp_path / "export.csv"
        count = export_to_csv(logs, output)
        assert output.exists()
        assert count == 2

    def test_csv_has_header(self, tmp_path):
        logs = [_make_log()]
        output = tmp_path / "test.csv"
        export_to_csv(logs, output)

        with open(output, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert "id" in header
        assert "command_type" in header
        assert "return_code" in header

    def test_csv_row_count(self, tmp_path):
        logs = [_make_log(i) for i in range(5)]
        output = tmp_path / "test.csv"
        export_to_csv(logs, output)

        with open(output, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        # 1 header + 5 data rows
        assert len(rows) == 6

    def test_csv_masks_credentials(self, tmp_path):
        log = _make_log(xml_request="<epp><pw>secret</pw></epp>")
        output = tmp_path / "test.csv"
        export_to_csv([log], output)

        content = output.read_text(encoding="utf-8")
        assert "secret" not in content

    def test_csv_with_profile_map(self, tmp_path):
        log = _make_log(profile_id=42)
        output = tmp_path / "test.csv"
        export_to_csv([log], output, profile_map={42: "My Profile"})

        with open(output, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["profile_name"] == "My Profile"

    def test_empty_logs(self, tmp_path):
        output = tmp_path / "empty.csv"
        count = export_to_csv([], output)
        assert count == 0
        assert output.exists()

    def test_creates_parent_dirs(self, tmp_path):
        output = tmp_path / "subdir" / "nested" / "export.csv"
        export_to_csv([], output)
        assert output.exists()


class TestExportJson:
    def test_creates_json_file(self, tmp_path):
        logs = [_make_log(1), _make_log(2)]
        output = tmp_path / "export.json"
        count = export_to_json(logs, output)
        assert output.exists()
        assert count == 2

    def test_json_structure(self, tmp_path):
        logs = [_make_log()]
        output = tmp_path / "test.json"
        export_to_json(logs, output)

        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "export_date" in data
        assert "total_records" in data
        assert "records" in data
        assert data["total_records"] == 1

    def test_json_record_fields(self, tmp_path):
        log = _make_log(command_type="domain:check", return_code=1000)
        output = tmp_path / "test.json"
        export_to_json([log], output)

        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)

        record = data["records"][0]
        assert record["command_type"] == "domain:check"
        assert record["return_code"] == 1000

    def test_json_masks_credentials(self, tmp_path):
        log = _make_log(xml_request="<epp><pw>topsecret</pw></epp>")
        output = tmp_path / "test.json"
        export_to_json([log], output)

        content = output.read_text(encoding="utf-8")
        assert "topsecret" not in content

    def test_json_empty_logs(self, tmp_path):
        output = tmp_path / "empty.json"
        count = export_to_json([], output)
        assert count == 0
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_records"] == 0
        assert data["records"] == []
