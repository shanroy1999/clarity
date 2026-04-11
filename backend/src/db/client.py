"""
Supabase database client for Clarity.

Single source of truth for all database connections.
Never import supabase directly anywhere else — always use this module.
"""

import os
from functools import lru_cache

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_client() -> Client:
    """
    Returns a cached Supabase client instance.

    Uses lru_cache so the client is created once per process.
    Call get_client() anywhere in the backend — always returns
    the same instance.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment. "
            "Check your .env file."
        )

    return create_client(url, key)


async def save_weekly_snapshot(user_id: str, snapshot: dict) -> dict:
    """
    Persist a LifeLoadSnapshot to Supabase.

    Args:
        user_id: Clarity user UUID
        snapshot: Normalized snapshot dict from .clarity-cache/

    Returns:
        Inserted row from Supabase
    """
    client = get_client()

    row = {
        "user_id": user_id,
        "week_start": snapshot["week_start"],
        "total_meeting_hours": snapshot.get("total_meeting_hours"),
        "meetings_per_day": snapshot.get("meetings_per_day"),
        "back_to_back_count": snapshot.get("back_to_back_count"),
        "free_evening_count": snapshot.get("free_evening_count"),
        "longest_focus_block_hours": snapshot.get("longest_focus_block_hours"),
        "overload_days": snapshot.get("overload_days"),
        "total_emails_received": snapshot.get("total_emails_received"),
        "unread_count": snapshot.get("unread_count"),
        "late_night_sends": snapshot.get("late_night_sends"),
        "unanswered_threads": snapshot.get("unanswered_threads"),
        "total_tasks": snapshot.get("total_tasks"),
        "completion_rate": snapshot.get("completion_rate"),
        "tasks_by_category": snapshot.get("tasks_by_category"),
        "most_avoided_category": snapshot.get("most_avoided_category"),
        "zero_completion_days": snapshot.get("zero_completion_days"),
        "total_spend": snapshot.get("total_spend"),
        "spend_vs_budget_pct": snapshot.get("spend_vs_budget_pct"),
        "high_spend_categories": snapshot.get("high_spend_categories"),
    }

    result = client.table("weekly_snapshots").upsert(
        row,
        on_conflict="user_id,week_start"
    ).execute()

    return result.data[0] if result.data else {}


async def save_weekly_report(
    user_id: str,
    snapshot_id: str,
    week_start: str,
    report_markdown: str,
    report_json: dict,
    quality_score: str = "passed",
    pattern_count: int = 0,
) -> dict:
    """
    Persist a weekly report to Supabase.
    """
    client = get_client()
    word_count = len(report_markdown.split())

    row = {
        "user_id": user_id,
        "snapshot_id": snapshot_id,
        "week_start": week_start,
        "report_markdown": report_markdown,
        "report_json": report_json,
        "word_count": word_count,
        "quality_score": quality_score,
        "pattern_count": pattern_count,
    }

    result = client.table("weekly_reports").upsert(
        row,
        on_conflict="user_id,week_start"
    ).execute()

    return result.data[0] if result.data else {}


async def save_pattern_signals(
    user_id: str,
    snapshot_id: str,
    patterns: list[dict],
) -> list[dict]:
    """
    Persist detected pattern signals to Supabase.
    """
    client = get_client()

    rows = [
        {
            "user_id": user_id,
            "snapshot_id": snapshot_id,
            "pattern_type": p["type"],
            "severity": p["severity"],
            "evidence": p.get("evidence", []),
            "days_affected": p.get("days_affected", []),
            "historical_frequency": p.get("historical_frequency", 0),
            "weeks_consecutive": p.get("weeks_consecutive", 1),
        }
        for p in patterns
    ]

    if not rows:
        return []

    result = client.table("pattern_signals").insert(rows).execute()
    return result.data or []