from pathlib import Path
from contextlib import asynccontextmanager
import json
import logging
import sys
import time
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .db import database_readiness, init_db
from .routers import course, reviews, repositories, instructor, dev, auth, admin, onboarding
from .config import get_settings
from .services.challenge_engine import SemanticCoachingUnavailable
from .services.auth import COOKIE_NAME, validate_csrf_token


observability_logger = logging.getLogger("etis.observability")
observability_logger.setLevel(logging.INFO)
observability_logger.propagate = False

if not observability_logger.handlers:
    observability_handler = logging.StreamHandler(sys.stdout)
    observability_handler.setLevel(logging.INFO)
    observability_handler.setFormatter(logging.Formatter("%(message)s"))
    observability_logger.addHandler(observability_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ETIS Engineering Studio API",
    version="0.15.0",
    description="Evidence-centered engineering apprenticeship environment for COMP 330",
    lifespan=lifespan,
)


CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ]
)

PERMISSIONS_POLICY = ", ".join(
    [
        "camera=()",
        "microphone=()",
        "geolocation=()",
    ]
)


@app.middleware("http")
async def enforce_cookie_csrf(request: Request, call_next):
    """
    Require a session-bound CSRF token for state-changing requests that use
    browser cookie authentication.

    Bearer-only API requests do not carry the browser session cookie and remain
    outside the CSRF threat model.
    """
    if request.method.upper() in CSRF_PROTECTED_METHODS:
        session_token = request.cookies.get(COOKIE_NAME)

        if session_token:
            presented = request.headers.get("X-CSRF-Token", "")

            if not validate_csrf_token(session_token, presented):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CSRF validation failed",
                    },
                )

    return await call_next(request)


@app.middleware("http")
async def add_browser_security_headers(request: Request, call_next):
    """
    Apply the browser security baseline consistently to Studio responses.

    HSTS is intentionally handled separately because local development uses
    plain HTTP while production is expected to terminate TLS.
    """
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = PERMISSIONS_POLICY
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY

    if get_settings().etis_env == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


@app.middleware("http")
async def record_safe_request_observability(request: Request, call_next):
    """
    Emit bounded request telemetry without sensitive request content.

    Never log query strings, headers, cookies, request bodies, email addresses,
    bearer/session tokens, exception messages, or other caller-supplied
    sensitive values.
    """
    request_id = str(uuid4())
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)

        route_object = request.scope.get("route")
        route_template = getattr(route_object, "path", "<unmatched>")

        log_fields = {
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "route": route_template,
            "status_code": 500,
            "duration_ms": duration_ms,
            "error_type": type(exc).__name__,
        }

        observability_logger.error(
            json.dumps(log_fields, separators=(",", ":"), sort_keys=True),
            extra=log_fields,
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
            headers={
                "X-Request-ID": request_id,
            },
        )

    duration_ms = round((time.perf_counter() - started) * 1000, 3)

    route_object = request.scope.get("route")
    route_template = getattr(route_object, "path", "<unmatched>")

    log_fields = {
        "event": "http_request",
        "request_id": request_id,
        "method": request.method,
        "route": route_template,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }

    observability_logger.info(
        json.dumps(log_fields, separators=(",", ":"), sort_keys=True),
        extra=log_fields,
    )

    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(course.router)
app.include_router(reviews.router)
app.include_router(repositories.router)
app.include_router(instructor.router)
app.include_router(dev.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(onboarding.router)


@app.get("/ready")
def ready():
    readiness = database_readiness()
    is_ready = bool(
        readiness.get("database_connected")
        and readiness.get("migration_current")
    )

    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ready" if is_ready else "not_ready",
            **readiness,
        },
    )


@app.get("/health")
def health():
    settings = get_settings()
    semantic_ready = bool(settings.etis_semantic_conversation and settings.etis_ai_enabled and settings.openai_api_key and settings.openai_model)
    return {
        "status": "ok",
        "service": "etis-engineering-studio",
        "version": "0.15.0",
        "conversation_mode": "semantic" if semantic_ready else "semantic-required-not-configured",
        "semantic_coaching_ready": semantic_ready,
        "model": settings.openai_model if semantic_ready else None,
        "repository_model": settings.openai_repository_model if semantic_ready else None,
        "critic_model": settings.openai_critic_model if semantic_ready else None,
        "conversation_critic_mode": settings.etis_conversation_critic_mode,
        "prompt_cache_enabled": settings.etis_prompt_cache_enabled,
        "environment": settings.etis_env,
        "entra_sso_ready": bool(settings.entra_client_id and settings.entra_client_secret),
        "github_identity_link_ready": bool(settings.github_oauth_client_id and settings.github_oauth_client_secret),
        "github_app_ready": bool(
            settings.github_app_id
            and settings.github_app_private_key
            and settings.github_app_slug
        ),
    }


@app.exception_handler(SemanticCoachingUnavailable)
async def semantic_coaching_unavailable(_request: Request, exc: SemanticCoachingUnavailable):
    return JSONResponse(
        status_code=503,
        content={
            "detail": str(exc),
            "code": "semantic_coaching_unavailable",
            "action": "Configure OPENAI_API_KEY and OPENAI_MODEL, then restart the API.",
        },
    )


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")


@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(static_dir / "index.html")


@app.get("/github/setup-complete", response_class=HTMLResponse)
def github_setup_complete():
    # GitHub may append installation_id/setup_action query parameters. This
    # endpoint intentionally ignores them: GitHub redirect parameters are not
    # authorization evidence and must never promote repository state.
    return FileResponse(static_dir / "github-setup-complete.html")
