"""Shared pytest fixtures for the backend suite.

The suite is hermetic by default: an autouse fixture replaces the real
socket layer with one that fails fast whenever a test tries to reach an
external host or resolve an external hostname. Loopback traffic stays
allowed because CPython event loops use 127.0.0.1 self-pipes internally,
and loopback is not an external provider (SEC, Hugging Face, Groq,
Qdrant Cloud all live outside localhost). Tests that legitimately need
external access must declare ``@pytest.mark.integration`` (local
services/fixtures) or ``@pytest.mark.live_network`` (internet), both of
which are registered in ``pytest.ini``; ``live_network`` is additionally
deselected from default runs.
"""

from __future__ import annotations

import ipaddress
import socket

import pytest

_HERMETIC_MARKERS = frozenset({"integration", "live_network"})

_BLOCK_MESSAGE = (
    "Real network operation blocked ({operation} -> {address!r}). "
    "The default test suite must stay offline: mock the dependency, or "
    "mark the test with @pytest.mark.integration / @pytest.mark.live_network."
)


def _address_host(address) -> str | None:
    if isinstance(address, tuple | list):
        return str(address[0]) if address else None
    if isinstance(address, str):
        return address
    return None


def _is_loopback(address) -> bool:
    """Whether a connect/getaddrinfo target is loopback (always allowed)."""
    host = _address_host(address)
    if not host:
        return False
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return host.lower() == "localhost"


class _NoNetworkSocket(socket.socket):
    """A real socket type whose outbound operations fail immediately."""

    def connect(self, address):
        if _is_loopback(address):
            return super().connect(address)
        raise RuntimeError(
            _BLOCK_MESSAGE.format(operation="connect", address=address)
        )

    def connect_ex(self, address):
        if _is_loopback(address):
            return super().connect_ex(address)
        raise RuntimeError(
            _BLOCK_MESSAGE.format(operation="connect_ex", address=address)
        )

    def sendto(self, data, address):
        if _is_loopback(address):
            return super().sendto(data, address)
        raise RuntimeError(
            _BLOCK_MESSAGE.format(operation="sendto", address=address)
        )


@pytest.fixture(autouse=True)
def forbid_real_network(request):
    """Fail any unmocked outbound network call in the default suite."""
    markers = {marker.name for marker in request.node.iter_markers()}
    if markers & _HERMETIC_MARKERS:
        yield
        return

    saved_socket = socket.socket
    saved_create_connection = socket.create_connection
    saved_getaddrinfo = socket.getaddrinfo
    saved_gethostbyname = socket.gethostbyname

    def blocked_create_connection(address, *args, **kwargs):
        if _is_loopback(address):
            return saved_create_connection(address, *args, **kwargs)
        raise RuntimeError(
            _BLOCK_MESSAGE.format(operation="create_connection", address=address)
        )

    def blocked_getaddrinfo(host, *args, **kwargs):
        if _is_loopback(host):
            return saved_getaddrinfo(host, *args, **kwargs)
        raise RuntimeError(
            _BLOCK_MESSAGE.format(operation="getaddrinfo", address=host)
        )

    def blocked_gethostbyname(host):
        if _is_loopback(host):
            return saved_gethostbyname(host)
        raise RuntimeError(
            _BLOCK_MESSAGE.format(operation="gethostbyname", address=host)
        )

    socket.socket = _NoNetworkSocket
    socket.create_connection = blocked_create_connection
    socket.getaddrinfo = blocked_getaddrinfo
    socket.gethostbyname = blocked_gethostbyname
    try:
        yield
    finally:
        socket.socket = saved_socket
        socket.create_connection = saved_create_connection
        socket.getaddrinfo = saved_getaddrinfo
        socket.gethostbyname = saved_gethostbyname
