"""Workspace authentication and LLM rate limiting.

There are no user accounts. A visitor creates a workspace and receives a random bearer token (shown once,
kept in the browser). Only a SHA-256 hash of the token is stored. Every request is resolved to a workspace
from that token, and every query is scoped to it, so documents are private to whoever holds the token.
Trade-off: no password recovery, and clearing the browser loses access. That fits an anonymous demo; real
accounts (OAuth) would slot in by mapping a user to a workspace.
"""

import hashlib
import hmac
import secrets

from fastapi import Depends, Header

from app.config import Settings
from app.db import Database, new_id, now
from app.deps import get_db, get_settings_dep
from app.errors import AppError


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_workspace(db: Database) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    ws_id = new_id()
    with db.tx() as c:
        c.execute("INSERT INTO workspaces (id, token_hash, created_at) VALUES (?, ?, ?)", (ws_id, _hash(token), now()))
    return ws_id, token


def current_workspace(authorization: str | None = Header(default=None), db: Database = Depends(get_db)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("Missing workspace token.", 401, "UNAUTHORIZED")
    token = authorization[7:].strip()
    row = db.one("SELECT id, token_hash FROM workspaces WHERE token_hash = ?", (_hash(token),))
    if not row or not hmac.compare_digest(row["token_hash"], _hash(token)):
        raise AppError("This workspace doesn't exist or the token is wrong.", 401, "UNAUTHORIZED")
    return row["id"]


def charge_llm_call(
    ws_id: str = Depends(current_workspace), db: Database = Depends(get_db), settings: Settings = Depends(get_settings_dep)
) -> str:
    """Sliding one-hour window per workspace; protects the shared API key from runaway use. Returns the workspace id."""
    window_start = now() - 3600
    with db.tx() as c:
        c.execute("DELETE FROM usage_events WHERE at < ?", (window_start - 86400,))
        used = c.execute("SELECT COUNT(*) FROM usage_events WHERE workspace_id = ? AND at >= ?", (ws_id, window_start)).fetchone()[0]
        if used >= settings.llm_calls_per_hour:
            raise AppError("You've reached this demo's hourly AI limit. Please try again later.", 429, "RATE_LIMITED")
        c.execute("INSERT INTO usage_events (workspace_id, at) VALUES (?, ?)", (ws_id, now()))
    return ws_id
