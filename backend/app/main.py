"""EvidenceFlow FastAPI application factory and entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.dedup import router as dedup_router
from app.api.health import router as health_router
from app.api.queries import router as queries_router
from app.api.reviews import router as reviews_router
from app.api.runs import router as runs_router
from app.core.database import SessionLocal, utc_now
from app.core.errors import AppError
from app.models.audit import PipelineRun


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup self-healing: Clean up any interrupted pipeline runs
    db = SessionLocal()
    try:
        interrupted = db.query(PipelineRun).filter(PipelineRun.status == "running").all()
        for run in interrupted:
            run.status = "failed"
            run.error_message = "Process interrupted during server restart or shutdown."
            run.completed_at = utc_now()
        if interrupted:
            db.commit()
    finally:
        db.close()
    yield
    # Shutdown logic if any


def create_app() -> FastAPI:
    app = FastAPI(
        title="EvidenceFlow API",
        description="Mini-Rayyan systematic review tool backend core API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register standard error envelope handlers
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_envelope(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": jsonable_encoder(exc.errors())},
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "details": {},
                }
            },
        )

    # Mount routers
    app.include_router(health_router, prefix="/api")
    app.include_router(reviews_router, prefix="/api")
    app.include_router(queries_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")
    app.include_router(dedup_router, prefix="/api")

    return app


app = create_app()
