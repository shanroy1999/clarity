"""
Clarity pipeline checkpointing.

Saves pipeline state at each stage so a failed run can resume
from the last successful checkpoint rather than restarting.

Checkpoint stages:
  0 - pipeline_start
  1 - snapshot_loaded
  2 - parallel_analysis_complete
  3 - report_generated
  4 - pipeline_complete

Usage:
    cp = Checkpoint(week_start)
    await cp.save(stage=1, data={"snapshot": snapshot})

    # On resume:
    state = await cp.load()
    if state["stage"] >= 1:
        snapshot = state["data"]["snapshot"]
        # skip re-loading
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

log = structlog.get_logger()

CHECKPOINT_DIR = Path(".clarity-cache/checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

STAGES = {
    0: "pipeline_start",
    1: "snapshot_loaded",
    2: "parallel_analysis_complete",
    3: "report_generated",
    4: "pipeline_complete",
}


class Checkpoint:
    """Manages checkpoint state for a single pipeline run."""

    def __init__(self, week_start: str):
        self.week_start = week_start
        self.path = CHECKPOINT_DIR / f"checkpoint-{week_start}.json"

    async def save(self, stage: int, data: dict) -> None:
        """Save checkpoint at a given stage."""
        checkpoint = {
            "week_start": self.week_start,
            "stage": stage,
            "stage_name": STAGES.get(stage, "unknown"),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        self.path.write_text(json.dumps(checkpoint, indent=2))
        log.info(
            "checkpoint_saved",
            week_start=self.week_start,
            stage=stage,
            stage_name=STAGES.get(stage),
        )

    def load(self) -> dict | None:
        """
        Load existing checkpoint if present.
        Returns None if no checkpoint exists.
        """
        if not self.path.exists():
            return None
        try:
            checkpoint = json.loads(self.path.read_text())
            log.info(
                "checkpoint_loaded",
                week_start=self.week_start,
                stage=checkpoint.get("stage"),
                stage_name=checkpoint.get("stage_name"),
                saved_at=checkpoint.get("saved_at"),
            )
            return checkpoint
        except Exception as e:
            log.warning("checkpoint_corrupt", error=str(e))
            return None

    def clear(self) -> None:
        """Delete checkpoint after successful pipeline completion."""
        if self.path.exists():
            self.path.unlink()
            log.info("checkpoint_cleared", week_start=self.week_start)

    def exists(self) -> bool:
        return self.path.exists()