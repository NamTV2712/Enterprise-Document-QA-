"""Rate-limit identity resolution behind optional trusted reverse proxies.

By default the API keys rate limits on the socket peer address. When the
deployment sits behind a known reverse proxy (ngrok tunnel, local Docker
gateway, and so on), every external client shares that proxy's address
and therefore one shared rate-limit bucket.

Operators can declare proxy networks through ``TRUSTED_PROXY_CIDRS``.
Only then is ``X-Forwarded-For`` consulted, and only to walk trusted
hops right-to-left until the first non-trusted client address. Requests
from any other peer, malformed headers, and unconfigured deployments all
fall back to the socket peer so a direct client can never choose its
rate-limit bucket by forging headers.
"""

from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache
from typing import Any

from configs.settings import settings

logger = logging.getLogger(__name__)

TrustedNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def _clean_token(value: str | None) -> str:
    """Trim whitespace and optional IPv6 brackets from a header token."""
    if value is None:
        return ""
    token = value.strip()
    if len(token) >= 2 and token.startswith("[") and token.endswith("]"):
        token = token[1:-1].strip()
    return token


def _parse_ip(token: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(token)
    except ValueError:
        return None


@lru_cache(maxsize=8)
def _parse_trusted_cidrs(cidrs_text: str) -> tuple[TrustedNetwork, ...]:
    """Parse the configured CIDR allowlist once per distinct value.

    Invalid entries are logged and skipped instead of widening trust;
    a typo degrades toward legacy peer-based keying rather than granting
    header trust to an unintended network.
    """
    networks: list[TrustedNetwork] = []
    for raw_token in cidrs_text.split(","):
        token = _clean_token(raw_token)
        if not token:
            continue
        try:
            networks.append(ipaddress.ip_network(token, strict=False))
        except ValueError:
            logger.warning(
                "Ignoring invalid TRUSTED_PROXY_CIDRS entry %r; it grants no trust",
                token,
            )
    return tuple(networks)


def _is_trusted(address: str, networks: tuple[TrustedNetwork, ...]) -> bool:
    parsed = _parse_ip(address)
    if parsed is None:
        return False
    return any(parsed in network for network in networks)


def resolve_client_ip(
    peer: str | None,
    forwarded_for: str | None,
    cidrs_text: str,
) -> str:
    """Return the rate-limit identity for one request.

    ``peer`` is the socket-level client address (``request.client.host``)
    and ``forwarded_for`` is the raw ``X-Forwarded-For`` header value.
    The proxy chain is walked from right (closest hop) to left; the first
    address outside the trusted set is returned as the originating client.
    """
    peer_ip = _clean_token(peer)
    if not peer_ip or _parse_ip(peer_ip) is None:
        return "unknown"

    networks = _parse_trusted_cidrs(cidrs_text)
    if not networks or not _is_trusted(peer_ip, networks):
        return peer_ip

    if not forwarded_for:
        return peer_ip

    entries = [_clean_token(part) for part in forwarded_for.split(",")]
    if not entries or any(not entry or _parse_ip(entry) is None for entry in entries):
        # A single malformed token poisons the whole chain: fall back to
        # the peer rather than trusting whichever prefix still parses.
        return peer_ip

    for entry in reversed(entries):
        if not _is_trusted(entry, networks):
            return entry
    # Every listed hop is trusted infrastructure with no untrusted origin.
    return peer_ip


def get_rate_limit_key(request: Any) -> str:
    """slowapi key_func resolving the bucket identity per request."""
    peer = request.client.host if request.client else None
    forwarded_for = request.headers.get("x-forwarded-for")
    return resolve_client_ip(peer, forwarded_for, settings.trusted_proxy_cidrs)
