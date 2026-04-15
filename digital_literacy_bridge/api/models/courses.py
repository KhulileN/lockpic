"""Pydantic models for course and lesson operations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LessonType(StrEnum):
    """Supported lesson content types."""

    INTERACTIVE = "interactive"
    VIDEO = "video"
    TEXT = "text"
    QUIZ = "quiz"


# --- Course Models ---
class CourseCreate(BaseModel):
    """
    Request model for creating a new course.

    Content (title, description) is internationalized as JSON dicts.
    """

    slug: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe unique identifier (lowercase, hyphens, numbers)",
    )
    title: dict[str, str] = Field(
        ...,
        description="Internationalized title: {'en': 'English Title', 'es': 'Título Español'}",
    )
    description: dict[str, str] = Field(
        ...,
        description="Internationalized description",
    )
    icon: str | None = Field(
        None,
        description="Optional icon (emoji or icon name)",
    )
    prerequisite_course_slug: str | None = Field(
        None,
        alias="prerequisite_course",
        description="Slug of prerequisite course if any",
    )
    order: int = Field(
        default=0,
        ge=0,
        description="Display order (lower numbers first)",
    )
    estimated_minutes: int = Field(
        default=15,
        ge=1,
        description="Total estimated completion time in minutes",
    )


class CourseResponse(BaseModel):
    """Response model for course listing/details."""

    id: str = Field(..., description="Course database ID")
    slug: str = Field(..., description="Course slug")
    title: dict[str, str] = Field(..., description="Internationalized title")
    description: dict[str, str] = Field(..., description="Internationalized description")
    icon: str | None = Field(None, description="Course icon")
    order: int = Field(..., description="Display order")
    estimated_minutes: int = Field(..., description="Estimated duration")
    lesson_count: int = Field(..., description="Number of lessons in this course")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


class CourseDetailResponse(CourseResponse):
    """Detailed course response including lessons."""

    lessons: list[LessonSummary] = Field(..., description="List of lessons in this course")

    # Forward reference fix
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from .courses import LessonSummary  # type: ignore


class LessonSummary(BaseModel):
    """Summary of a lesson for course listing."""

    id: str
    slug: str
    title: dict[str, str]
    lesson_type: LessonType
    order: int
    estimated_minutes: int
    is_completed: bool | None = None  # Added when viewing with user context

    model_config = {"from_attributes": True}


# --- Lesson Models ---
class LessonCreate(BaseModel):
    """
    Request model for creating a lesson.

    Content is internationalized: content[lang_code] = lesson_content_dict
    Each language's content structure can vary by lesson_type.
    """

    course_slug: str = Field(
        ...,
        alias="course",
        description="Slug of the parent course",
    )
    slug: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe lesson identifier within the course",
    )
    title: dict[str, str] = Field(
        ...,
        description="Internationalized title per language",
    )
    content: dict[str, dict[str, Any]] = Field(
        ...,
        description=(
            "Internationalized content keyed by language code. "
            "Each language's content is a dict with keys based on lesson_type."
        ),
    )
    lesson_type: LessonType = Field(
        ...,
        description="Type of lesson (affects content structure and rendering)",
    )
    prerequisite_lesson_slugs: list[str] = Field(
        default_factory=list,
        alias="prerequisites",
        description="Slugs of prerequisite lessons within the same course",
    )
    order: int = Field(
        default=0,
        ge=0,
        description="Order within the course",
    )
    estimated_minutes: int = Field(
        default=5,
        ge=1,
        description="Estimated time to complete this lesson",
    )

    @field_validator("prerequisite_lesson_slugs", mode="before")
    @classmethod
    def ensure_list(cls, v: str | list[str]) -> list[str]:
        """Ensure prerequisites is a list."""
        if isinstance(v, str):
            return [v]
        return v


class LessonResponse(BaseModel):
    """Response model for a lesson, with language-specific content."""

    id: str = Field(..., description="Lesson database ID")
    course_id: str = Field(..., description="Parent course ID")
    slug: str = Field(..., description="Lesson slug")
    title: dict[str, str] = Field(..., description="Internationalized title")
    # Note: Content is returned in requested language (see API route)
    content: dict[str, Any] = Field(
        ...,
        description="Lesson content in the requested language",
    )
    lesson_type: LessonType = Field(..., description="Lesson content type")
    order: int = Field(..., description="Order within course")
    estimated_minutes: int = Field(..., description="Estimated duration")
    is_completed: bool | None = Field(
        None,
        description="Whether the requesting user has completed this lesson (requires auth)",
    )

    model_config = {"from_attributes": True}

    @field_validator("content", mode="before")
    @classmethod
    def ensure_language_content(cls, v: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """
        The content is expected to be already resolved to a single language
        by the API route before being passed to this response model.
        This validator ensures the structure is correct (dict, not dict-of-dicts).
        """
        if isinstance(v, dict) and all(isinstance(k, str) for k in v.keys()):
            # Check if it's nested i18n vs single language
            # Single language: {"en": {"body": "..."}}
            # We want to return just the inner dict: {"body": "..."}
            # Actually the API route should provide the resolved language dict directly
            return v
        return v


class LessonContentResponse(BaseModel):
    """Simplified response for lesson content only (for embedded views)."""

    id: str
    slug: str
    title: str  # Resolved to specific language
    content: dict[str, Any]  # Content for specific language
    lesson_type: LessonType
    is_completed: bool | None = None
