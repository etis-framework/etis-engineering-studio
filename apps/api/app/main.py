from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .db import init_db
from .routers import course, reviews, repositories, instructor, dev, auth, admin, onboarding
from .config import get_settings
from .services.challenge_engine import SemanticCoachingUnavailable
from .services.auth import COOKIE_NAME, validate_csrf_token


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

app.include_router(course.router)
app.include_router(reviews.router)
app.include_router(repositories.router)
app.include_router(instructor.router)
app.include_router(dev.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(onboarding.router)


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
        "github_app_ready": bool(settings.github_app_id or settings.github_app_slug),
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
