"""Pydantic models for authentication and user-related requests/responses."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """
    Request model for creating/registering a user.

    Username is optional - users can remain anonymous.
    """

    username: str | None = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional username for identification (alphanumeric, underscore, hyphen)",
    )
    preferred_language: str = Field(
        default="en",
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="Preferred language code, e.g., 'en', 'es', 'pt-BR'",
    )


class UserResponse(BaseModel):
    """Response model for user data (non-sensitive)."""

    id: str = Field(..., description="User's database ID (UUID)")
    anonymous_id: str | None = Field(
        None,
        description="Anonymous identifier stored in browser cookie",
    )
    username: str | None = Field(
        None,
        description="Chosen username, if set",
    )
    preferred_language: str = Field(
        ...,
        description="User's selected language",
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
    )

    model_config = {
        "from_attributes": True,  # Allow creating from ORM model
    }
