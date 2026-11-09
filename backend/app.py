from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import CORS_ORIGINS
from backend.db.connection import init_db
from backend.errors import (
    APIError,
    HTTP_ERROR,
    INFERENCE_ERROR,
    NOT_FOUND,
    VALIDATION_ERROR,
)
from backend.routes import analytics, complaints, health


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="BankSense",
    version="0.1.0",
    description=(
        "NLP-based banking complaint triage prototype. Decision support only: "
        "intent predictions are model output, priority is a rule suggestion, and "
        "similar cases come from records stored by this prototype."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(complaints.router)
app.include_router(analytics.router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "BankSense", "docs": "/docs", "health": "/api/health"}


@app.exception_handler(APIError)
async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    location = [str(part) for part in first.get("loc", []) if part != "body"]
    detail = {
        "code": VALIDATION_ERROR,
        "message": first.get("msg", "Invalid request"),
    }
    if location:
        detail["field"] = ".".join(location)
    return JSONResponse(status_code=400, content={"error": detail})


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = NOT_FOUND if exc.status_code == 404 else HTTP_ERROR
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": INFERENCE_ERROR, "message": "Internal server error"}},
    )
