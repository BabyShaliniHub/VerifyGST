from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.info import SERVICE_VERSION


def create_app() -> FastAPI:
    application = FastAPI(title="VerifiGST API", version=SERVICE_VERSION)
    application.include_router(health_router)
    return application


app = create_app()
