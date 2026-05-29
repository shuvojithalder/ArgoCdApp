"""Sample API for Kubernetes / Argo CD deployment."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="ArgoCdApp",
    description="Sample Python API for GitOps deployment with Argo CD",
    version="1.0.0",
)


class HealthResponse(BaseModel):
    status: str


class MessageResponse(BaseModel):
    message: str


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Liveness/readiness probe endpoint."""
    return HealthResponse(status="ok")


@app.get("/ready", response_model=HealthResponse, tags=["ops"])
def ready() -> HealthResponse:
    """Readiness probe endpoint."""
    return HealthResponse(status="ready")


@app.get("/", response_model=MessageResponse, tags=["api"])
def root() -> MessageResponse:
    return MessageResponse(message="Hello from ArgoCdApp!")


@app.get("/api/info", response_model=MessageResponse, tags=["api"])
def info() -> MessageResponse:
    return MessageResponse(message="Python FastAPI running on Kubernetes")
