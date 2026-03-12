"""
Client EPP TCP/TLS avec framing RFC 5734.

Implémente la connexion sécurisée TLS 1.2+ et le protocole de framing
EPP : chaque trame est précédée de 4 octets big-endian indiquant la
longueur totale (header 4 bytes inclus + payload).
"""

import socket
import ssl
import struct
from typing import Optional

from src.utils.logger import get_logger, mask_sensitive

logger = get_logger("epp_tester.client")

# Longueur du header EPP RFC 5734 (4 octets big-endian)
EPP_HEADER_SIZE = 4


class EppConnectionError(Exception):
    """Erreur de connexion au serveur EPP."""


class EppFramingError(Exception):
    """Erreur de framing RFC 5734."""


class EppClient:
    """Client EPP avec connexion TLS et framing RFC 5734.

    Protocole de framing (RFC 5734 § 4) :
    - Chaque message est précédé de 4 octets big-endian représentant
      la longueur totale du message : taille_header(4) + taille_payload.
    - Le récepteur lit 4 octets, calcule la taille du payload, puis
      lit exactement ce nombre d'octets.
    """

    def __init__(self) -> None:
        self._socket: Optional[ssl.SSLSocket] = None
        self._host: str = ""
        self._port: int = 700
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        """True si une connexion TLS active est établie."""
        return self._connected and self._socket is not None

    def connect(
        self,
        host: str,
        port: int = 700,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        cafile: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """Ouvre une connexion TCP/TLS vers le serveur EPP.

        Args:
            host: adresse du serveur EPP
            port: port TCP (défaut RFC 5734 : 700)
            certfile: chemin vers le certificat TLS client (optionnel)
            keyfile: chemin vers la clé privée TLS client (optionnel)
            cafile: chemin vers la CA pour vérifier le serveur (optionnel)
            timeout: délai d'attente en secondes (défaut: 30)

        Raises:
            EppConnectionError: si la connexion échoue
        """
        self._host = host
        self._port = port

        # Configuration TLS — minimum TLS 1.2 (RFC 5734 § 2)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2

        if cafile:
            ctx.load_verify_locations(cafile=cafile)
        else:
            # Désactive la vérification du certificat serveur si pas de CA
            # (utile en environnement de test/sandbox)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        if certfile and keyfile:
            # Authentification mutuelle TLS (mTLS)
            ctx.load_cert_chain(certfile=certfile, keyfile=keyfile)

        try:
            raw_sock = socket.create_connection((host, port), timeout=timeout)
            raw_sock.settimeout(timeout)
            self._socket = ctx.wrap_socket(raw_sock, server_hostname=host)
            self._connected = True
            logger.info("Connexion TLS établie vers %s:%d", host, port)
        except (socket.error, ssl.SSLError, OSError) as exc:
            self._connected = False
            raise EppConnectionError(
                f"Impossible de se connecter à {host}:{port} — {exc}"
            ) from exc

    def get_greeting(self) -> str:
        """Lit le greeting EPP envoyé par le serveur à la connexion.

        Le serveur envoie automatiquement un <greeting> après connexion.
        RFC 5730 § 2.4.

        Returns:
            Trame XML du greeting.

        Raises:
            EppConnectionError: si la connexion n'est pas active
        """
        self._check_connected()
        greeting = self._recv_frame()
        logger.debug("Greeting EPP reçu :\n%s", mask_sensitive(greeting))
        return greeting

    def send_command(self, xml: str) -> str:
        """Envoie une commande XML EPP et retourne la réponse.

        Args:
            xml: commande XML EPP à envoyer

        Returns:
            Réponse XML brute du serveur

        Raises:
            EppConnectionError: si la connexion n'est pas active
            EppFramingError: si une erreur de framing survient
        """
        self._check_connected()

        # Log de la commande envoyée (credentials masqués)
        logger.debug("EPP >>> envoi :\n%s", mask_sensitive(xml))

        self._send_frame(xml)
        response = self._recv_frame()

        logger.debug("EPP <<< réponse :\n%s", mask_sensitive(response))
        return response

    def read_response(self) -> str:
        """Lit une réponse EPP sans envoyer de commande.

        Utile pour lire des messages asynchrones ou le greeting initial.

        Returns:
            Trame XML brute du serveur
        """
        self._check_connected()
        return self._recv_frame()

    def disconnect(self) -> None:
        """Ferme proprement la connexion TLS/TCP."""
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                self._socket.close()
                self._socket = None
        self._connected = False
        logger.info("Déconnexion EPP de %s:%d", self._host, self._port)

    # ------------------------------------------------------------------
    # Méthodes privées de framing RFC 5734
    # ------------------------------------------------------------------

    def _send_frame(self, xml: str) -> None:
        """Envoie une trame EPP avec son header 4 octets.

        Format RFC 5734 :
        [4 octets big-endian : longueur totale = 4 + len(payload)] [payload UTF-8]
        """
        payload = xml.encode("utf-8")
        # La longueur totale inclut les 4 octets du header
        total_length = EPP_HEADER_SIZE + len(payload)
        header = struct.pack(">I", total_length)
        try:
            self._socket.sendall(header + payload)
        except (socket.error, ssl.SSLError, OSError) as exc:
            self._connected = False
            raise EppFramingError(f"Erreur d'envoi de trame : {exc}") from exc

    def _recv_frame(self) -> str:
        """Lit une trame EPP complète depuis le socket.

        Lit 4 octets de header pour obtenir la longueur totale,
        puis lit exactement (longueur - 4) octets de payload.

        Returns:
            Payload XML décodé en UTF-8
        """
        # Lecture du header
        header = self._recv_exact(EPP_HEADER_SIZE)
        if len(header) < EPP_HEADER_SIZE:
            raise EppFramingError("Header EPP incomplet reçu")

        total_length = struct.unpack(">I", header)[0]
        payload_length = total_length - EPP_HEADER_SIZE

        if payload_length <= 0:
            raise EppFramingError(
                f"Longueur de payload invalide : {payload_length} "
                f"(total={total_length})"
            )

        # Lecture du payload
        payload = self._recv_exact(payload_length)
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EppFramingError(f"Payload EPP non décodable en UTF-8 : {exc}") from exc

    def _recv_exact(self, n: int) -> bytes:
        """Lit exactement n octets depuis le socket.

        Args:
            n: nombre d'octets à lire

        Returns:
            Bytes lus (peut être inférieur à n en cas de fermeture connexion)
        """
        buf = b""
        while len(buf) < n:
            try:
                chunk = self._socket.recv(n - len(buf))
            except (socket.error, ssl.SSLError, OSError) as exc:
                self._connected = False
                raise EppFramingError(f"Erreur de réception : {exc}") from exc
            if not chunk:
                # Connexion fermée par le serveur
                self._connected = False
                raise EppFramingError(
                    f"Connexion fermée par le serveur après {len(buf)}/{n} octets"
                )
            buf += chunk
        return buf

    def _check_connected(self) -> None:
        """Vérifie que la connexion est active."""
        if not self.is_connected:
            raise EppConnectionError(
                "Pas de connexion EPP active — appelez connect() d'abord."
            )
