"""Meta-tests proving the hermetic network guard is active by default.

External targets are blocked; loopback stays allowed so CPython event
loops can create their internal self-pipe sockets.
"""

from __future__ import annotations

import socket

import pytest

# Documentation-only external addresses; the guard raises before any packet.
EXTERNAL_HOST = "www.sec.gov"
EXTERNAL_IP = "203.0.113.1"


def test_outbound_tcp_connection_is_blocked() -> None:
    with pytest.raises(RuntimeError, match="Real network operation blocked"):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.connect((EXTERNAL_IP, 443))


def test_external_dns_resolution_is_blocked() -> None:
    with pytest.raises(RuntimeError, match="getaddrinfo"):
        socket.getaddrinfo(EXTERNAL_HOST, 443)


def test_create_connection_helper_is_blocked() -> None:
    with pytest.raises(RuntimeError, match="create_connection"):
        socket.create_connection((EXTERNAL_HOST, 443))


def test_loopback_connections_stay_allowed() -> None:
    """Event-loop self-pipes rely on loopback; it must not be blocked."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(("127.0.0.1", port))
