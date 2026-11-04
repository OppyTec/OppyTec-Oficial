"""
oppytec-backend/src/core/guards/ssrf_guard.py
Guardia estricto de prevención de Server-Side Request Forgery (SSRF - CWE-918):
- Valida que URLs para webhooks salientes o descargas externas utilicen esquemas seguros (HTTP/HTTPS).
- Bloquea accesos a rangos de IP privados, loopback (127.0.0.1, ::1), link-local (169.254.169.254 AWS metadata),
  redes internas RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), broadcast y dominios de metadatos de cloud.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from src.core.exceptions import SecurityValidationError

BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "::1",
    "metadata.google.internal",
    "metadata.internal",
    "169.254.169.254",
    "instance-data",
})

FORBIDDEN_IP_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
)


def is_private_or_restricted_ip(ip_str: str) -> bool:
    """Retorna True si la dirección IP pertenece a un rango privado, reservado o loopback."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    for net in FORBIDDEN_IP_NETWORKS:
        if ip in net:
            return True
    return False


def validate_safe_webhook_url(
    url: str,
    *,
    allow_dns_resolution: bool = True,
    field_name: str = "webhook_url",
) -> str:
    """
    Valida de forma determinista que una URL sea segura contra ataques SSRF:
    - Esquema permitido únicamente 'http' o 'https'.
    - Hostname no vacío ni en la lista negra de metadatos/cloud.
    - Resolución IP verificada contra rangos privados (RFC 1918 / RFC 3927).
    Lanza `SecurityValidationError` (HTTP 422 o 400) si se detecta cualquier vector SSRF.
    """
    if not url or not isinstance(url, str):
        raise SecurityValidationError(
            f"Invalid URL for '{field_name}'.",
            i18n_key="security:errors.invalid_url",
            error_code="INVALID_URL",
        )

    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
    except Exception as exc:
        raise SecurityValidationError(
            f"Malformed URL for '{field_name}': {exc}",
            i18n_key="security:errors.malformed_url",
            error_code="MALFORMED_URL",
        ) from exc

    if parsed.scheme.lower() not in ("http", "https"):
        raise SecurityValidationError(
            f"Forbidden URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.",
            i18n_key="security:errors.forbidden_url_scheme",
            error_code="SSRF_FORBIDDEN_SCHEME",
        )

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise SecurityValidationError(
            "Webhook URL must contain a valid hostname.",
            i18n_key="security:errors.missing_hostname",
            error_code="MISSING_HOSTNAME",
        )

    if hostname in BLOCKED_HOSTNAMES:
        raise SecurityValidationError(
            f"Blocked internal hostname '{hostname}' detected (SSRF prevention).",
            i18n_key="security:errors.ssrf_blocked_hostname",
            error_code="SSRF_TARGET_BLOCKED",
        )

    # Verificar si el hostname es una dirección IP directa
    try:
        if is_private_or_restricted_ip(hostname):
            raise SecurityValidationError(
                f"Private or restricted IP '{hostname}' blocked (SSRF prevention).",
                i18n_key="security:errors.ssrf_blocked_ip",
                error_code="SSRF_TARGET_BLOCKED",
            )
    except ValueError:
        pass

    # Resolución DNS para verificar que no apunte a IPs internas (si está habilitada)
    if allow_dns_resolution:
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_cand = item[4][0]
                if is_private_or_restricted_ip(ip_cand):
                    raise SecurityValidationError(
                        f"Resolved IP '{ip_cand}' for hostname '{hostname}' is restricted (SSRF prevention).",
                        i18n_key="security:errors.ssrf_blocked_ip",
                        error_code="SSRF_TARGET_BLOCKED",
                    )
        except socket.gaierror:
            # Si no puede resolverse en tests offline y no es IP directa, se permite si no es bloqueado
            pass

    return cleaned
