"""
OAuth token refresh for Clarity.

Manages Google (Calendar + Gmail) and Todoist OAuth tokens.
Tokens are stored in Supabase Vault — never in environment variables
or the database directly.

Called by:
- SessionStart hook before MCP connections are established
- Any MCP tool call that returns a 401
- Scheduled refresh (every 50 minutes, tokens expire at 60)
"""

import os
import time
import httpx
import structlog
from datetime import datetime, timezone, timedelta
from typing import Literal

from backend.src.db.client import get_client

log = structlog.get_logger()

Provider = Literal["google", "todoist"]

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
TODOIST_TOKEN_URL = "https://todoist.com/oauth/access_token"

# Refresh 10 minutes before expiry to avoid mid-session failures
REFRESH_BUFFER_SECONDS = 600


# ---------------------------------------------------------------------------
# Vault helpers
# ---------------------------------------------------------------------------

async def _get_token_from_vault(user_id: str, provider: Provider) -> dict | None:
    """
    Read OAuth token data from Supabase Vault.

    Returns dict with keys: access_token, refresh_token, expires_at
    Returns None if no token found.
    """
    client = get_client()
    try:
        result = (
            client.table("user_oauth_tokens")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def _save_token_to_vault(
    user_id: str,
    provider: Provider,
    access_token: str,
    refresh_token: str | None,
    expires_in: int,
) -> None:
    """
    Persist refreshed token data to Supabase.

    expires_at is stored as ISO timestamp so session-start hook
    can check expiry without making an API call.
    """
    client = get_client()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    row = {
        "user_id": user_id,
        "provider": provider,
        "access_token": access_token,
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Only update refresh_token if a new one was issued
    # Google sometimes omits it on refresh — keep the existing one
    if refresh_token:
        row["refresh_token"] = refresh_token

    client.table("user_oauth_tokens").upsert(
        row,
        on_conflict="user_id,provider",
    ).execute()

    log.info("token_saved", user_id=user_id, provider=provider, expires_at=expires_at)


# ---------------------------------------------------------------------------
# Expiry check
# ---------------------------------------------------------------------------

def _is_expiring_soon(expires_at: str | None) -> bool:
    """
    Returns True if the token expires within REFRESH_BUFFER_SECONDS.
    Returns True if expires_at is missing (treat as expired).
    """
    if not expires_at:
        return True

    try:
        expiry = datetime.fromisoformat(expires_at)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        remaining = (expiry - datetime.now(timezone.utc)).total_seconds()
        return remaining < REFRESH_BUFFER_SECONDS
    except ValueError:
        return True


# ---------------------------------------------------------------------------
# Provider-specific refresh
# ---------------------------------------------------------------------------

async def _refresh_google_token(refresh_token: str) -> dict:
    """
    Exchange a Google refresh token for a new access token.

    Returns: {access_token, expires_in, refresh_token (maybe)}
    Raises: httpx.HTTPStatusError on failure
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise EnvironmentError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"
        )

    async with httpx.AsyncClient() as http:
        response = await http.post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

# Todoist uses a static API token — no refresh flow exists.
# Token is set once in .env as TODOIST_API_TOKEN and never rotates
# unless the user regenerates it manually in Todoist settings.
# _refresh_todoist_token intentionally not implemented

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def ensure_fresh_token(user_id: str, provider: Provider) -> str:
    """
    Returns a valid access token for the given provider.

    Google: refreshes automatically when expiring soon.
    Todoist: returns static token from Vault — no refresh needed.

    Args:
        user_id: Clarity user UUID
        provider: "google" or "todoist"

    Returns:
        Valid access token string

    Raises:
        RuntimeError: No token found — user must authorize
        httpx.HTTPStatusError: Google refresh request failed
    """
    token_data = await _get_token_from_vault(user_id, provider)

    if not token_data:
        raise RuntimeError(
            f"No {provider} token for user {user_id}. "
            f"User must complete authorization."
        )

    # Todoist: static token, never expires — return immediately
    if provider == "todoist":
        log.debug("todoist_token_static", user_id=user_id)
        return token_data["access_token"]

    # Google: check expiry and refresh if needed
    if not _is_expiring_soon(token_data.get("expires_at")):
        log.debug("token_fresh", user_id=user_id, provider=provider)
        return token_data["access_token"]

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise RuntimeError(
            f"Google token for user {user_id} is expired and has no "
            f"refresh token. User must re-authorize."
        )

    log.info("token_refreshing", user_id=user_id, provider=provider)

    new_tokens = await _refresh_google_token(refresh_token)

    await _save_token_to_vault(
        user_id=user_id,
        provider=provider,
        access_token=new_tokens["access_token"],
        refresh_token=new_tokens.get("refresh_token"),
        expires_in=new_tokens.get("expires_in", 3600),
    )

    log.info("token_refreshed", user_id=user_id, provider=provider)
    return new_tokens["access_token"]


async def check_all_tokens(user_id: str) -> dict[str, str]:
    """
    Check token status for all providers without refreshing.

    Google: checks expiry against expires_at timestamp.
    Todoist: reports "static" — token never expires automatically.

    Returns dict: {provider: "fresh" | "expiring" | "expired" | "missing" | "static"}
    """
    providers: list[Provider] = ["google", "todoist"]
    status: dict[str, str] = {}

    for provider in providers:
        token_data = await _get_token_from_vault(user_id, provider)

        if not token_data:
            status[provider] = "missing"
            continue

        # Todoist uses a static token — no expiry to check
        if provider == "todoist":
            status[provider] = "static"
            continue

        expires_at = token_data.get("expires_at")
        if not expires_at:
            status[provider] = "expired"
            continue

        try:
            expiry = datetime.fromisoformat(expires_at)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            remaining = (expiry - datetime.now(timezone.utc)).total_seconds()

            if remaining < 0:
                status[provider] = "expired"
            elif remaining < REFRESH_BUFFER_SECONDS:
                status[provider] = "expiring"
            else:
                status[provider] = "fresh"
        except ValueError:
            status[provider] = "expired"

    return status
