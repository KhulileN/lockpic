"""Pydantic models for user progress tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProgressUpdate(BaseModel):
    """
    Request model for updating lesson progress.

    Typically used to mark a lesson as in_progress or completed.
    """

    status: str = Field(
        ...,
        pattern=r"^(not_started|in_progress|completed)$",
        description="Progress status: one of not_started, in_progress, completed",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional data (quiz scores, time_spent_seconds, notes, etc.)",
    )


class UserProgressResponse(BaseModel):
    """Response model for a user's progress entry."""

    id: str = Field(..., description="Progress record ID")
    lesson_id: str = Field(..., description="Completed lesson ID")
    lesson_slug: str = Field(..., description="Lesson slug (denormalized for convenience)")
    lesson_title: dict[str, str] = Field(
        ...,
        description="Lesson title (internationalized, denormalized)",
    )
    course_slug: str = Field(..., description="Parent course slug (denormalized)")
    status: str = Field(..., description="Current status")
    started_at: datetime | None = Field(
        None,
        description="When user first started this lesson",
    )
    completed_at: datetime | None = Field(
        None,
        description="When user completed this lesson",
    )
    metadata: dict[str, Any] = Field(
        ...,
        description="Additional progress metadata",
    )

    model_config = ConfigDict(from_attributes=True)


class ProgressSummary(BaseModel):
    """Summary of user progress across a course."""

    course_id: str
    course_slug: str
    course_title: dict[str, str]
    total_lessons: int
    completed_lessons: int
    progress_percent: float = Field(..., ge=0, le=100)
    last_activity: datetime | None = None
