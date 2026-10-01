"""Fail-closed capability checks for the local private workspace boundary.

Public/provider-free routes remain available in every deployment mode. Private
workspace reads and writes require explicit local mode, a loopback socket peer,
an exact local Host and (when present) Origin, plus a dedicated bearer token.
Forwarding headers are deliberately irrelevant to this boundary.
"""

from __future__ import annotations
from src.workspace.attribution import timed

import ipaddress
import secrets
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status

from configs.settings import settings


class AccessCapability(str, Enum):
    PUBLIC_PROVIDER_FREE = "public_provider_free"
    LOCAL_WORKSPACE = "local_workspace"
    EXECUTION_JOBS = "execution_jobs"


@dataclass(frozen=True)
class AccessGrant:
    capabilities: frozenset[AccessCapability]


_PUBLIC_GRANT = AccessGrant(frozenset({AccessCapability.PUBLIC_PROVIDER_FREE}))
_WORKSPACE_UNAVAILABLE = "Local workspace capability is unavailable"
_LOCAL_ONLY = "Local workspace access is restricted to loopback clients"
_HOST_DENIED = "Local workspace request host is not allowed"
_ORIGIN_DENIED = "Local workspace request origin is not allowed"
_AUTH_REQUIRED = "Local workspace authentication required"
_EXECUTION_DISABLED = "Workspace execution capability is disabled"


def require_public_provider_free_access() -> AccessGrant:
    """Mark a route as public and provider-free without changing its behavior."""
    return _PUBLIC_GRANT


def _loopback_peer(request: Request) -> bool:
    """Use only the socket peer; never trust Forwarded or X-Forwarded-For."""
    peer = request.client.host if request.client else ""
    try:
        return ipaddress.ip_address(peer).is_loopback
    except ValueError:
        return False


def _host_authority(value: str) -> tuple[str, int | None] | None:
    """Parse a Host-style value, preserving an explicitly configured port."""
    try:
        parsed = urlsplit(f"//{value}")
        port = parsed.port
    except ValueError:
        return None
    if (
        not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return (parsed.hostname.casefold(), port) if parsed.hostname else None


def _host_is_allowed(value: str) -> bool:
    requested = _host_authority(value)
    if requested is None:
        return False
    requested_name, requested_port = requested
    for entry in settings.local_workspace_allowed_hosts_list:
        allowed = _host_authority(entry)
        if allowed is None:
            continue
        allowed_name, allowed_port = allowed
        if allowed_name == requested_name and (
            allowed_port is None or allowed_port == requested_port
        ):
            return True
    return False


def _valid_bearer_token(request: Request) -> bool:
    configured = settings.local_workspace_token.get_secret_value()
    if not configured:
        return False

    authorization = request.headers.get("authorization", "")
    parts = authorization.split(" ")
    well_formed = (
        len(parts) == 2
        and parts[0].casefold() == "bearer"
        and bool(parts[1])
        and not any(char.isspace() for char in parts[1])
    )
    candidate = parts[1] if well_formed else ""
    matches = secrets.compare_digest(candidate.encode("utf-8"), configured.encode("utf-8"))
    return well_formed and matches


@timed("api.access")
def require_local_workspace_access(request: Request) -> AccessGrant:
    """Authorize one private workspace read or write request."""
    if settings.workspace_mode != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_WORKSPACE_UNAVAILABLE)
    if not _loopback_peer(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_LOCAL_ONLY)

    if not _host_is_allowed(request.headers.get("host", "")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_HOST_DENIED)

    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.local_workspace_allowed_origins_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_ORIGIN_DENIED)

    if not _valid_bearer_token(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_AUTH_REQUIRED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.performance_workspace_authorized = True
    return AccessGrant(
        frozenset(
            {
                AccessCapability.PUBLIC_PROVIDER_FREE,
                AccessCapability.LOCAL_WORKSPACE,
            }
        )
    )


def require_execution_access(request: Request) -> AccessGrant:
    """Authorize a bounded local job only when execution is explicitly enabled."""
    workspace_grant = require_local_workspace_access(request)
    if not settings.enable_workspace_execution:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_EXECUTION_DISABLED)
    return AccessGrant(
        workspace_grant.capabilities | frozenset({AccessCapability.EXECUTION_JOBS})
    )


def configuration_status() -> dict[str, object]:
    """Return an allowlisted status object that cannot contain credential values."""
    local_enabled = settings.workspace_mode == "local"
    return {
        "deployment_mode": settings.workspace_mode,
        "capabilities": {
            AccessCapability.PUBLIC_PROVIDER_FREE.value: True,
            AccessCapability.LOCAL_WORKSPACE.value: local_enabled,
            AccessCapability.EXECUTION_JOBS.value: (
                local_enabled and settings.enable_workspace_execution
            ),
        },
    }
