"""Private deployment close operation; the caller supplies KSAT-12's lifecycle lock."""

import asyncio
import os
import socket
import struct
from collections.abc import Callable
from pathlib import Path


class DeploymentControl:
    def __init__(
        self,
        lifecycle_lock: asyncio.Lock,
        is_owned: Callable[[], bool],
        maintenance_marker: Path,
        socket_path: Path,
    ):
        self.lifecycle_lock = lifecycle_lock
        self.is_owned = is_owned
        self.maintenance_marker = maintenance_marker
        self.socket_path = socket_path
        self.server: asyncio.AbstractServer | None = None
        self.deploy_uid: int | None = None
        self.socket_inode: int | None = None

    async def close_if_idle(self) -> str:
        try:
            await asyncio.wait_for(self.lifecycle_lock.acquire(), 1)
        except TimeoutError:
            return "busy"
        try:
            if self.is_owned():
                return "busy"
            write = asyncio.create_task(asyncio.to_thread(self._persist_marker))
            try:
                await asyncio.shield(write)
            except asyncio.CancelledError:
                await write  # Keep the lifecycle lock until the marker write ends.
                raise
            return "closed"
        finally:
            self.lifecycle_lock.release()

    def _persist_marker(self) -> None:
        marker = os.open(
            self.maintenance_marker,
            os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW,
            0o600,
        )
        try:
            os.fsync(marker)
        finally:
            os.close(marker)
        directory = os.open(self.maintenance_marker.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    async def start(self, *, deploy_uid: int) -> None:
        if self.server is not None:
            raise RuntimeError("Deployment control already started")
        # ponytail: the current deploy command and API share UID 0; use a
        # dedicated group and socket ownership if those identities diverge.
        if deploy_uid != os.getuid():
            raise RuntimeError("Deploy and API identities must share a Unix UID")
        parent = self.socket_path.parent.stat()
        if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
            raise RuntimeError("Deployment control directory must be owner-private")
        listener = socket.socket(socket.AF_UNIX)
        bound = False
        try:
            listener.bind(str(self.socket_path))
            bound = True
            os.chmod(self.socket_path, 0o600)
            self.socket_inode = self.socket_path.stat().st_ino
            listener.listen(1)
            self.deploy_uid = deploy_uid
            self.server = await asyncio.start_unix_server(
                self._handle, sock=listener, limit=32
            )
        except BaseException:
            listener.close()
            if bound and self.socket_path.exists():
                self.socket_path.unlink()
            raise

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            peer = writer.get_extra_info("socket")
            credential_option = getattr(socket, "SO_PEERCRED", None)
            if peer is None or credential_option is None:
                result = "denied"
            else:
                _, uid, _ = struct.unpack(
                    "3i", peer.getsockopt(socket.SOL_SOCKET, credential_option, 12)
                )
                if uid != self.deploy_uid:
                    result = "denied"
                elif await asyncio.wait_for(reader.readline(), 2) != b"close\n":
                    result = "invalid"
                else:
                    result = await self.close_if_idle()
        except Exception:
            result = "error"
        writer.write(result.encode() + b"\n")
        try:
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def stop(self) -> None:
        if self.server is None:
            return
        self.server.close()
        await self.server.wait_closed()
        self.server = None
        if (
            self.socket_path.exists()
            and self.socket_path.stat().st_ino == self.socket_inode
        ):
            self.socket_path.unlink()
