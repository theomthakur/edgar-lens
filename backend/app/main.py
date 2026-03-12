from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers.analysis import router as analysis_router
from app.routers.evals import router as evals_router
from app.routers.filings import router as filings_router
from app.routers.health import router as health_router
from app.routers.reports import router as reports_router

app = FastAPI(title="Finance Research Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(filings_router)
app.include_router(analysis_router)
app.include_router(reports_router)
app.include_router(evals_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Finance Research Agent API running"}
