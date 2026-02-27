"""Security utilities — authentication and authorization placeholders.

This module provides dependency stubs that will be replaced by a full
JWT / OAuth2 implementation in a future iteration.  Every endpoint that
needs authentication should depend on ``get_current_user`` so the swap
is seamless.
"""

from uuid import UUID, uuid4

from fastapi import Depends, Request

from app.core.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Hard-coded demo user returned until real auth is wired up
# ---------------------------------------------------------------------------
DEMO_USER_ID: UUID = UUID("00000000-0000-4000-a000-000000000001")


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> UUID:
    """Return the authenticated user's UUID.

    Currently returns a deterministic demo ID.  When real auth is
    implemented this will decode a JWT from the ``Authorization`` header
    and resolve the user id.

    Args:
        request: The incoming HTTP request.
        settings: Application settings (injected).

    Returns:
        The UUID of the authenticated user.
    """
    # Future: extract and verify JWT from request.headers["Authorization"]
    return DEMO_USER_ID
