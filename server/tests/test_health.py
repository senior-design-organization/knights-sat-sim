import asyncio

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health(monkeypatch) -> None:
    monkeypatch.delenv("RUNTIME_DEPLOYMENT", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_waits_for_cleanup_migrations_and_persistent_maintenance(
    tmp_path, monkeypatch
) -> None:
    from api.readiness import StartupReadiness

    marker = tmp_path / "active"
    monkeypatch.setenv("RUNTIME_DEPLOYMENT", "test")
    readiness = StartupReadiness(marker)
    events = []

    class Runtime:
        async def reconcile(self):
            events.append("cleanup")

    def migrate():
        events.append("migration")

    app.state.readiness = readiness
    try:
        assert client.get("/health").status_code == 503
        marker.touch()
        asyncio.run(readiness.initialize(Runtime(), migrate))
        assert events == ["cleanup", "migration"]
        assert client.get("/health").status_code == 503
        marker.unlink()
        assert client.get("/health").json() == {"status": "ok"}
        marker.symlink_to(tmp_path / "missing")
        assert client.get("/health").status_code == 503
    finally:
        del app.state.readiness


def test_cleanup_or_migration_failure_stays_unready_until_explicit_retry(
    tmp_path, monkeypatch
) -> None:
    from api.readiness import StartupReadiness

    readiness = StartupReadiness(tmp_path / "active")
    monkeypatch.setenv("RUNTIME_DEPLOYMENT", "test")

    class Runtime:
        async def reconcile(self):
            raise RuntimeError("injected cleanup failure")

    def migrate():
        raise RuntimeError("injected migration failure")

    app.state.readiness = readiness
    try:
        with pytest.raises(RuntimeError, match="cleanup"):
            asyncio.run(readiness.initialize(Runtime(), migrate))
        assert client.get("/health").status_code == 503

        class RecoveredRuntime:
            async def reconcile(self):
                pass

        with pytest.raises(RuntimeError, match="migration"):
            asyncio.run(readiness.initialize(RecoveredRuntime(), migrate))
        assert client.get("/health").status_code == 503
        asyncio.run(readiness.initialize(RecoveredRuntime(), lambda: None))
        assert client.get("/health").status_code == 200
    finally:
        del app.state.readiness
