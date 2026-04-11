"""
Clarity FastAPI backend.

Entry point: uvicorn main:app --reload
"""

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import structlog

log = structlog.get_logger()

app = FastAPI(
    title="Clarity API",
    description="Backend for Clarity life load intelligence",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_hook_secret(x_clarity_secret: str = Header(...)):
    """Validate shared secret on all Claude Code hook endpoints."""
    expected = os.environ.get("CLARITY_HOOK_SECRET", "")
    if not expected or x_clarity_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid hook secret")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "clarity-api"}


@app.post("/api/hooks/session-stop")
async def session_stop(
    request: Request,
    x_clarity_secret: str = Header(...),
):
    verify_hook_secret(x_clarity_secret)
    body = await request.json()
    log.info("session_stop_hook", session_id=body.get("session_id"))
    return {"received": True}
