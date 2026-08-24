"""Reusable offline socket guard shared by pytest and offline tooling.

The default backend test suite installs this guard through
``tests/conftest.py``. Offline batch tools such as the deterministic
evaluation Phase 1 runner install it directly so an accidental provider
call fails fast instead of silently consuming quota. Loopback traffic
stays allowed because CPython event loops create 127.0.0.1 self-pipes
internally, and no external provider (SEC, Hugging Face, Groq, Qdrant
Cloud) is reachable through loopback.
"""

from __future__ import annotations

import ipaddress
import socket
from contextlib import contextmanager
from typing import Iterator

_BLOCK_MESSAGE = (
    "Real network operation blocked ({operation} -> {address!r}). "
    "This context must stay offline: mock the dependency or run without "
    "the offline guard."
)


def _address_host(address) -> str | None:
    if isinstance(address, tuple | list):
        return str(address[0]) if address else None
    if isinstance(address, str):
        return address
    return None


def _is_loopback(address) -> bool:
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


def install_offline_socket_guard() -> callable:
    """Patch the socket module; returned callable restores the originals."""
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

    def restore():
        socket.socket = saved_socket
        socket.create_connection = saved_create_connection
        socket.getaddrinfo = saved_getaddrinfo
        socket.gethostbyname = saved_gethostbyname

    return restore


@contextmanager
def offline_socket_guard() -> Iterator[None]:
    """Context manager form of :func:`install_offline_socket_guard`."""
    restore = install_offline_socket_guard()
    try:
        yield
    finally:
        restore()
