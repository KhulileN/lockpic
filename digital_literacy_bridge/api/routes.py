"""API routes for Digital Literacy Bridge."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.database import get_db
from config.settings import get_dlb_settings
from database.models import Course, Lesson, User, UserProgress
from api.models.auth import UserResponse
from api.models.courses import (
    CourseCreate,
    CourseResponse,
    CourseDetailResponse,
    LessonCreate,
    LessonResponse,
)
from api.models.progress import (
    ProgressUpdate,
    UserProgressResponse,
    ProgressSummary,
)
from utils.content_loader import ContentLoader

router = APIRouter(prefix="/api/v1", tags=["courses"])

# Re-export get_current_user for convenience (from dependencies module)
from api.dependencies import get_current_user, get_user_by_username  # noqa: E402

# --- Helper Functions ---
def resolve_localized_string(
    i18n_dict: dict[str, str] | None,
    preferred_lang: str,
    context: str = "field",
) -> str:
    """
    Resolve a localized string from an i18n dictionary.

    Args:
        i18n_dict: Dictionary mapping language codes to strings
        preferred_lang: The user's preferred language code (e.g., "en")
        context: Field name for error messages

    Returns:
        The best matching string, or empty string if none available
    """
    if not i18n_dict:
        return ""

    # Exact match
    if preferred_lang in i18n_dict:
        return i18n_dict[preferred_lang]

    # Base language fallback (e.g., "pt-BR" -> "pt")
    base_lang = preferred_lang.split("-")[0]
    if base_lang in i18n_dict:
        return i18n_dict[base_lang]

    # Default to first available entry
    first_key = next(iter(i18n_dict))
    return i18n_dict[first_key]


def resolve_localized_content(
    content_i18n: dict[str, dict[str, Any]] | None,
    preferred_lang: str,
) -> dict[str, Any]:
    """
    Resolve lesson content for a specific language.

    Args:
        content_i18n: Dict mapping language codes to content dicts
        preferred_lang: Requested language code

    Returns:
        The content dict for the best matching language
    """
    if not content_i18n:
        return {}

    if preferred_lang in content_i18n:
        return content_i18n[preferred_lang]

    base_lang = preferred_lang.split("-")[0]
    if base_lang in content_i18n:
        return content_i18n[base_lang]

    # Return any available language
    return next(iter(content_i18n.values()))


# --- Health Check ---
@router.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok", "service": "digital-literacy-bridge"}


# --- Courses ---
@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    language: str | None = Query(
        None,
        description="Preferred language for titles/descriptions (e.g., 'en', 'es')",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[CourseResponse]:
    """
    List all courses with basic information.

    Optionally localize title and description to the requested language.
    """
    stmt = select(Course).order_by(Course.order, Course.created_at)
    result = await db.execute(stmt)
    courses = result.scalars().all()

    # Get default language from settings if not specified
    settings = get_dlb_settings()
    lang = language or "en"

    response = []
    for course in courses:
        title = resolve_localized_string(course.title, lang)
        description = resolve_localized_string(course.description, lang)
        response.append(
            CourseResponse(
                id=course.id,
                slug=course.slug,
                title=course.title,  # Return full i18n dict for client
                description=course.description,
                icon=course.icon,
                order=course.order,
                estimated_minutes=course.estimated_minutes,
                lesson_count=len(course.lessons),
                created_at=course.created_at,
            )
        )

    return response


@router.get("/courses/{course_slug}", response_model=CourseDetailResponse)
async def get_course(
    course_slug: str,
    language: str | None = Query(
        None,
        description="Preferred language for titles/descriptions",
    ),
    db: AsyncSession = Depends(get_db),
) -> CourseDetailResponse:
    """
    Get course details including all lessons.

    Lessons are returned with minimal fields (no content body) - use
    GET /lessons/{lesson_id} to retrieve full lesson content.
    """
    # Load course with lessons using selectinload
    stmt = (
        select(Course)
        .options(selectinload(Course.lessons))
        .where(Course.slug == course_slug)
    )
    result = await db.execute(stmt)
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    settings = get_dlb_settings()
    lang = language or "en"

    # Build lesson summaries
    lesson_summaries = []
    for lesson in sorted(course.lessons, key=lambda l: l.order):
        title = resolve_localized_string(lesson.title, lang)
        lesson_summaries.append(
            {
                "id": lesson.id,
                "slug": lesson.slug,
                "title": lesson.title,  # Return full i18n dict
                "lesson_type": lesson.lesson_type,
                "order": lesson.order,
                "estimated_minutes": lesson.estimated_minutes,
                "is_completed": None,  # No user context in this endpoint
            }
        )

    return CourseDetailResponse(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        icon=course.icon,
        order=course.order,
        estimated_minutes=course.estimated_minutes,
        lesson_count=len(course.lessons),
        created_at=course.created_at,
        lessons=lesson_summaries,  # type: ignore[arg-type]
    )


@router.post("/courses", response_model=CourseResponse, status_code=201)
async def create_course(
    course_data: CourseCreate,
    db: AsyncSession = Depends(get_db),
) -> CourseResponse:
    """
    Create a new course.

    This endpoint is primarily for content administration/seed scripts.
    In production, consider protecting this with authentication.
    """
    # Check for slug conflict
    existing = await db.execute(select(Course).where(Course.slug == course_data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Course with slug '{course_data.slug}' already exists")

    course = Course(
        slug=course_data.slug,
        title=course_data.title,
        description=course_data.description,
        icon=course_data.icon,
        prerequisite_course_id=None,  # Will be set later if needed
        order=course_data.order,
        estimated_minutes=course_data.estimated_minutes,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    return CourseResponse(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        icon=course.icon,
        order=course.order,
        estimated_minutes=course.estimated_minutes,
        lesson_count=0,
        created_at=course.created_at,
    )


# --- Lessons ---
@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: str,
    language: str | None = Query(
        None,
        description="Preferred language for title and content",
    ),
    user: Annotated[User, Depends(get_current_user)] = None,  # type: ignore
    db: AsyncSession = Depends(get_db),
) -> LessonResponse:
    """
    Get a specific lesson's full content.

    If the user is authenticated (via anonymous cookie), their progress
    for this lesson is included (is_completed flag).
    """
    # Load lesson with course for prerequisite check (if needed)
    stmt = (
        select(Lesson)
        .options(selectinload(Lesson.course))
        .where(Lesson.id == lesson_id)
    )
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get user's progress for this lesson if user provided
    is_completed = False
    if user:
        prog_stmt = select(UserProgress).where(
            UserProgress.user_id == user.id,
            UserProgress.lesson_id == lesson.id,
        )
        prog_result = await db.execute(prog_stmt)
        progress = prog_result.scalar_one_or_none()
        if progress:
            is_completed = progress.status == "completed"

    # Resolve language
    settings = get_dlb_settings()
    lang = language or user.preferred_language if user else (language or "en")

    # Get content in requested language
    content = resolve_localized_content(lesson.content, lang)
    title = resolve_localized_string(lesson.title, lang)

    return LessonResponse(
        id=lesson.id,
        course_id=lesson.course_id,
        slug=lesson.slug,
        title=lesson.title,  # Full i18n dict
        content=content,
        lesson_type=lesson.lesson_type,
        order=lesson.order,
        estimated_minutes=lesson.estimated_minutes,
        is_completed=is_completed,
    )


@router.post("/lessons", response_model=LessonResponse, status_code=201)
async def create_lesson(
    lesson_data: LessonCreate,
    db: AsyncSession = Depends(get_db),
) -> LessonResponse:
    """
    Create a new lesson within a course.

    The course_slug is required; the course must exist.
    """
    # Look up course
    course_stmt = select(Course).where(Course.slug == lesson_data.course_slug)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(
            status_code=404,
            detail=f"Course with slug '{lesson_data.course_slug}' not found",
        )

    # Check for slug conflict within course
    existing = await db.execute(
        select(Lesson).where(
            Lesson.course_id == course.id,
            Lesson.slug == lesson_data.slug,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Lesson with slug '{lesson_data.slug}' already exists in this course",
        )

    # Validate prerequisite lesson slugs exist within this course
    if lesson_data.prerequisite_lesson_slugs:
        prereq_stmt = select(Lesson.id).where(
            Lesson.course_id == course.id,
            Lesson.slug.in_(lesson_data.prerequisite_lesson_slugs),
        )
        prereq_result = await db.execute(prereq_stmt)
        found_ids = [row[0] for row in prereq_result.all()]
        missing = set(lesson_data.prerequisite_lesson_slugs) - {
            # We'd need to query slugs, but simpler: check count matches
        }
        # For simplicity, skip full validation here; could be added

    lesson = Lesson(
        course_id=course.id,
        slug=lesson_data.slug,
        title=lesson_data.title,
        content=lesson_data.content,
        lesson_type=lesson_data.lesson_type,
        prerequisite_lesson_ids=[],  # Filled later with actual IDs if needed
        order=lesson_data.order,
        estimated_minutes=lesson_data.estimated_minutes,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)

    # Return minimal response (no content body since that's language-specific)
    return LessonResponse(
        id=lesson.id,
        course_id=lesson.course_id,
        slug=lesson.slug,
        title=lesson.title,
        content={},  # Empty - client should fetch with language query
        lesson_type=lesson.lesson_type,
        order=lesson.order,
        estimated_minutes=lesson.estimated_minutes,
        is_completed=False,
    )


# --- Progress ---
@router.get("/progress/me", response_model=list[UserProgressResponse])
async def get_my_progress(
    user: Annotated[User, Depends(get_current_user)] = None,  # type: ignore
    db: AsyncSession = Depends(get_db),
) -> list[UserProgressResponse]:
    """
    Retrieve all progress entries for the current user.

    Entries are ordered by course order then lesson order.
    Each entry includes the lesson's title (i18n) and course slug.
    """
    if not user:
        # Should not happen with get_current_user, but just in case
        return []

    stmt = (
        select(UserProgress, Lesson, Course)
        .join(Lesson, UserProgress.lesson_id == Lesson.id)
        .join(Course, Lesson.course_id == Course.id)
        .where(UserProgress.user_id == user.id)
        .order_by(Course.order, Lesson.order)
    )
    result = await db.execute(stmt)
    rows = result.all()

    responses = []
    for progress, lesson, course in rows:
        responses.append(
            UserProgressResponse(
                id=progress.id,
                lesson_id=lesson.id,
                lesson_slug=lesson.slug,
                lesson_title=lesson.title,
                course_slug=course.slug,
                status=progress.status,
                started_at=progress.started_at,
                completed_at=progress.completed_at,
                metadata=progress.metadata or {},
            )
        )

    return responses


@router.post("/progress/lessons/{lesson_id}", response_model=UserProgressResponse)
async def update_lesson_progress(
    lesson_id: str,
    update_data: ProgressUpdate,
    user: Annotated[User, Depends(get_current_user)] = None,  # type: ignore
    db: AsyncSession = Depends(get_db),
) -> UserProgressResponse:
    """
    Update progress for a specific lesson.

    Creates a new progress record if none exists, or updates existing.
    Automatically sets started_at/completed_at based on status.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify lesson exists
    lesson_stmt = select(Lesson).where(Lesson.id == lesson_id)
    lesson_result = await db.execute(lesson_stmt)
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Find existing progress
    prog_stmt = select(UserProgress).where(
        UserProgress.user_id == user.id,
        UserProgress.lesson_id == lesson_id,
    )
    prog_result = await db.execute(prog_stmt)
    progress = prog_result.scalar_one_or_none()

    now = datetime.utcnow()
    status = update_data.status

    if progress:
        # Update existing
        progress.status = status
        progress.metadata = {**progress.metadata, **update_data.metadata}
        if status == "in_progress" and not progress.started_at:
            progress.started_at = now
        if status == "completed" and not progress.completed_at:
            progress.completed_at = now
        progress.updated_at = now
    else:
        # Create new
        progress = UserProgress(
            user_id=user.id,
            lesson_id=lesson_id,
            status=status,
            started_at=now if status == "in_progress" else None,
            completed_at=now if status == "completed" else None,
            metadata=update_data.metadata,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)

    # Fetch course for response
    course_stmt = select(Course).join(Lesson).where(Lesson.id == lesson_id)
    course_result = await db.execute(course_stmt)
    course = course_result.scalar_one()

    return UserProgressResponse(
        id=progress.id,
        lesson_id=lesson.id,
        lesson_slug=lesson.slug,
        lesson_title=lesson.title,
        course_slug=course.slug,
        status=progress.status,
        started_at=progress.started_at,
        completed_at=progress.completed_at,
        metadata=progress.metadata or {},
    )


# --- Course Catalog / Content Loader Integration ---
@router.get("/content/courses")
async def list_available_content_courses(
    language: str | None = Query(None, description="Filter courses by language availability"),
) -> list[dict[str, Any]]:
    """
    List courses available from YAML content files.

    This endpoint reads from the content/ directory and returns course metadata
    without requiring database setup. Useful for verifying content structure.

    The response format mirrors CourseResponse but is read from YAML files.
    """
    loader = ContentLoader()
    courses = []
    for slug in loader.list_courses():
        try:
            course_data = loader.load_course(slug)
            # Extract basic metadata
            title = course_data.get("title", {})
            description = course_data.get("description", {})
            lessons = course_data.get("lessons", [])
            lang = language or "en"
            title_localized = resolve_localized_string(title, lang)
            desc_localized = resolve_localized_string(description, lang)
            courses.append(
                {
                    "slug": slug,
                    "title": title,
                    "title_localized": title_localized,
                    "description": description,
                    "description_localized": desc_localized,
                    "icon": course_data.get("icon"),
                    "order": course_data.get("order", 0),
                    "estimated_minutes": course_data.get("estimated_minutes", len(lessons) * 10),
                    "lesson_count": len(lessons),
                }
            )
        except Exception as e:
            logger.error(f"Failed to load course {slug}: {e}")
            continue

    return sorted(courses, key=lambda c: c["order"])
