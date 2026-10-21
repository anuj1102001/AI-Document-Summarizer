"""One error type for everything the user should see, with a stable machine-readable code."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.logging_setup import get_logger

log = get_logger(__name__)


class AppError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "BAD_REQUEST"):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        # Never leak internals (stack traces, file paths, provider messages) to the client.
        log.exception("unhandled_error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL", "message": "Something went wrong on our side. Please try again."}},
        )
