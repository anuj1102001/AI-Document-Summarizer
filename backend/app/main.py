"""Margin API: document intelligence with grounded, cited answers."""

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.errors import install_error_handlers
from app.logging_setup import configure_logging, get_logger, request_id

log = get_logger("app.http")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title="Margin API", version="2.0.0", description="Document intelligence: summaries, cited Q&A, extraction and comparison."
    )
    install_error_handlers(app)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
        return JSONResponse(
            status_code=422, content={"error": {"code": "INVALID_INPUT", "message": f"Invalid {field}: {first.get('msg', 'bad value')}."}}
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def _request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        token = request_id.set(rid)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id.reset(token)
        ms = int((time.perf_counter() - started) * 1000)
        response.headers["x-request-id"] = rid
        response.headers["x-content-type-options"] = "nosniff"
        log.info(
            "request", extra={"method": request.method, "path": request.url.path, "status": response.status_code, "ms": ms, "rid": rid}
        )
        return response

    app.include_router(router)
    return app


app = create_app()
