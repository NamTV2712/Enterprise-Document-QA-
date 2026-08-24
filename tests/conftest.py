"""Shared pytest fixtures for the backend suite.

The suite is hermetic by default: an autouse fixture installs the shared
offline socket guard (see ``configs/offline_guard.py``) so any unmocked
external network call fails fast. Tests that legitimately need external
access must declare ``@pytest.mark.integration`` (local services or
fixtures) or ``@pytest.mark.live_network`` (internet), both registered in
``pytest.ini``; ``live_network`` is additionally deselected from default
runs.
"""

from __future__ import annotations

import pytest

from configs.offline_guard import install_offline_socket_guard

_HERMETIC_MARKERS = frozenset({"integration", "live_network"})


@pytest.fixture(autouse=True)
def forbid_real_network(request):
    """Fail any unmocked outbound network call in the default suite."""
    markers = {marker.name for marker in request.node.iter_markers()}
    if markers & _HERMETIC_MARKERS:
        yield
        return

    restore = install_offline_socket_guard()
    try:
        yield
    finally:
        restore()
