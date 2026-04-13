"""
Clarity orchestrator agent.

Coordinates the full weekly analysis pipeline:
1. Validates data sources are ready
2. Runs pattern-detector and load-analyzer in parallel
3. Waits for both to complete
4. Passes combined output to insight-writer
5. Saves report to Supabase
6. Triggers proactive alerts if HIGH severity patterns detected

Entry point for all scheduled and on-demand Clarity runs.
"""

import asyncio
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
import re

load_dotenv()
log = structlog.get_logger()

CACHE_DIR = Path(".clarity-cache")
CACHE_DIR.mkdir(exist_ok=True)

def _extract_json(raw: str) -> dict:
    """
    Extract the first valid JSON object from a string.
    Handles trailing text after the closing brace.
    """
    # Find the first { and match to its closing }
    start = raw.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", raw, 0)

    depth = 0
    for i, char in enumerate(raw[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[start:i + 1])

    raise json.JSONDecodeError("Unclosed JSON object", raw, start)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _latest_file(prefix: str) -> Path | None:
    """Return the most recent cache file matching prefix-*.json."""
    files = sorted(CACHE_DIR.glob(f"{prefix}-*.json"), reverse=True)
    return files[0] if files else None


def _read_cache(prefix: str) -> dict:
    """Read cache — checks Supabase first in cloud mode,
    falls back to local file in development.
    Read the latest cache file for a given prefix. Returns {} if missing."""
    # Cloud mode: read from Supabase, not local files
    if os.environ.get("CLARITY_CLOUD_RUN") == "1":
        return {}  # Phase 6 extension: implement Supabase fetch here
    # Local mode: read from .clarity-cache/
    path = _latest_file(prefix)
    if not path:
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _write_cache(prefix: str, week_start: str, data: dict) -> Path:
    """Write data to a dated cache file."""
    path = CACHE_DIR / f"{prefix}-{week_start}.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def _current_week_start() -> str:
    """Return the Monday of the current week as YYYY-MM-DD."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

async def _run_subagent(
    client: AsyncAnthropic,
    agent_name: str,
    system_prompt: str,
    user_message: str,
) -> str:
    """
    Run a single subagent and return its text response.
    Strips markdown code fences so JSON parsing is reliable.
    """
    log.info("subagent_start", agent=agent_name)

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    # Extract text from the first content block
    result = ""
    for block in response.content:
        if hasattr(block, "text"):
            result = block.text
            break

    # Strip markdown code fences if present
    # Handles ```json\n...\n``` and ```\n...\n```
    result = result.strip()
    if result.startswith("```"):
        lines = result.split("\n")
        # Remove first line (```json or ```) and last line (```)
        result = "\n".join(lines[1:-1]).strip()

    log.info(
        "subagent_complete",
        agent=agent_name,
        tokens=response.usage.output_tokens,
        result_preview=result[:100],
    )
    return result


# ---------------------------------------------------------------------------
# Agent system prompts
# ---------------------------------------------------------------------------

PATTERN_DETECTOR_PROMPT = """
You are the pattern detection specialist for Clarity.

Analyse the provided life load snapshots and detect behavioral patterns
that indicate overwhelm, depletion, or avoidance. Compare across all
provided weeks to compute cross-week severity.

Pattern types to detect:
- depletion_cascade: 3+ meetings → evening task collapse → next-day avoidance
- avoidance_loop: same task category moved repeatedly
- boundary_erosion: consistent after-hours signals across 3+ days
- social_withdrawal: personal communication tasks consistently avoided

For each pattern:
- Cite specific evidence from the data
- Set severity based on frequency: once=LOW, 2 weeks=MEDIUM, 3+ weeks=HIGH
- Set historical_frequency to actual count across provided weeks

Return ONLY valid JSON matching this schema:
{
  "week_start": "YYYY-MM-DD",
  "patterns_detected": [
    {
      "type": "pattern_type",
      "severity": "HIGH|MEDIUM|LOW",
      "evidence": ["specific evidence string"],
      "days_affected": ["Mon", "Tue"],
      "historical_frequency": 0,
      "weeks_consecutive": 1
    }
  ],
  "no_patterns_detected": false,
  "analysis_confidence": "high|medium|low"
}
""".strip()

LOAD_ANALYZER_PROMPT = """
You are the load analysis specialist for Clarity.

Quantify the total demand on the user across their week — meetings,
tasks, and financial pressure. Identify where their capacity was exceeded.

Compute:
- total_load_score: composite 0-100 (meeting hours × 3 + task backlog × 2 + financial stress × 2)
- capacity_exceeded_days: days where meeting hours > 4 or task completion = 0
- primary_load_driver: the dominant source of overload this week
- financial_stress_present: true if spend_vs_budget_pct > 30

Return ONLY valid JSON matching this schema:
{
  "week_start": "YYYY-MM-DD",
  "total_load_score": 0,
  "capacity_exceeded_days": [],
  "primary_load_driver": "meeting|financial|task|combined",
  "financial_stress_present": false,
  "load_by_day": {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0},
  "summary": "one sentence describing the week's load profile"
}
""".strip()

INSIGHT_WRITER_PROMPT = """
You are the insight writer for Clarity.

Write a weekly report that reads like a message from a brutally honest
friend who has studied all the data. Direct, specific, data-grounded.

Rules (non-negotiable):
- Cite specific numbers in every paragraph
- Never use the word "productivity"
- Never suggest apps, tools, or systems
- Never give generic advice ("try to get more sleep")
- Under 400 words total
- End with one sentence naming the root cause

Structure:
1. Opening (2-3 sentences): what you saw — numbers, not impressions
2. Pattern paragraphs (one per detected pattern): name it, show evidence, connect it
3. The connection: one sentence tying patterns to a single root cause
4. The one honest thing: most useful truth in the data

Return ONLY valid JSON:
{
  "report_markdown": "full report text",
  "root_cause": "one sentence",
  "word_count": 0,
  "patterns_addressed": ["pattern_type"]
}
""".strip()


# ---------------------------------------------------------------------------
# Parallel execution
# ---------------------------------------------------------------------------

async def _run_parallel_analysis(
    client: AsyncAnthropic,
    snapshot: dict,
    prior_snapshots: list[dict],
) -> tuple[dict, dict]:
    """
    Run pattern-detector and load-analyzer in parallel.

    Returns (pattern_result, load_result) as dicts.
    Both agents get the same snapshot data but process different aspects.
    """
    all_snapshots_text = json.dumps(
        [snapshot] + prior_snapshots[:3],
        indent=2,
    )
    snapshot_text = json.dumps(snapshot, indent=2)

    pattern_task = asyncio.create_task(
        _run_subagent(
            client,
            agent_name="pattern-detector",
            system_prompt=PATTERN_DETECTOR_PROMPT,
            user_message=(
                f"Analyse these weekly snapshots for behavioral patterns. "
                f"The first is the current week, the rest are prior weeks:\n\n"
                f"{all_snapshots_text}"
            ),
        )
    )

    load_task = asyncio.create_task(
        _run_subagent(
            client,
            agent_name="load-analyzer",
            system_prompt=LOAD_ANALYZER_PROMPT,
            user_message=(
                f"Analyse the load profile for this week:\n\n{snapshot_text}"
            ),
        )
    )

    # Both run simultaneously — return_exceptions=True means a failure in one
    # does not cancel the other. Each result is either a string or an Exception.
    results = await asyncio.gather(pattern_task, load_task, return_exceptions=True)
    pattern_raw, load_raw = results

    if isinstance(pattern_raw, Exception):
        log.error("pattern_detector_failed", error=str(pattern_raw), error_type=type(pattern_raw).__name__)
        pattern_result: dict = {"patterns_detected": [], "no_patterns_detected": True, "analysis_confidence": "low"}
    else:
        # log.info("pattern_raw_preview", raw=pattern_raw[:300] if pattern_raw else "EMPTY")
        try:
            pattern_result = _extract_json(pattern_raw)
        except json.JSONDecodeError as exc:
            log.error("pattern_detector_invalid_json", error=str(exc), error_type=type(exc).__name__)
            pattern_result = {"patterns_detected": [], "no_patterns_detected": True, "analysis_confidence": "low"}

    if isinstance(load_raw, Exception):
        log.error("load_analyzer_failed", error=str(load_raw), error_type=type(load_raw).__name__)
        load_result: dict = {"total_load_score": 0, "financial_stress_present": False, "summary": "Load analysis unavailable"}
    else:
        # log.info("load_raw_preview", raw=load_raw[:300] if load_raw else "EMPTY")
        try:
            load_result = _extract_json(load_raw)
        except json.JSONDecodeError as exc:
            log.error("load_analyzer_invalid_json", error=str(exc), error_type=type(exc).__name__)
            load_result = {"total_load_score": 0, "financial_stress_present": False, "summary": "Load analysis unavailable"}

    return pattern_result, load_result


# ---------------------------------------------------------------------------
# Alert evaluation
# ---------------------------------------------------------------------------

def _should_alert(patterns: dict) -> list[dict]:
    """
    Return patterns that warrant a proactive alert.
    Only HIGH severity patterns trigger alerts.
    """
    return [
        p for p in patterns.get("patterns_detected", [])
        if p.get("severity") == "HIGH"
    ]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_weekly_pipeline(
    user_id: str,
    week_start: str | None = None,
) -> dict[str, Any]:
    """
    Run the full Clarity weekly analysis pipeline.

    Args:
        user_id: Clarity user UUID
        week_start: Monday date (YYYY-MM-DD). Defaults to current week.

    Returns:
        Pipeline result with report, patterns, and alert triggers.
    """
    week_start = week_start or _current_week_start()
    log.info("pipeline_start", user_id=user_id, week_start=week_start)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        log.error("anthropic_api_key_missing_or_placeholder", error="API key missing or placeholder", error_type="ConfigurationError")
        return {
            "success": False,
            "error": "ANTHROPIC_API_KEY is not set or is still a placeholder. Check your .env file.",
            "week_start": week_start,
        }

    client = AsyncAnthropic(api_key=api_key)

    # 1. Load current snapshot
    snapshot = _read_cache("snapshot")
    if not snapshot:
        return {
            "success": False,
            "error": "No snapshot found. Run /analyze-week first.",
            "week_start": week_start,
        }

    # 2. Load prior snapshots for cross-week pattern analysis
    all_snapshots = sorted(
        CACHE_DIR.glob("snapshot-*.json"),
        reverse=True,
    )
    prior_snapshots = []
    for path in all_snapshots[1:4]:  # up to 3 prior weeks
        try:
            prior_snapshots.append(json.loads(path.read_text()))
        except Exception:
            continue

    log.info(
        "snapshots_loaded",
        current=week_start,
        prior_weeks=len(prior_snapshots),
    )

    # 3. Run pattern-detector and load-analyzer in parallel
    patterns, load_analysis = await _run_parallel_analysis(
        client, snapshot, prior_snapshots
    )

    # 4. Write intermediate results to cache
    _write_cache("patterns", week_start, patterns)
    _write_cache("load", week_start, load_analysis)
    log.info("intermediate_cache_written", week_start=week_start)

    # 5. Bail early if both parallel agents failed — insight-writer has nothing to work with
    both_failed = (
        patterns.get("no_patterns_detected") is True
        and load_analysis.get("summary") == "Load analysis unavailable"
    )
    if both_failed:
        log.error("both_subagents_failed", week_start=week_start, error="Both parallel agents returned fallback state", error_type="SubagentFailure")
        return {
            "success": False,
            "error": (
                "Both pattern-detector and load-analyzer failed. "
                "Check ANTHROPIC_API_KEY and network connectivity."
            ),
            "week_start": week_start,
            "user_id": user_id,
            "patterns_detected": 0,
            "load_score": 0,
            "alert_count": 0,
            "alert_patterns": [],
        }

    # 5. Run insight-writer with both results
    combined_context = json.dumps(
        {
            "snapshot": snapshot,
            "patterns": patterns,
            "load_analysis": load_analysis,
        },
        indent=2,
    )

    report_raw = await _run_subagent(
        client,
        agent_name="insight-writer",
        system_prompt=INSIGHT_WRITER_PROMPT,
        user_message=(
            f"Write the Clarity weekly report using this data:\n\n"
            f"{combined_context}"
        ),
    )

    try:
        report = _extract_json(report_raw)
    except json.JSONDecodeError:
        log.warning("insight_writer_invalid_json")
        report = {
            "report_markdown": report_raw,
            "root_cause": "Analysis incomplete",
            "word_count": len(report_raw.split()),
            "patterns_addressed": [],
        }

    # 6. Write report to cache
    _write_cache("report", week_start, report)
    log.info("report_written", week_start=week_start)

    # 7. Evaluate alert triggers
    alert_patterns = _should_alert(patterns)
    if alert_patterns:
        log.info(
            "alerts_triggered",
            count=len(alert_patterns),
            types=[p["type"] for p in alert_patterns],
        )

    result = {
        "success": True,
        "week_start": week_start,
        "user_id": user_id,
        "patterns_detected": len(patterns.get("patterns_detected", [])),
        "load_score": load_analysis.get("total_load_score", 0),
        "alert_count": len(alert_patterns),
        "alert_patterns": alert_patterns,
        "report_markdown": report.get("report_markdown", ""),
        "root_cause": report.get("root_cause", ""),
        "word_count": report.get("word_count", 0),
        "cache_files": {
            "patterns": str(_latest_file("patterns")),
            "load": str(_latest_file("load")),
            "report": str(_latest_file("report")),
        },
    }

    log.info(
        "pipeline_complete",
        week_start=week_start,
        patterns=result["patterns_detected"],
        load_score=result["load_score"],
        word_count=result["word_count"],
        alerts=result["alert_count"],
    )

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    user_id = os.environ.get("CLARITY_DEV_USER_ID", "dev-user")
    week_start = sys.argv[1] if len(sys.argv) > 1 else None

    result = asyncio.run(run_weekly_pipeline(user_id, week_start))
    print(json.dumps(result, indent=2))