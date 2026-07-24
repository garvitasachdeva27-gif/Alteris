import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db
import auth
import prompts
import execution
import versions
import ab_testing
import analytics

load_dotenv()

app = FastAPI(
    title="Alteris API",
    description="Backend API for the Alteris AI Prompt Engineering Platform",
    version="1.0.0"
)

# In production, FRONTEND_URL is set to your deployed frontend's real origin.
# Locally, it falls back to common dev setups (opening index.html directly,
# or serving it with a simple local server on port 5500/8080).
FRONTEND_URL = os.getenv("FRONTEND_URL")
allowed_origins = [FRONTEND_URL] if FRONTEND_URL else [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "null",  # covers opening index.html directly as a file:// URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def read_root():
    return {"message": "Alteris API is running.", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
@app.head("/")
def head_root():
    return Response(status_code=200)


@app.head("/health")
def head_health():
    return Response(status_code=200)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(prompts.router, tags=["Prompts"])
app.include_router(execution.router, tags=["Execution"])
app.include_router(versions.router, tags=["Versions"])
app.include_router(ab_testing.router, tags=["A/B Testing"])
app.include_router(analytics.router, tags=["Analytics"])
