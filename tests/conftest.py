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

from pathlib import Path

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


def skip_without_data(*paths: str):
    """Skip tests that replay git-ignored data artifacts when absent.

    A repository checkout (including CI) has no ``data/`` directory; tests
    that read frozen evaluation artifacts or diagnostics receipts can only
    run on a machine where an authorized local corpus exists.
    """
    missing = [path for path in paths if not Path(path).exists()]
    return pytest.mark.skipif(
        bool(missing),
        reason="requires git-ignored data artifacts: " + ", ".join(paths),
    )
