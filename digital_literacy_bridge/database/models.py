"""SQLAlchemy ORM models for Digital Literacy Bridge."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    JSON,
    Boolean,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from config.database import Base

if TYPE_CHECKING:
    from sqlalchemy.sql import Selectable


def generate_uuid() -> str:
    """Generate a UUID string for primary keys."""
    return str(uuid.uuid4())


# --- Association Tables ---
# (Could be used later for course<->language many-to-many)
# course_languages = Table(
#     "course_languages",
#     Base.metadata,
#     Column("course_id", String(36), ForeignKey("courses.id"), primary_key=True),
#     Column("language_code", String(5), primary_key=True),
# )


# --- Models ---
class Course(Base):
    """A collection of lessons teaching a specific skill."""

    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        doc="URL-friendly unique identifier",
    )
    title: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        doc="Internationalized title as dict: {lang_code: title}",
    )
    description: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        doc="Internationalized description as dict",
    )
    icon: Mapped[str | None] = mapped_column(
        String(50),
        doc="Optional icon identifier (emoji or icon name)",
    )
    prerequisite_course_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="SET NULL"),
        doc="ID of prerequisite course if any",
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Display order (lower numbers first)",
    )
    estimated_minutes: Mapped[int] = mapped_column(
        Integer,
        default=15,
        doc="Estimated time to complete the entire course",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        doc="Last update timestamp",
    )

    # Relationships
    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Lesson.order",
    )
    prerequisite_course: Mapped[Course | None] = relationship(
        remote_side=[id],
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id!r}, slug={self.slug!r})>"


class Lesson(Base):
    """Individual lesson within a course."""

    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        doc="Parent course ID",
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="URL-friendly lesson identifier within course",
    )
    title: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        doc="Internationalized title: {lang_code: title}",
    )
    content: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        doc="Lesson content structured by language and type",
    )
    lesson_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Type of lesson: text, video, interactive, quiz",
    )
    prerequisite_lesson_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        doc="List of prerequisite lesson IDs",
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Order within the course",
    )
    requires_authentication: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="Whether user must be authenticated to view",
    )
    estimated_minutes: Mapped[int] = mapped_column(
        Integer,
        default=5,
        doc="Estimated time to complete this lesson",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    # Relationships
    course: Mapped[Course] = relationship(back_populates="lessons")
    progress_entries: Mapped[list[UserProgress]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )

    # Composite unique constraint: slug unique within a course
    __table_args__ = (
        UniqueConstraint("course_id", "slug", name="uq_lesson_slug_per_course"),
    )

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id!r}, slug={self.slug!r}, course_id={self.course_id!r})>"


class User(Base):
    """Minimal user profile (anonymous or optionally identified)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    anonymous_id: Mapped[str | None] = mapped_column(
        String(36),
        unique=True,
        doc="Anonymous identifier stored in browser cookie",
    )
    username: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        doc="Optional chosen username (for sharing progress)",
    )
    preferred_language: Mapped[str] = mapped_column(
        String(5),
        default="en",
        doc="Preferred language code (e.g., 'en', 'es', 'fr-CA')",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    progress_entries: Mapped[list[UserProgress]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        identifier = self.username or self.anonymous_id or self.id
        return f"<User(id={self.id!r}, identifier={identifier!r})>"


class UserProgress(Base):
    """Track user progress through lessons."""

    __tablename__ = "user_progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    lesson_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="not_started",
        doc="Progress status: not_started, in_progress, completed",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        doc="When the lesson was first started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        doc="When the lesson was completed",
    )
    metadata: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        doc="Additional data like quiz scores, time spent, etc.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="progress_entries")
    lesson: Mapped[Lesson] = relationship(back_populates="progress_entries")

    # Composite unique constraint: one progress record per user per lesson
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),
    )

    def __repr__(self) -> str:
        return f"<UserProgress(user_id={self.user_id!r}, lesson_id={self.lesson_id!r}, status={self.status!r})>"
