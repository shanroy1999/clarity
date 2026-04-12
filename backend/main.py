"""
Clarity FastAPI backend.

Entry point: uvicorn main:app --reload
"""

from pathlib import Path
import sys

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import structlog
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
log = structlog.get_logger()

# Add project root to path so agents/ imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def verify_hook_secret(x_clarity_secret: str = Header(...)):
    """Validate shared secret on all Claude Code hook endpoints."""
    expected = os.environ.get("CLARITY_HOOK_SECRET", "")
    if not expected or x_clarity_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid hook secret")

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RunPipelineRequest(BaseModel):
    user_id: str
    week_start: str | None = None

class ConversationRequest(BaseModel):
    user_id: str
    message: str
    history: list[dict] = []

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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

@app.post("/api/pipeline/run")
async def run_pipeline(body: RunPipelineRequest):
    """
    Trigger the full Clarity weekly analysis pipeline.
    Runs pattern-detector and load-analyzer in parallel,
    then generates the weekly report.
    """
    from agents.orchestrator import run_weekly_pipeline

    try:
        result = await run_weekly_pipeline(
            user_id=body.user_id,
            week_start=body.week_start,
        )
        return result
    except Exception as e:
        log.error("pipeline_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/conversation")
async def conversation(body: ConversationRequest):
    """
    Send a message to the Clarity conversation agent.
    Returns the agent response and updated conversation history.
    """
    from agents.conversation import respond

    try:
        response_text, updated_history = await respond(
            user_message=body.message,
            conversation_history=body.history,
            user_id=body.user_id,
        )
        return {
            "response": response_text,
            "history": updated_history,
        }
    except Exception as e:
        log.error("conversation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))