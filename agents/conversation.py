"""
Clarity conversation agent.

Answers follow-up questions about a weekly report.
Anchors every answer in the actual data from the snapshot and patterns.
Maintains conversation history within a session.

Called from the FastAPI backend when a user sends a message
in the conversation UI after reading their report.
"""

import json
import os
from pathlib import Path

import structlog
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
log = structlog.get_logger()

CACHE_DIR = Path(".clarity-cache")

SYSTEM_PROMPT = """
You are the conversation agent for Clarity.

The user has just read their weekly life load report. They are asking
follow-up questions. Your job is to explain, elaborate, and connect —
always using the actual data from their snapshot, patterns, and report.

Rules:
- Every answer must cite specific data from the provided context
- If the user asks why they feel a certain way, connect it to a pattern
- Never speculate beyond what the data shows
- Never suggest solutions unless they are obvious from the pattern itself
- Keep responses under 150 words — this is a conversation, not a report
- If the user asks something the data cannot answer, say so directly

You have access to:
- Their weekly snapshot (calendar, email, task, financial signals)
- The detected patterns with evidence
- The load analysis
- The full weekly report text
""".strip()


def _load_context() -> str:
    """
    Load all available cache files into a single context string.
    Returns empty string if nothing found.
    """
    context_parts = []

    for prefix in ("snapshot", "patterns", "load", "report"):
        files = sorted(CACHE_DIR.glob(f"{prefix}-*.json"), reverse=True)
        if files:
            try:
                data = json.loads(files[0].read_text())
                context_parts.append(
                    f"## {prefix.title()}\n{json.dumps(data, indent=2)}"
                )
            except Exception:
                continue

    return "\n\n".join(context_parts)


async def respond(
    user_message: str,
    conversation_history: list[dict],
    user_id: str,
) -> tuple[str, list[dict]]:
    """
    Generate a response to a user message.

    Args:
        user_message: What the user just said
        conversation_history: Full prior conversation as list of
                              {"role": "user"|"assistant", "content": str}
        user_id: Clarity user UUID (for logging)

    Returns:
        (response_text, updated_conversation_history)
    """
    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    context = _load_context()
    if not context:
        return (
            "I don't have your weekly data loaded yet. "
            "Run /analyze-week first to generate a report.",
            conversation_history,
        )

    # Build full system prompt with context
    system = f"{SYSTEM_PROMPT}\n\n## Your data this week\n\n{context}"

    # Append the new user message
    updated_history = conversation_history + [
        {"role": "user", "content": user_message}
    ]

    log.info(
        "conversation_turn",
        user_id=user_id,
        turn=len(updated_history),
        message_preview=user_message[:50],
    )

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system,
        messages=updated_history,
    )

    response_text = response.content[0].text

    # Add assistant response to history
    updated_history = updated_history + [
        {"role": "assistant", "content": response_text}
    ]

    log.info(
        "conversation_response",
        user_id=user_id,
        tokens=response.usage.output_tokens,
        response_preview=response_text[:50],
    )

    return response_text, updated_history