import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.clusters import router as clusters_router
from app.api.queues import router as queues_router

logging.basicConfig(
    level=logging.DEBUG if settings.server.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("YARN Queue Explorer запущен")
    logger.info(f"  Режим аутентификации: {settings.auth.mode}")
    logger.info(f"  Кластеров настроено: {len(settings.clusters)}")
    for c in settings.clusters:
        logger.info(f"    - {c.name} ({c.id}): {', '.join(c.resource_manager_urls)}")
    logger.info(f"  Сервер: {settings.server.host}:{settings.server.port}")
    logger.info("=" * 60)
    yield
    logger.info("YARN Queue Explorer остановлен")


app = FastAPI(
    title="YARN Queue Explorer",
    description="Web UI для управления очередями Apache YARN Capacity Scheduler",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth_router)
app.include_router(clusters_router)
app.include_router(queues_router)

# Статика фронтенда
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.debug,
    )
