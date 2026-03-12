"""Tests du client EPP avec mock socket (unittest.mock)."""

import struct
import pytest
from unittest.mock import MagicMock, patch, call

from src.epp.client import EppClient, EppConnectionError, EppFramingError


def make_frame(xml: str) -> bytes:
    """Construit une trame EPP RFC 5734 à partir d'un XML."""
    payload = xml.encode("utf-8")
    header = struct.pack(">I", 4 + len(payload))
    return header + payload


# XML de test
GREETING_XML = '<?xml version="1.0"?><epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><greeting><svID>test-server</svID></greeting></epp>'
LOGIN_OK_XML = '<?xml version="1.0"?><epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="1000"><msg>Command completed successfully</msg></result><trID><clTRID>EPP-001</clTRID><svTRID>SRV-001</svTRID></trID></response></epp>'


@pytest.fixture
def mock_ssl_socket():
    """Retourne un mock de ssl.SSLSocket."""
    sock = MagicMock()
    return sock


@pytest.fixture
def connected_client(mock_ssl_socket):
    """Retourne un EppClient avec une connexion mockée."""
    client = EppClient()
    client._socket = mock_ssl_socket
    client._connected = True
    client._host = "epp.test.example.com"
    client._port = 700
    return client


class TestEppClientConnect:
    def test_connect_success(self):
        """Vérifie que connect() établit la connexion TLS."""
        client = EppClient()
        mock_sock = MagicMock()

        with patch("socket.create_connection", return_value=mock_sock) as mock_conn, \
             patch("ssl.SSLContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx
            mock_ctx.wrap_socket.return_value = mock_sock

            client.connect("epp.test.example.com", 700)

            mock_conn.assert_called_once_with(("epp.test.example.com", 700), timeout=30)
            assert client.is_connected

    def test_connect_failure_raises_error(self):
        """Vérifie que connect() lève EppConnectionError en cas d'échec."""
        client = EppClient()
        import socket
        with patch("socket.create_connection", side_effect=socket.error("Connection refused")):
            with pytest.raises(EppConnectionError, match="Impossible de se connecter"):
                client.connect("unreachable.host", 700)

    def test_is_connected_false_initially(self):
        client = EppClient()
        assert not client.is_connected


class TestEppClientFraming:
    def test_send_command_builds_correct_frame(self, connected_client, mock_ssl_socket):
        """Vérifie que send_command() envoie le bon framing RFC 5734."""
        xml = "<epp><hello/></epp>"
        payload = xml.encode("utf-8")
        expected_header = struct.pack(">I", 4 + len(payload))
        expected_frame = expected_header + payload

        # Mock de la réponse
        response_xml = LOGIN_OK_XML
        response_frame = make_frame(response_xml)

        # Simule recv : retourne 4 octets header puis le payload
        header_bytes = response_frame[:4]
        payload_bytes = response_frame[4:]

        mock_ssl_socket.recv.side_effect = [header_bytes, payload_bytes]

        result = connected_client.send_command(xml)

        mock_ssl_socket.sendall.assert_called_once_with(expected_frame)
        assert result == response_xml

    def test_recv_frame_reads_exact_bytes(self, connected_client, mock_ssl_socket):
        """Vérifie que read_response() lit exactement les octets annoncés."""
        xml = GREETING_XML
        frame = make_frame(xml)
        header = frame[:4]
        payload = frame[4:]

        mock_ssl_socket.recv.side_effect = [header, payload]

        result = connected_client.read_response()
        assert result == xml

    def test_recv_frame_handles_chunked_data(self, connected_client, mock_ssl_socket):
        """Vérifie la lecture correcte quand les données arrivent en plusieurs chunks."""
        xml = GREETING_XML
        frame = make_frame(xml)
        header = frame[:4]
        payload = frame[4:]

        # Simule des chunks : header en 2 fois, payload en 3 fois
        mid = len(payload) // 2
        mock_ssl_socket.recv.side_effect = [
            header[:2], header[2:],         # header en 2 morceaux
            payload[:mid],                   # payload chunk 1
            payload[mid:mid+5],              # payload chunk 2
            payload[mid+5:],                 # payload chunk 3
        ]

        result = connected_client.read_response()
        assert result == xml

    def test_recv_frame_connection_closed_raises_error(self, connected_client, mock_ssl_socket):
        """Vérifie qu'une connexion fermée lève EppFramingError."""
        mock_ssl_socket.recv.return_value = b""  # connexion fermée
        with pytest.raises(EppFramingError, match="Connexion fermée"):
            connected_client.read_response()

    def test_send_command_not_connected_raises_error(self):
        """Vérifie que send_command sans connexion lève EppConnectionError."""
        client = EppClient()
        with pytest.raises(EppConnectionError, match="Pas de connexion EPP active"):
            client.send_command("<epp><hello/></epp>")


class TestEppClientDisconnect:
    def test_disconnect_closes_socket(self, connected_client, mock_ssl_socket):
        connected_client.disconnect()
        mock_ssl_socket.close.assert_called_once()
        assert not connected_client.is_connected

    def test_disconnect_idempotent(self):
        """Disconnect sur un client non connecté ne doit pas lever d'exception."""
        client = EppClient()
        client.disconnect()  # Ne doit pas lever d'exception

    def test_get_greeting(self, connected_client, mock_ssl_socket):
        """Vérifie que get_greeting() lit la première trame du serveur."""
        frame = make_frame(GREETING_XML)
        mock_ssl_socket.recv.side_effect = [frame[:4], frame[4:]]

        result = connected_client.get_greeting()
        assert result == GREETING_XML
