from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .db import init_db
from .routers import course,reviews,repositories,instructor,dev,auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app=FastAPI(title="ETIS Engineering Studio API",version="0.2.0",description="Evidence-centered engineering judgment environment for COMP 330", lifespan=lifespan)

app.include_router(course.router)
app.include_router(reviews.router)
app.include_router(repositories.router)
app.include_router(instructor.router)
app.include_router(dev.router)
app.include_router(auth.router)

@app.get("/health")
def health():
    return {"status":"ok","service":"etis-engineering-studio","version":"0.2.0"}

static_dir=Path(__file__).parent/"static"
if static_dir.exists():
    app.mount("/assets",StaticFiles(directory=static_dir),name="assets")

@app.get("/",response_class=HTMLResponse)
def home():
    return FileResponse(static_dir/"index.html")
