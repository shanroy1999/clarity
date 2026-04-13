"""
Clarity Agent SDK runner.

Uses the Claude Agent SDK to run Clarity analysis with full
Claude Code tool access — file reading, bash execution, and
MCP connections — rather than raw API calls.

This gives agents access to the actual .clarity-cache/ files
and can run the ingestion skills directly rather than passing
data through function arguments.

Use this for the full agentic pipeline where agents need to
read files, execute commands, and use MCP tools.
Use orchestrator.py for the lightweight API-only pipeline.
"""

import asyncio
import json
import os
from pathlib import Path

import structlog
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
log = structlog.get_logger()


async def run_analysis_with_sdk(
    week_start: str,
    user_id: str,
) -> dict:
    """
    Run Clarity weekly analysis using the Claude Agent SDK.

    The SDK gives Claude full tool access — it can read cache files,
    run bash commands, and use MCP servers directly.
    This is the production path for the full agentic experience.

    Args:
        week_start: Monday date (YYYY-MM-DD)
        user_id: Clarity user UUID

    Returns:
        Pipeline result dict
    """
    try:
        from claude_code_sdk import query, ClaudeCodeOptions
    except ImportError:
        log.error("agent_sdk_not_installed")
        return {
            "success": False,
            "error": "claude-code-sdk not installed. Run: pip install claude-code-sdk",
        }

    log.info("sdk_pipeline_start", week_start=week_start, user_id=user_id)

    prompt = f"""
You are running the Clarity weekly analysis pipeline for week starting {week_start}.

Follow these steps in order:

1. Read .clarity-cache/snapshot-{week_start}.json to load the week's data.
   If it doesn't exist, report that and stop.

2. Read up to 3 prior snapshots from .clarity-cache/ for cross-week context.

3. Analyse the data for these pattern types:
   - depletion_cascade: heavy meeting days → evening task collapse
   - avoidance_loop: same task category moved repeatedly
   - boundary_erosion: consistent after-hours signals
   - social_withdrawal: personal tasks consistently avoided

4. Compute load analysis:
   - total_load_score (0-100)
   - capacity_exceeded_days
   - primary_load_driver

5. Write patterns to .clarity-cache/patterns-{week_start}.json
6. Write load analysis to .clarity-cache/load-{week_start}.json

7. Generate the weekly report in the voice of a brutally honest friend:
   - Cite specific numbers in every paragraph
   - Under 400 words
   - End with one sentence naming the root cause

8. Write report to .clarity-cache/report-{week_start}.json as:
   {{"report_markdown": "...", "root_cause": "...", "word_count": N}}

9. Return a JSON summary of what was found.
""".strip()

    result_text = ""

    async for message in query(
        prompt=prompt,
        options=ClaudeCodeOptions(
            max_turns=20,
            cwd=str(Path(__file__).parent.parent),
            allowed_tools=["Read", "Write", "Bash"],
        ),
    ):
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    result_text = block.text

    log.info("sdk_pipeline_complete", week_start=week_start)

    # Parse final result
    try:
        from agents.orchestrator import _extract_json
        result = _extract_json(result_text)
        result["success"] = True
        result["week_start"] = week_start
        return result
    except Exception:
        return {
            "success": True,
            "week_start": week_start,
            "raw_output": result_text[:500],
        }


if __name__ == "__main__":
    import sys

    user_id = os.environ.get("CLARITY_DEV_USER_ID", "dev-user")
    week_start = sys.argv[1] if len(sys.argv) > 1 else "2026-04-07"

    result = asyncio.run(run_analysis_with_sdk(week_start, user_id))
    print(json.dumps(result, indent=2))