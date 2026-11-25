"""CardioLink API — FastAPI entrypoint.

A REST API modeled on IHE profiles (PIX, PDQ, XDS, ATNA) for the
CardioLink cardiology-interoperability prototype.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .database import ensure_schema, init_db
from .routers import audit, auth, documents, exams, patients, pix, studies
from .seed import ensure_pix_data, seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_schema()
    seed_if_empty()
    ensure_pix_data()
    yield


app = FastAPI(
    title="CardioLink API",
    version="0.1.0",
    description="REST API modeled on IHE profiles (PIX ITI-9, PDQ, XDS, ATNA ITI-20).",
    lifespan=lifespan,
)

origins = ["*"] if CORS_ORIGINS.strip() == "*" else [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "CardioLink API"}


for r in (auth, patients, exams, studies, documents, audit, pix):
    app.include_router(r.router)
