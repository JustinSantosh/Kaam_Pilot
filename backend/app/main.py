from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app import __version__
from app.agent.deps import Deps, default_deps
from app.agent.graph import build_graph
from app.agent.runtime import Runtime
from app.api import routes_business, routes_chat, routes_files, routes_quotes
from app.api.errors import install_error_handlers
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


def create_app(
    settings: Settings | None = None, deps_factory: DepsFactory | None = None
) -> FastAPI:
    settings = settings or get_settings()
    make_deps = deps_factory or default_deps

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        app.state.catalog = load_catalog()  # invalid catalog → fail at startup, not on a quote

        async with AsyncExitStack() as stack:
            engine = make_engine(records_url(settings.storage_dir))
            stack.push_async_callback(engine.dispose)
            await create_tables(engine)
            app.state.repo = Repo(make_sessionmaker(engine))

            checkpointer = await stack.enter_async_context(
                AsyncSqliteSaver.from_conn_string(str(settings.storage_dir / CHECKPOINTS_DB))
            )
            # Follow-ups (D-013): persistent job store, one scheduler per process.
            scheduler = make_scheduler(settings)
            followups = FollowupService(
                app.state.repo, InAppOutbound(app.state.repo), scheduler, settings
            )
            followups.activate()
            scheduler.start()
            stack.callback(scheduler.shutdown, wait=False)
            app.state.followups = followups

            app.state.deps = make_deps(app.state.catalog, app.state.repo, settings)
            app.state.deps.followups = followups
            app.state.graph = build_graph(app.state.deps, checkpointer)
            app.state.runtime = Runtime(app.state.graph, app.state.repo, followups)
            yield

    app = FastAPI(title="KaamPilot", version=__version__, lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    for module in (routes_chat, routes_business, routes_quotes, routes_files):
        app.include_router(module.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
