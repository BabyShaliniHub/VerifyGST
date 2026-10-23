from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.verifications import router as verification_router
from app.core.config import cors_origins
from app.core.info import SERVICE_VERSION
from app.services.demo.environment import build_demo_environment


def create_app() -> FastAPI:
    application = FastAPI(title="VerifiGST API", version=SERVICE_VERSION)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    application.state.demo = build_demo_environment()
    application.include_router(health_router)
    application.include_router(verification_router)
    return application


app = create_app()
