"""DB-SCALE-001 deterministic initialization, WAL snapshots and writer races."""
from concurrent.futures import ThreadPoolExecutor
import gc
import sqlite3
import threading
import weakref

import pytest

from configs.settings import Settings
from src.workspace.database import WorkspaceDatabase, WorkspaceDatabaseStateError
from src.workspace.jobs import JobConflictError, JobTransitionError, SQLiteJobRepository
from src.workspace.migrations import MIGRATIONS
from src.workspace.attribution import capture
from tests.test_workspace_jobs import _create, _running
from tests.test_workspace_worker import queued


def configured(path):
    return Settings(_env_file=None, workspace_mode="local",
        local_workspace_token="db-scale-local-token-0123456789-abcdef",
        workspace_db_path=path, workspace_runs_dir=path.parent / "runs")


def repository(path):
    db = WorkspaceDatabase(path)
    db.ensure_initialized()
    return SQLiteJobRepository(db, forbidden_secret_values=())


@pytest.mark.parametrize("upgrade", [False, True])
def test_eight_initializers_validate_once_and_publish_only_complete_schema(tmp_path, monkeypatch, upgrade):
    path = tmp_path / "workspace.sqlite3"
    if upgrade:
        WorkspaceDatabase(path, migrations=MIGRATIONS[:6]).initialize()
    stores = [WorkspaceDatabase(path) for _ in range(8)]
    start = threading.Barrier(8)
    entered, release = threading.Event(), threading.Event()
    calls = []
    original = WorkspaceDatabase._initialize_locked
    def gated(db):
        calls.append(True)
        entered.set()
        assert release.wait(5)
        return original(db)
    monkeypatch.setattr(WorkspaceDatabase, "_initialize_locked", gated)
    def ensure(db):
        start.wait(5)
        version = db.ensure_initialized()
        with db.connection() as c:
            versions = [r[0] for r in c.execute("SELECT version FROM schema_migrations ORDER BY version")]
        assert versions == list(range(1, 8))
        return version
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(ensure, db) for db in stores]
        try:
            assert entered.wait(5)
            assert all(not f.done() for f in futures)
        finally:
            release.set()
        assert [f.result(10) for f in futures] == [7] * 8
    assert len(calls) == 1
    with stores[0].connection() as c:
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_unrelated_databases_initialize_concurrently(tmp_path, monkeypatch):
    stores = [WorkspaceDatabase(tmp_path / f"store-{i}.sqlite3") for i in range(2)]
    overlap = threading.Barrier(2)
    original = WorkspaceDatabase._initialize_locked
    def gated(db):
        overlap.wait(5)
        return original(db)
    monkeypatch.setattr(WorkspaceDatabase, "_initialize_locked", gated)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(db.ensure_initialized) for db in stores]
        assert [f.result(10) for f in futures] == [7, 7]
    assert stores[0]._initialization is not stores[1]._initialization


def test_hot_factories_skip_integrity_and_writer_lock_but_explicit_audit_does_not(tmp_path, monkeypatch):
    settings = configured(tmp_path / "workspace.sqlite3")
    owner = SQLiteJobRepository.from_settings(settings, forbidden_secret_values=())
    job = _create(owner)
    def unexpected(_db):
        pytest.fail("hot factory performed a full integrity initialization")
    monkeypatch.setattr(WorkspaceDatabase, "_initialize_locked", unexpected)
    with owner.database._write_lock:
        with ThreadPoolExecutor(max_workers=1) as pool:
            def hot_reads():
                for _ in range(30):
                    other = SQLiteJobRepository.from_settings(settings, forbidden_secret_values=())
                    assert other.get_job(job.job_id) == job
                return True
            assert pool.submit(hot_reads).result(5)
    with pytest.raises(pytest.fail.Exception):
        owner.database.initialize()


def test_full_audit_still_rejects_future_schema_and_invalidates_warm_receipt(tmp_path):
    db = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    db.ensure_initialized()
    with db.transaction(write=True) as c:
        c.execute("INSERT INTO schema_migrations VALUES (8, 'future', 'future', 'now')")
    with pytest.raises(WorkspaceDatabaseStateError, match="newer"):
        db.initialize()
    with pytest.raises(WorkspaceDatabaseStateError, match="newer"):
        WorkspaceDatabase(db.path).ensure_initialized()


def test_migration_contract_is_part_of_initialized_identity(tmp_path):
    path = tmp_path / "workspace.sqlite3"
    old = WorkspaceDatabase(path, migrations=MIGRATIONS[:6])
    assert old.ensure_initialized() == 6
    current = WorkspaceDatabase(path)
    assert current.ensure_initialized() == 7
    with pytest.raises(WorkspaceDatabaseStateError, match="newer"):
        old.ensure_initialized()
    assert current.ensure_initialized() == 7


def test_deleted_store_reinitializes_instead_of_reusing_old_receipt(tmp_path):
    db = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    db.ensure_initialized()
    db.path.unlink()
    assert db.ensure_initialized() == 7
    with db.connection() as c:
        assert c.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 7


def test_replaced_file_must_pass_full_validation(tmp_path):
    db = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    db.ensure_initialized()
    replacement = tmp_path / "replacement.sqlite3"
    replacement.write_bytes(b"not a sqlite database")
    replacement.replace(db.path)
    with pytest.raises(WorkspaceDatabaseStateError):
        db.ensure_initialized()


def test_failed_initialization_can_retry_without_publishing_partial_receipt(tmp_path, monkeypatch):
    db = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    original = db._initialize_locked
    def failed():
        raise WorkspaceDatabaseStateError("synthetic initialization failure")
    monkeypatch.setattr(db, "_initialize_locked", failed)
    with pytest.raises(WorkspaceDatabaseStateError):
        db.ensure_initialized()
    assert db._initialization.ready is None
    monkeypatch.setattr(db, "_initialize_locked", original)
    assert db.ensure_initialized() == 7


def test_initialization_registry_releases_unowned_store_state(tmp_path):
    db = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    db.ensure_initialized()
    state = weakref.ref(db._initialization)
    del db
    gc.collect()
    assert state() is None


def test_eight_readers_overlap_on_distinct_owned_connections(tmp_path, monkeypatch):
    repo = repository(tmp_path / "workspace.sqlite3")
    job = _create(repo)
    overlap = threading.Barrier(8)
    original = repo._job_in
    connections = []
    lock = threading.Lock()
    class OwnedConnection(sqlite3.Connection):
        closed = False
        def close(self):
            self.closed = True
            return super().close()
    def connect(*args, **kwargs):
        return sqlite3.connect(*args, **kwargs, factory=OwnedConnection)
    monkeypatch.setattr(WorkspaceDatabase, "_open_connection", staticmethod(connect))
    def gated(c, job_id):
        with lock:
            connections.append(c)
        overlap.wait(5)
        return original(c, job_id)
    monkeypatch.setattr(repo, "_job_in", gated)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(repo.get_job, job.job_id) for _ in range(8)]
        assert [f.result(10) for f in futures] == [job] * 8
    assert len({id(c) for c in connections}) == 8
    assert all(c.closed for c in connections)


def test_reader_factory_overlaps_uncommitted_writer_without_dirty_state(tmp_path):
    settings = configured(tmp_path / "workspace.sqlite3")
    repo = SQLiteJobRepository.from_settings(settings, forbidden_secret_values=())
    running = _running(repo)
    entered, release = threading.Event(), threading.Event()
    def gate(phase, _job_id):
        if phase == "after_progress_update":
            entered.set()
            assert release.wait(5)
    writer = SQLiteJobRepository(repo.database, failure_injector=gate, forbidden_secret_values=())
    with ThreadPoolExecutor(max_workers=2) as pool:
        mutation = pool.submit(writer.report_progress, running.job_id,
            expected_revision=running.revision, stage="advance", current=1, total=2)
        try:
            assert entered.wait(5)
            def read():
                independent = SQLiteJobRepository.from_settings(settings, forbidden_secret_values=())
                return independent.get_job(running.job_id)
            assert pool.submit(read).result(5) == running
            assert not mutation.done()
        finally:
            release.set()
        committed = mutation.result(5)
    assert repo.get_job(running.job_id) == committed
    assert committed.revision == running.revision + 1


def test_job_and_steps_are_one_snapshot_during_committed_step_transition(tmp_path, monkeypatch):
    reader = repository(tmp_path / "workspace.sqlite3")
    running = _running(reader)
    writer = SQLiteJobRepository(reader.database, forbidden_secret_values=())
    selected, release = threading.Event(), threading.Event()
    original = reader._steps_in
    def paused(c, job_id):
        selected.set()
        assert release.wait(5)
        return original(c, job_id)
    monkeypatch.setattr(reader, "_steps_in", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(reader.get_job, running.job_id)
        try:
            assert selected.wait(5)
            committed = writer.transition_step(running.job_id, running.steps[0].step_id,
                expected_job_revision=running.revision, expected_step_revision=1, target_state="running")
        finally:
            release.set()
        snapshot = future.result(5)
    assert snapshot == running
    assert committed.revision == 3 and committed.steps[0].state == "running"


def test_list_count_and_items_share_one_snapshot(tmp_path, monkeypatch):
    repo = repository(tmp_path / "workspace.sqlite3")
    first = _create(repo)
    selected, release = threading.Event(), threading.Event()
    class CountCursor:
        def __init__(self, cursor):
            self.row = cursor.fetchone()
        def fetchone(self):
            selected.set()
            assert release.wait(5)
            return self.row
    class PausedConnection(sqlite3.Connection):
        def execute(self, sql, *args):
            cursor = super().execute(sql, *args)
            return CountCursor(cursor) if sql.startswith("SELECT COUNT(*) FROM jobs") else cursor
    def connect(*args, **kwargs):
        return sqlite3.connect(*args, **kwargs, factory=PausedConnection)
    monkeypatch.setattr(WorkspaceDatabase, "_open_connection", staticmethod(connect))
    writer = SQLiteJobRepository(repo.database, forbidden_secret_values=())
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(repo.list_jobs)
        try:
            assert selected.wait(5)
            _create(writer, key="second")
        finally:
            release.set()
        page = future.result(5)
    assert page.total == len(page.items) == 1 and page.items[0] == first


def test_concurrent_cas_writers_keep_one_commit_and_ordered_events(tmp_path):
    repo = repository(tmp_path / "workspace.sqlite3")
    running = _running(repo)
    start = threading.Barrier(8)
    def mutate(i):
        start.wait(5)
        try:
            return repo.report_progress(running.job_id, expected_revision=running.revision,
                stage="advance", current=i, total=8)
        except JobConflictError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(mutate, range(8)))
    assert sum(x is not None for x in outcomes) == 1
    current = repo.get_job(running.job_id)
    assert current.revision == 3
    assert [x.sequence for x in repo.list_events(running.job_id)] == [1, 2, 3]


def test_eight_claimants_have_one_owner_and_one_running_event(tmp_path):
    repo = repository(tmp_path / "workspace.sqlite3")
    job = queued(repo)
    start = threading.Barrier(8)
    def claim(_):
        contender = SQLiteJobRepository(WorkspaceDatabase(repo.database.path), forbidden_secret_values=())
        contender.database.ensure_initialized()
        start.wait(5)
        return contender.claim_next_job((("agent", "synthetic_worker"),))
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(claim, range(8)))
    owners = [x for x in outcomes if x is not None]
    assert len(owners) == 1 and owners[0].job_id == job.job_id and owners[0].revision == 2
    assert [e.sequence for e in repo.list_events(job.job_id)] == [1, 2]


def test_bounded_read_event_pollers_and_writer_both_progress(tmp_path):
    repo = repository(tmp_path / "workspace.sqlite3")
    running = _running(repo)
    start = threading.Barrier(9)
    def reader(_):
        start.wait(5)
        for _ in range(25):
            snapshot = repo.get_job(running.job_id)
            assert snapshot.state == "running"
            assert repo.list_jobs().total == 1
            events = repo.list_events(running.job_id)
            assert [e.sequence for e in events] == list(range(1, len(events) + 1))
        return 25
    def writer():
        start.wait(5)
        current = running
        for i in range(20):
            current = repo.report_progress(current.job_id, expected_revision=current.revision,
                stage="advance", current=i, total=20)
        return current
    with ThreadPoolExecutor(max_workers=9) as pool:
        reads = [pool.submit(reader, i) for i in range(8)]
        write = pool.submit(writer)
        assert [f.result(15) for f in reads] == [25] * 8
        final = write.result(15)
    assert final.revision == 22
    assert len(repo.list_events(running.job_id)) == 22


@pytest.mark.parametrize("queued_state", [False, True])
def test_cancel_under_read_load_keeps_revisions_and_terminal_immutability(tmp_path, queued_state):
    repo = repository(tmp_path / "workspace.sqlite3")
    job = _create(repo) if queued_state else _running(repo)
    start = threading.Barrier(3)
    def read():
        start.wait(5)
        for _ in range(20):
            assert repo.get_job(job.job_id).state in {job.state, "cancelling", "cancelled"}
            assert repo.list_events(job.job_id)
    def cancel():
        start.wait(5)
        return repo.request_cancellation(job.job_id, expected_revision=job.revision)
    with ThreadPoolExecutor(max_workers=3) as pool:
        reads = [pool.submit(read) for _ in range(2)]
        result = pool.submit(cancel).result(10)
        for f in reads: f.result(10)
    assert result.state == ("cancelled" if queued_state else "cancelling")
    with pytest.raises(JobConflictError):
        repo.request_cancellation(job.job_id, expected_revision=job.revision)
    if not queued_state:
        result = repo.acknowledge_cancellation(job.job_id, expected_revision=result.revision)
    with pytest.raises(JobTransitionError):
        repo.transition_job(job.job_id, expected_revision=result.revision, target_state="running")
    assert repo.get_job(job.job_id) == result


def test_connection_setup_failure_closes_owned_handle(tmp_path, monkeypatch):
    opened, closed = [], []
    class FailingConnection(sqlite3.Connection):
        def execute(self, sql, *args):
            if sql == "PRAGMA trusted_schema = OFF":
                raise sqlite3.OperationalError("synthetic configuration failure")
            return super().execute(sql, *args)
        def close(self):
            closed.append(self)
            return super().close()
    def connect(*args, **kwargs):
        c = sqlite3.connect(*args, **kwargs, factory=FailingConnection)
        opened.append(c)
        return c
    monkeypatch.setattr(WorkspaceDatabase, "_open_connection", staticmethod(connect))
    db = WorkspaceDatabase(tmp_path / "workspace.sqlite3")
    with pytest.raises(WorkspaceDatabaseStateError):
        db.ensure_initialized()
    assert opened == closed and len(closed) == 1


def test_snapshot_failure_closes_owned_handle_and_warm_reads_have_no_writer_wait(tmp_path, monkeypatch):
    repo = repository(tmp_path / "workspace.sqlite3")
    job = _create(repo)
    owned = []
    original = repo.database._connect
    def opened():
        c = original()
        owned.append(c)
        return c
    monkeypatch.setattr(repo.database, "_connect", opened)
    with pytest.raises(RuntimeError):
        with repo.database.connection(snapshot=True):
            raise RuntimeError("synthetic read failure")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        owned[0].execute("SELECT 1")
    with capture("api") as trace:
        repo.database.ensure_initialized()
        assert repo.get_job(job.job_id) == job
    phases = {s.phase for s in trace.records}
    assert "workspace.read" in phases
    assert "workspace.serialized_wait" not in phases and "workspace.initialize" not in phases
