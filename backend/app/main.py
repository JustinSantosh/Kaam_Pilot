import logging
import os
import time
from asyncio import Lock
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import text

from app import __version__
from app.agent.deps import Deps, default_deps
from app.agent.graph import build_graph
from app.agent.runtime import Runtime
from app.api import auth, routes_business, routes_chat, routes_files, routes_quotes
from app.api.errors import error, install_error_handlers
from app.config import Settings, get_settings
from app.db.repo import Repo
from app.db.session import (
    CHECKPOINTS_DB,
    create_tables,
    make_engine,
    make_sessionmaker,
    records_url,
)
from app.schemas.pricing import Catalog
from app.services.catalog import load_catalog
from app.services.followups import FollowupService, make_scheduler
from app.services.outbound import InAppOutbound

DepsFactory = Callable[[Catalog, Repo, Settings], Deps]
logger = logging.getLogger("kaampilot")


def create_app(
    settings: Settings | None = None, deps_factory: DepsFactory | None = None
) -> FastAPI:
    settings = settings or get_settings()
    make_deps = deps_factory or default_deps

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configured_workers = os.getenv("WEB_CONCURRENCY") or os.getenv("UVICORN_WORKERS")
        if configured_workers and int(configured_workers) > 1:
            logger.warning(
                "multiple workers are unsupported with the SQLite scheduler",
                extra={"worker_count": int(configured_workers)},
            )
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        app.state.catalog = load_catalog()  # invalid catalog → fail at startup, not on a quote

        async with AsyncExitStack() as stack:
            engine = make_engine(
                records_url(settings.storage_dir),
                busy_timeout_ms=settings.sqlite_busy_timeout_ms,
            )
            stack.push_async_callback(engine.dispose)
            await create_tables(engine)
            app.state.repo = Repo(make_sessionmaker(engine))
            app.state.engine = engine

            checkpointer = await stack.enter_async_context(
                AsyncSqliteSaver.from_conn_string(str(settings.storage_dir / CHECKPOINTS_DB))
            )
            app.state.checkpointer = checkpointer
            # Follow-ups (D-013): persistent job store, one scheduler per process.
            scheduler = make_scheduler(settings)
            followups = FollowupService(
                app.state.repo, InAppOutbound(app.state.repo), scheduler, settings
            )
            followups.activate()
            scheduler.start()
            stack.callback(scheduler.shutdown, wait=False)
            app.state.followups = followups
            app.state.scheduler = scheduler

            app.state.deps = make_deps(app.state.catalog, app.state.repo, settings)
            app.state.deps.followups = followups
            app.state.graph = build_graph(app.state.deps, checkpointer)
            app.state.runtime = Runtime(app.state.graph, app.state.repo, followups)
            yield

    app = FastAPI(title="KaamPilot", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    rate_limit_state: dict[str, tuple[int, int]] = {}
    rate_limit_lock = Lock()

    @app.middleware("http")
    async def limit_chat_requests(request: Request, call_next):
        if request.method == "POST" and request.url.path in {
            "/api/chat/send",
            "/api/chat/send-audio",
        }:
            client_ip = request.client.host if request.client else "unknown"
            now = int(time.monotonic())
            window = now // 60
            async with rate_limit_lock:
                previous_window, count = rate_limit_state.get(client_ip, (window, 0))
                count = count + 1 if previous_window == window else 1
                rate_limit_state[client_ip] = (window, count)
                if count > settings.chat_rate_limit_per_minute:
                    response = error(429, "rate_limited", "too many chat requests; retry shortly")
                    response.headers["Retry-After"] = str(60 - now % 60)
                    return response
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    install_error_handlers(app)
    app.include_router(auth.router)
    for module in (routes_chat, routes_business, routes_quotes, routes_files):
        app.include_router(module.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        checks = {"records_db": False, "checkpointer": False, "scheduler": False}
        try:
            async with request.app.state.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            checks["records_db"] = True
        except Exception:
            logger.exception("readiness check failed", extra={"component": "records_db"})
        try:
            await request.app.state.checkpointer.aget_tuple(
                {"configurable": {"thread_id": "__readiness__"}}
            )
            checks["checkpointer"] = True
        except Exception:
            logger.exception("readiness check failed", extra={"component": "checkpointer"})
        checks["scheduler"] = bool(request.app.state.scheduler.running)
        status = "ready" if all(checks.values()) else "not_ready"
        return JSONResponse(
            status_code=200 if status == "ready" else 503,
            content={"status": status, "checks": checks},
        )

    return app


app = create_app()
