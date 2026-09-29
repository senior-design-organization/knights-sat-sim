import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import docker
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.readiness import StartupReadiness
from api.runtime import RuntimeController, RuntimeStorage


@asynccontextmanager
async def lifespan(application: FastAPI):
    client = None
    if os.environ.get("RUNTIME_DEPLOYMENT"):
        application.state.readiness = StartupReadiness(
            Path(os.environ.get("MAINTENANCE_MARKER", "/maintenance/active"))
        )
        try:
            client = await asyncio.to_thread(docker.from_env)
            runtime = RuntimeController(
                client,
                RuntimeStorage.from_environment(),
                image=os.environ["RUNTIME_IMAGE"],
            )
            migrate = getattr(application.state, "migrate", None)
            if migrate is None:

                def migrate() -> None:
                    raise RuntimeError("KSAT-8 migration hook is not installed")

            await application.state.readiness.initialize(runtime, migrate)
        except Exception:
            logging.exception(
                "Startup reconciliation or migration failed; admission stays closed"
            )
    try:
        yield
    finally:
        if client is not None:
            await asyncio.to_thread(client.close)


app = FastAPI(title="Satellite Security Challenge Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    readiness: StartupReadiness | None = getattr(app.state, "readiness", None)
    if os.environ.get("RUNTIME_DEPLOYMENT") and (
        readiness is None or not readiness.ready
    ):
        raise HTTPException(
            503, "Startup cleanup, migrations or maintenance incomplete"
        )
    return {"status": "ok"}
