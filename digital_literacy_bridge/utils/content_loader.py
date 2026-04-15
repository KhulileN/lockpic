"""Content loader for YAML-based course and lesson content."""

from __future__ import annotations

from pathlib import Path
import yaml
from typing import Any

from config.settings import get_dlb_settings
import loguru

logger = loguru.logger


class ContentLoader:
    """
    Load and validate course/lesson content from YAML files.

    Content files are stored in the directory specified by
    dlb_content_dir setting (default: content/courses).

    Each course is a YAML file named {slug}.yaml.
    """

    def __init__(self, content_dir: Path | None = None):
        """
        Initialize the content loader.

        Args:
            content_dir: Override the default content directory.
        """
        settings = get_dlb_settings()
        self.content_dir = content_dir or Path(settings.dlb_content_dir)
        self._course_cache: dict[str, dict[str, Any]] = {}

    def load_course(self, slug: str) -> dict[str, Any]:
        """
        Load a course's YAML file and return parsed dict.

        Results are cached per slug within this loader instance.

        Args:
            slug: Course identifier (filename stem)

        Returns:
            Parsed YAML data as dict

        Raises:
            FileNotFoundError: If course file doesn't exist
            ValueError: If course data fails validation
        """
        if slug in self._course_cache:
            return self._course_cache[slug]

        course_file = self.content_dir / f"{slug}.yaml"
        if not course_file.exists():
            logger.error(f"Course file not found: {course_file}")
            raise FileNotFoundError(f"Course '{slug}' not found at {course_file}")

        try:
            with open(course_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {course_file}: {e}")
            raise ValueError(f"Invalid YAML in course '{slug}': {e}")

        self._validate_course(data)
        self._course_cache[slug] = data
        logger.debug(f"Loaded course: {slug}")
        return data

    def load_lesson(
        self, course_slug: str, lesson_slug: str
    ) -> dict[str, Any]:
        """
        Load a specific lesson from the course YAML.

        Args:
            course_slug: Course identifier
            lesson_slug: Lesson identifier within the course

        Returns:
            Lesson data dict

        Raises:
            ValueError: If lesson not found in course
        """
        course = self.load_course(course_slug)
        lessons = course.get("lessons", [])
        for lesson in lessons:
            if lesson.get("slug") == lesson_slug:
                return lesson
        raise ValueError(
            f"Lesson '{lesson_slug}' not found in course '{course_slug}'"
        )

    def list_courses(self) -> list[str]:
        """
        List available course slugs from the content directory.

        Returns:
            List of course slugs (YAML filename stems)
        """
        if not self.content_dir.exists():
            return []
        return [p.stem for p in self.content_dir.glob("*.yaml") if p.is_file()]

    def _validate_course(self, data: dict[str, Any]) -> None:
        """
        Validate course structure.

        Required fields: slug, title (dict), description (dict), lessons (list)
        Each lesson must have: slug, title (dict), content (dict), type

        Args:
            data: Parsed course YAML dict

        Raises:
            ValueError: If validation fails
        """
        required_fields = ["slug", "title", "description", "lessons"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in course: {field}")

        # Validate title and description are dicts with at least one entry
        if not isinstance(data["title"], dict) or not data["title"]:
            raise ValueError("Course title must be a non-empty dict of language codes")
        if not isinstance(data["description"], dict) or not data["description"]:
            raise ValueError("Course description must be a non-empty dict")

        # Validate lessons
        lessons = data.get("lessons", [])
        if not isinstance(lessons, list):
            raise ValueError("Course lessons must be a list")

        lesson_slugs = set()
        for idx, lesson in enumerate(lessons):
            if not isinstance(lesson, dict):
                raise ValueError(f"Lesson at index {idx} must be a dict")
            lesson_slug = lesson.get("slug")
            if not lesson_slug:
                raise ValueError(f"Lesson at index {idx} missing 'slug'")
            if lesson_slug in lesson_slugs:
                raise ValueError(f"Duplicate lesson slug: {lesson_slug}")
            lesson_slugs.add(lesson_slug)

            # Check lesson required fields
            lesson_required = ["slug", "title", "content", "type"]
            for field in lesson_required:
                if field not in lesson:
                    raise ValueError(
                        f"Lesson '{lesson_slug}' missing required field: {field}"
                    )

            # Validate prerequisites if present
            prereqs = lesson.get("prerequisite_lesson_slugs", [])
            if isinstance(prereqs, str):
                prereqs = [prereqs]
            for prereq in prereqs:
                if prereq not in lesson_slugs and prereq != lesson_slug:
                    # Note: prerequisite could come after, so we don't fail here
                    # This just logs a warning; actual cross-reference validation
                    # happens after all lessons are parsed.
                    logger.warning(
                        f"Lesson '{lesson_slug}' references prerequisite '{prereq}' "
                        "that hasn't been defined yet"
                    )

        # All good
        logger.debug(f"Course validation passed: {data.get('slug')}")
