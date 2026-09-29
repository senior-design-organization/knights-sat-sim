"""Startup ordering for the runtime and persistent deployment marker."""

import asyncio
import os
from collections.abc import Callable
from pathlib import Path

from api.runtime import RuntimeController


class StartupReadiness:
    def __init__(self, maintenance_marker: Path):
        self.maintenance_marker = maintenance_marker
        self.initialized = False

    async def initialize(
        self, runtime: RuntimeController, migrate: Callable[[], None]
    ) -> None:
        self.initialized = False
        await runtime.reconcile()
        await asyncio.to_thread(migrate)
        self.initialized = True

    @property
    def ready(self) -> bool:
        try:
            return (
                self.initialized
                and self.maintenance_marker.parent.is_dir()
                and not os.path.lexists(self.maintenance_marker)
            )
        except OSError:
            return False
