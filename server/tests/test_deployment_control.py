import asyncio
import os
import stat

import pytest

from api.deployment_control import DeploymentControl


def test_private_close_refuses_busy_and_persists_maintenance(tmp_path):
    async def check():
        lock = asyncio.Lock()
        owned = True
        marker = tmp_path / "active"
        control = DeploymentControl(
            lock, lambda: owned, marker, tmp_path / "control.sock"
        )
        await control.start(deploy_uid=os.getuid())
        try:
            assert stat.S_IMODE(control.socket_path.stat().st_mode) == 0o600

            async def request(command=b"close\n"):
                reader, writer = await asyncio.open_unix_connection(control.socket_path)
                writer.write(command)
                await writer.drain()
                response = await reader.readline()
                writer.close()
                await writer.wait_closed()
                return response

            assert await request(b"wrong\n") == b"invalid\n"
            assert await request() == b"busy\n"
            assert not marker.exists()
            owned = False
            assert await request() == b"closed\n"
            assert marker.exists()
            assert await request() == b"closed\n"
        finally:
            await control.stop()

    asyncio.run(check())


def test_private_close_rejects_distinct_deploy_identity(tmp_path):
    async def check():
        marker = tmp_path / "active"
        control = DeploymentControl(
            asyncio.Lock(), lambda: False, marker, tmp_path / "control.sock"
        )
        with pytest.raises(RuntimeError, match="share a Unix UID"):
            await control.start(deploy_uid=os.getuid() + 1)
        assert not control.socket_path.exists()
        assert not marker.exists()

    asyncio.run(check())


def test_start_and_deployment_close_share_one_lifecycle_lock(tmp_path):
    async def check(start_first):
        lock = asyncio.Lock()
        marker = tmp_path / "active"
        marker.unlink(missing_ok=True)
        owned = False
        control = DeploymentControl(
            lock, lambda: owned, marker, tmp_path / "control.sock"
        )

        async def start():
            nonlocal owned
            async with lock:
                if marker.exists():
                    return False
                owned = True
                return True

        if start_first:
            assert await start()
            assert await control.close_if_idle() == "busy"
            assert not marker.exists()
        else:
            assert await control.close_if_idle() == "closed"
            assert not await start()
            assert marker.exists()

    asyncio.run(check(True))
    asyncio.run(check(False))


def test_close_refuses_instead_of_waiting_forever_for_lifecycle_lock(tmp_path):
    async def check():
        lock = asyncio.Lock()
        marker = tmp_path / "active"
        control = DeploymentControl(lock, lambda: False, marker, tmp_path / "socket")
        async with lock:
            assert await asyncio.wait_for(control.close_if_idle(), 2) == "busy"
        assert not marker.exists()

    asyncio.run(check())


def test_marker_persistence_failure_does_not_report_closed(tmp_path, monkeypatch):
    async def check():
        marker = tmp_path / "active"
        control = DeploymentControl(
            asyncio.Lock(), lambda: False, marker, tmp_path / "control.sock"
        )
        await control.start(deploy_uid=os.getuid())
        try:

            def denied(_):
                raise OSError("injected fsync failure")

            with monkeypatch.context() as patch:
                patch.setattr(os, "fsync", denied)
                reader, writer = await asyncio.open_unix_connection(control.socket_path)
                writer.write(b"close\n")
                await writer.drain()
                assert await reader.readline() == b"error\n"
                writer.close()
                await writer.wait_closed()
            assert marker.exists()  # Failed closure remains conservative.
            assert await control.close_if_idle() == "closed"
        finally:
            await control.stop()

    asyncio.run(check())
