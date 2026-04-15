"""Dependency injection utilities for Digital Literacy Bridge."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import loguru

from config.database import get_db
from config.settings import get_dlb_settings
from database.models import User

logger = loguru.logger


async def get_dlb_settings_dep() -> DLBSettings:  # type: ignore[name-defined]
    """
    FastAPI dependency for DLB settings.

    Returns:
        DLBSettings: The application settings instance.
    """
    return get_dlb_settings()


async def get_current_user(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get or create the current user based on anonymous cookie.

    This implements a simple anonymous user model:
    1. Check for `dlb_anonymous_id` cookie
    2. If found, look up the user by that anonymous_id
    3. If not found or cookie absent, create a new anonymous user and set cookie
    4. Cookie is set via Set-Cookie header; client should persist it

    The cookie is httpOnly and could be secure in production.

    Args:
        request: FastAPI Request object to read cookies
        response: FastAPI Response object to set cookies
        db: Database session dependency

    Returns:
        User: The current user (anonymous or named)
    """
    settings = get_dlb_settings()
    cookie_name = "dlb_anonymous_id"
    cookie_max_age = 60 * 60 * 24 * 365  # 1 year

    anon_id = request.cookies.get(cookie_name)

    if anon_id:
        # Look up existing user by anonymous_id
        stmt = select(User).where(User.anonymous_id == anon_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"Found existing user: {user.id} (anon: {anon_id})")
            return user
        else:
            # Cookie exists but no user record (corrupted/deleted). Create new.
            logger.warning(f"Anonymous ID {anon_id} not found in DB, creating new user")

    # Create new anonymous user
    new_anon_id = str(uuid.uuid4())
    user = User(anonymous_id=new_anon_id)
    db.add(user)
    await db.flush()  # Generate ID without committing transaction

    # Mark cookie to be set in response
    response.set_cookie(
        key=cookie_name,
        value=new_anon_id,
        max_age=cookie_max_age,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
    )

    logger.info(f"Created new anonymous user: {user.id} with cookie: {new_anon_id}")
    return user


async def get_user_by_username(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """
    Look up a user by username (if they created one).

    Args:
        username: The username to look up
        db: Database session

    Returns:
        User or None if not found
    """
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


from config.settings import DLBSettings  # noqa: E402 - import after use to avoid circular
