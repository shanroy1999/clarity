"""
Clarity proactive alert dispatcher.

Called by the orchestrator when HIGH severity patterns are detected.
Sends alerts via available channels : currently a webhook endpoint
that can be connected to phone notifications via Claude Code channels.

Usage:
    python3 scripts/send-alert.py '{"type": "depletion_cascade", "severity": "HIGH", ...}'
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import structlog
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
log = structlog.get_logger()


ALERT_MESSAGES = {
    "depletion_cascade": (
        "Clarity: Heavy meeting load this week is setting up the same "
        "depletion pattern. Your evenings are at risk."
    ),
    "avoidance_loop": (
        "Clarity: A task you keep moving has been deferred {count} times. "
        "Worth looking at today."
    ),
    "boundary_erosion": (
        "Clarity: Work has expanded into your mornings and evenings "
        "for 3+ consecutive days."
    ),
    "social_withdrawal": (
        "Clarity: Personal tasks have been untouched all week. "
        "This one matters more than it looks."
    ),
}


def _format_message(pattern: dict) -> str:
    """Format a pattern dict into a human-readable alert message."""
    pattern_type = pattern.get("type", "unknown")
    template = ALERT_MESSAGES.get(
        pattern_type,
        "Clarity: A pattern worth your attention was detected this week.",
    )

    # Fill in dynamic values if template has placeholders
    if "{count}" in template:
        count = pattern.get("historical_frequency", 1) + 1
        template = template.format(count=count)

    return template


async def send_webhook_alert(pattern: dict, webhook_url: str) -> bool:
    """
    POST an alert to a webhook endpoint.

    This endpoint can be:
    - A Claude Code channel webhook
    - A personal webhook (ntfy.sh, Pushover, etc.)
    - The Clarity FastAPI backend /api/alerts endpoint
    """
    message = _format_message(pattern)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "pattern_type": pattern.get("type"),
        "severity": pattern.get("severity"),
        "source": "clarity",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            log.info(
                "alert_sent",
                pattern_type=pattern.get("type"),
                status=response.status_code,
            )
            return True
    except Exception as e:
        log.error("alert_failed", error=str(e), pattern_type=pattern.get("type"))
        return False


async def dispatch_alerts(patterns: list[dict]) -> dict:
    """
    Send alerts for all HIGH severity patterns.

    Checks for configured alert channels in priority order:
    1. CLARITY_ALERT_WEBHOOK : custom webhook URL
    2. CLARITY_NTFY_TOPIC : ntfy.sh topic for phone notifications
    3. Fallback: write to .clarity-cache/pending-alerts.json
    """
    if not patterns:
        return {"sent": 0, "failed": 0}

    high_patterns = [p for p in patterns if p.get("severity") == "HIGH"]
    if not high_patterns:
        log.info("no_high_severity_patterns")
        return {"sent": 0, "failed": 0}

    sent = 0
    failed = 0

    # Option 1: Custom webhook
    webhook_url = os.environ.get("CLARITY_ALERT_WEBHOOK")
    if webhook_url:
        for pattern in high_patterns:
            success = await send_webhook_alert(pattern, webhook_url)
            if success:
                sent += 1
            else:
                failed += 1
        return {"sent": sent, "failed": failed}

    # Option 2: ntfy.sh (free phone push notifications)
    ntfy_topic = os.environ.get("CLARITY_NTFY_TOPIC")
    if ntfy_topic:
        for pattern in high_patterns:
            message = _format_message(pattern)
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"https://ntfy.sh/{ntfy_topic}",
                        content=message.encode("utf-8"),  # explicit UTF-8, not ASCII
                        headers={
                            "Title": "Clarity: Pattern Detected",
                            "Priority": "high" if pattern.get("severity") == "HIGH" else "default",
                            "Tags": f"warning,{pattern.get('type', 'pattern')}",
                        },
                    )
                    response.raise_for_status()
                    sent += 1
                    log.info("ntfy_alert_sent", topic=ntfy_topic, pattern_type=pattern.get("type"))
            except Exception as e:
                log.error("ntfy_alert_failed", error=str(e))
                failed += 1
        return {"sent": sent, "failed": failed}

    # Fallback: write to pending alerts file
    pending_path = Path(".clarity-cache/pending-alerts.json")
    existing = []
    if pending_path.exists():
        try:
            existing = json.loads(pending_path.read_text())
        except Exception:
            existing = []

    new_alerts = [
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "pattern": p,
            "message": _format_message(p),
            "delivered": False,
        }
        for p in high_patterns
    ]

    pending_path.write_text(json.dumps(existing + new_alerts, indent=2))
    log.info("alerts_queued_to_file", count=len(new_alerts))

    return {"sent": 0, "failed": 0, "queued": len(new_alerts)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/send-alert.py '<pattern_json>'")
        sys.exit(1)

    pattern = json.loads(sys.argv[1])
    result = asyncio.run(dispatch_alerts([pattern]))
    print(json.dumps(result, indent=2))