"""Real lifespan and workspace recovery, with model/provider boundaries offline."""

from contextlib import ExitStack
import os

import pytest
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

from tests.integration.final_product_server import install_runtime_dependencies
from tests.test_workspace_jobs import _running
from src.workspace.database import WorkspaceDatabase
from src.workspace.jobs import SQLiteJobRepository


@pytest.mark.parametrize("mode", ["public", "local"])
def test_committed_app_lifespan_builds_indexes_and_closes_store(tmp_path, monkeypatch, mode):
    with ExitStack() as stack:
        environment = dict(os.environ)
        application, closed = install_runtime_dependencies(stack, tmp_path)
        assert dict(os.environ) == environment
        routes = [(method, route.path) for route in application.app.routes
                  if isinstance(route, APIRoute) for method in route.methods]
        assert len(routes) == len(set(routes)) == 90
        monkeypatch.setattr(application.settings, "workspace_mode", mode)
        monkeypatch.setattr(application.settings, "workspace_db_path", tmp_path / "workspace.sqlite3")
        with TestClient(application.app) as client:
            assert client.get("/health/ready").status_code == 200
            stats = client.get("/documents/stats")
            assert stats.status_code == 200
            assert stats.json()["documents"] == 2
            assert stats.json()["chunks"] == 4
            assert application._state["document_chunks_by_id"]
            assert application._state["chunk_records_by_id"]
            assert (tmp_path / "workspace.sqlite3").exists() is (mode == "local")
            assert closed == []
        assert closed == [True]


def test_real_local_lifespan_recovers_durable_active_jobs(tmp_path, monkeypatch):
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    database.initialize()
    repository = SQLiteJobRepository(database)
    active = _running(repository)
    with ExitStack() as stack:
        application, _closed = install_runtime_dependencies(stack, tmp_path)
        monkeypatch.setattr(application.settings, "workspace_mode", "local")
        monkeypatch.setattr(application.settings, "workspace_db_path", database.path)
        with TestClient(application.app):
            assert SQLiteJobRepository(WorkspaceDatabase(database.path)).get_job(active.job_id).state == "interrupted"


def test_local_lifespan_drains_more_than_one_recovery_page_of_agent_runs(tmp_path, monkeypatch):
    database = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    database.initialize()
    repository = SQLiteJobRepository(database)
    ids = []
    for index in range(101):
        job = repository.create_job(
            namespace="agent", job_type="bounded_agent_run",
            idempotency_key=f"recovery-{index}", configuration_fingerprint="a" * 64,
            payload={}, steps=("execute_agent",),
        )
        repository.transition_job(job.job_id, expected_revision=job.revision, target_state="running")
        ids.append(job.job_id)
    with ExitStack() as stack:
        application, _closed = install_runtime_dependencies(stack, tmp_path)
        monkeypatch.setattr(application.settings, "workspace_mode", "local")
        monkeypatch.setattr(application.settings, "workspace_db_path", database.path)
        with TestClient(application.app):
            pass
    reopened = SQLiteJobRepository(WorkspaceDatabase(database.path))
    assert all(reopened.get_job(job_id).state == "interrupted" for job_id in ids)


def test_empty_corpus_startup_fails_closed_without_opening_public_db(tmp_path, monkeypatch):
    with ExitStack() as stack:
        application, closed = install_runtime_dependencies(stack, tmp_path)
        monkeypatch.setattr(application.settings, "workspace_mode", "public")
        monkeypatch.setattr(application.settings, "workspace_db_path", tmp_path / "never.sqlite3")
        monkeypatch.setattr(application, "load_retrieval_chunks", lambda *_args: [])
        with pytest.raises(RuntimeError, match="No searchable chunks"):
            with TestClient(application.app):
                pytest.fail("empty startup admitted")
        assert closed == [True]
        assert not (tmp_path / "never.sqlite3").exists()
