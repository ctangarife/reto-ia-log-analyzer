"""
Lesson Edit Service
Manages granular editing of lesson content with change tracking
"""
import logging
import json
import difflib
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from config.database import db_manager

logger = logging.getLogger(__name__)


class LessonEditService:
    """Service for editing lessons with granular control and change tracking"""

    # Maximum character change for minor edit (10% of content or 500 chars)
    MINOR_EDIT_MAX_CHANGE_RATIO = 0.1
    MINOR_EDIT_MAX_ABSOLUTE = 500

    async def update_lesson(
        self,
        lesson_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        exercise_data: Optional[dict] = None,
        is_minor_edit: bool = False,
        change_description: Optional[str] = None,
        changed_by: UUID = None
    ) -> dict:
        """
        Update a lesson with granular control.

        If is_minor_edit is True:
        - Course status remains unchanged
        - Only allows small content changes
        - Requires courses:minor_edit permission

        If is_minor_edit is False:
        - Course returns to DRAFT status
        - Requires re-approval
        """
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get current lesson and course info
                lesson = await conn.fetchrow("""
                    SELECT l.*, cm.id as course_id, cm.status as course_status,
                           cm.workspace_id, cm.project_id
                    FROM learning.course_lessons l
                    JOIN learning.course_modules cm ON cm.id = l.module_id
                    WHERE l.id = $1
                """, lesson_id)

                if not lesson:
                    raise ValueError("Lesson not found")

                # Dynamic lessons cannot be edited
                if lesson["is_dynamic"]:
                    return {
                        "status": "error",
                        "message": "Dynamic lessons cannot be edited. Their content is generated automatically."
                    }

                changes = []
                course_status_change = None

                # Handle title change
                if title is not None and title != lesson["title"]:
                    changes.append({
                        "field": "title",
                        "old": lesson["title"],
                        "new": title
                    })
                    await conn.execute(
                        "UPDATE learning.course_lessons SET title = $1 WHERE id = $2",
                        title, lesson_id
                    )

                    # Record change history
                    await self._record_change(
                        conn, lesson_id, changed_by, "title",
                        lesson["title"], title, is_minor_edit, change_description
                    )

                # Handle content change
                if content is not None and content != lesson["content"]:
                    content_change = len(content) - len(lesson["content"])

                    # Validate minor edit constraints
                    if is_minor_edit:
                        if not self._is_minor_change(lesson["content"], content):
                            return {
                                "status": "error",
                                "message": "Change is too large for a minor edit. Set is_minor_edit=false or make smaller changes."
                            }

                    changes.append({
                        "field": "content",
                        "old_length": len(lesson["content"]) if lesson["content"] else 0,
                        "new_length": len(content),
                        "change": content_change
                    })

                    await conn.execute(
                        "UPDATE learning.course_lessons SET content = $1 WHERE id = $2",
                        content, lesson_id
                    )

                    # Record change history
                    await self._record_change(
                        conn, lesson_id, changed_by, "content",
                        lesson["content"], content, is_minor_edit, change_description
                    )

                # Handle exercise data change
                if exercise_data is not None and exercise_data != lesson["exercise_data"]:
                    changes.append({
                        "field": "exercise_data"
                    })

                    await conn.execute(
                        "UPDATE learning.course_lessons SET exercise_data = $1 WHERE id = $2",
                        json.dumps(exercise_data), lesson_id  # Convert dict to JSON string
                    )

                    # Record change history
                    await self._record_change(
                        conn, lesson_id, changed_by, "exercise",
                        str(lesson["exercise_data"]), str(exercise_data), is_minor_edit, change_description
                    )

                # Handle course status
                if not is_minor_edit and changes:
                    # Course goes back to draft
                    await conn.execute(
                        """UPDATE learning.course_modules
                           SET status = 'draft', change_description = $1
                           WHERE id = $2""",
                        f"Lesson {lesson['lesson_order']} edited", lesson["course_id"]
                    )
                    course_status_change = "draft"

                return {
                    "status": "success",
                    "lesson_id": str(lesson_id),
                    "message": f"Lesson updated with {len(changes)} change(s)",
                    "changes": changes,
                    "course_status": course_status_change or lesson["course_status"],
                    "is_minor_edit": is_minor_edit
                }

        except Exception as e:
            logger.error(f"Error updating lesson: {e}")
            raise

    async def update_exercise(
        self,
        lesson_id: UUID,
        exercise_data: dict,
        change_description: Optional[str] = None,
        changed_by: UUID = None
    ) -> dict:
        """Update only the exercise data of a lesson"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get current lesson
                lesson = await conn.fetchrow(
                    "SELECT * FROM learning.course_lessons WHERE id = $1",
                    lesson_id
                )

                if not lesson:
                    raise ValueError("Lesson not found")

                old_exercise = lesson["exercise_data"]

                await conn.execute(
                    "UPDATE learning.course_lessons SET exercise_data = $1 WHERE id = $2",
                    json.dumps(exercise_data), lesson_id  # Convert dict to JSON string
                )

                # Record change
                await self._record_change(
                    conn, lesson_id, changed_by, "exercise",
                    str(old_exercise), str(exercise_data), False, change_description
                )

                # Course goes back to draft
                await conn.execute(
                    """UPDATE learning.course_modules
                       SET status = 'draft'
                       WHERE id = $1""",
                    lesson["module_id"]
                )

                return {
                    "status": "success",
                    "lesson_id": str(lesson_id),
                    "message": "Exercise updated. Course returned to draft status."
                }

        except Exception as e:
            logger.error(f"Error updating exercise: {e}")
            raise

    async def get_lesson_history(
        self,
        lesson_id: UUID,
        limit: int = 50
    ) -> List[dict]:
        """Get change history for a lesson"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                changes = await conn.fetch("""
                    SELECT
                        h.id, h.lesson_id, h.changed_by, h.changed_at,
                        h.change_type, h.change_description, h.is_minor_edit,
                        u.email as changed_by_email,
                        u.first_name, u.last_name
                    FROM learning.lesson_change_history h
                    LEFT JOIN auth.users u ON u.id = h.changed_by
                    WHERE h.lesson_id = $1
                    ORDER BY h.changed_at DESC
                    LIMIT $2
                """, lesson_id, limit)

                return [dict(row) for row in changes]

        except Exception as e:
            logger.error(f"Error getting lesson history: {e}")
            return []

    async def get_lesson_diff(
        self,
        lesson_id: UUID,
        change_id: UUID
    ) -> dict:
        """Get diff for a specific change"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                change = await conn.fetchrow(
                    "SELECT * FROM learning.lesson_change_history WHERE id = $1",
                    change_id
                )

                if not change:
                    raise ValueError("Change not found")

                # Generate diff
                if change["old_value"] and change["new_value"]:
                    diff = list(difflib.unified_diff(
                        change["old_value"].splitlines(keepends=True),
                        change["new_value"].splitlines(keepends=True),
                        fromfile="old",
                        tofile="new"
                    ))
                else:
                    diff = []

                return {
                    "change": dict(change),
                    "diff": diff
                }

        except Exception as e:
            logger.error(f"Error getting lesson diff: {e}")
            raise

    def _is_minor_change(self, old_content: str, new_content: str) -> bool:
        """
        Determine if a content change qualifies as "minor edit".
        Minor edits are small corrections, not structural changes.
        """
        if not old_content:
            return False

        old_length = len(old_content)
        new_length = len(new_content)

        # Calculate character difference ratio
        char_diff = abs(new_length - old_length)
        ratio = char_diff / old_length if old_length > 0 else 1

        # Check against thresholds
        if ratio > self.MINOR_EDIT_MAX_CHANGE_RATIO:
            return False

        if char_diff > self.MINOR_EDIT_MAX_ABSOLUTE:
            return False

        return True

    async def _record_change(
        self,
        conn,
        lesson_id: UUID,
        changed_by: UUID,
        change_type: str,
        old_value: Optional[str],
        new_value: Optional[str],
        is_minor_edit: bool,
        change_description: Optional[str] = None
    ):
        """Record a change in the lesson history"""
        try:
            # Truncate values if too large (PostgreSQL TEXT limit is ~1GB but we don't need that much)
            max_value_length = 10000  # Keep first 10k chars for history

            old_value_truncated = old_value[:max_value_length] if old_value else None
            new_value_truncated = new_value[:max_value_length] if new_value else None

            await conn.execute("""
                INSERT INTO learning.lesson_change_history
                (lesson_id, changed_by, change_type, change_description, old_value, new_value, is_minor_edit)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, lesson_id, changed_by, change_type, change_description,
               old_value_truncated, new_value_truncated, is_minor_edit)

        except Exception as e:
            logger.error(f"Error recording change: {e}")
            # Don't raise - change recording shouldn't break the update

    async def restore_lesson_version(
        self,
        lesson_id: UUID,
        change_id: UUID,
        restored_by: UUID
    ) -> dict:
        """
        Restore a lesson to a previous version from change history.
        Creates a new change entry for the restoration.
        """
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get the change to restore
                change = await conn.fetchrow(
                    "SELECT * FROM learning.lesson_change_history WHERE id = $1",
                    change_id
                )

                if not change:
                    raise ValueError("Change not found")

                # Get current lesson
                current_lesson = await conn.fetchrow(
                    "SELECT * FROM learning.course_lessons WHERE id = $1",
                    lesson_id
                )

                if not current_lesson:
                    raise ValueError("Lesson not found")

                # Determine what to restore based on change type
                if change["change_type"] == "content":
                    new_content = change["old_value"]  # old_value is what we want to restore
                    await conn.execute(
                        "UPDATE learning.course_lessons SET content = $1 WHERE id = $2",
                        new_content, lesson_id
                    )

                    # Record the restoration
                    await self._record_change(
                        conn, lesson_id, restored_by, "content",
                        current_lesson["content"], new_content, False,
                        f"Restored from change at {change['changed_at']}"
                    )

                elif change["change_type"] == "title":
                    new_title = change["old_value"]
                    await conn.execute(
                        "UPDATE learning.course_lessons SET title = $1 WHERE id = $2",
                        new_title, lesson_id
                    )

                    await self._record_change(
                        conn, lesson_id, restored_by, "title",
                        current_lesson["title"], new_title, False,
                        f"Restored from change at {change['changed_at']}"
                    )

                elif change["change_type"] == "exercise":
                    new_exercise = json.loads(change["old_value"]) if change["old_value"] else None
                    await conn.execute(
                        "UPDATE learning.course_lessons SET exercise_data = $1 WHERE id = $2",
                        json.dumps(new_exercise) if new_exercise else None, lesson_id  # Convert dict to JSON string
                    )

                    await self._record_change(
                        conn, lesson_id, restored_by, "exercise",
                        str(current_lesson["exercise_data"]), change["old_value"], False,
                        f"Restored from change at {change['changed_at']}"
                    )

                # Course goes back to draft
                await conn.execute(
                    """UPDATE learning.course_modules
                       SET status = 'draft'
                       WHERE id = $1""",
                    current_lesson["module_id"]
                )

                return {
                    "status": "success",
                    "lesson_id": str(lesson_id),
                    "message": f"Lesson restored to version from {change['changed_at']}"
                }

        except Exception as e:
            logger.error(f"Error restoring lesson: {e}")
            raise


# Singleton instance
lesson_edit_service = LessonEditService()
