"""
Learning/Course Models
Models for the interactive mini-course system
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# ============================================
# ORM Models (Database Tables)
# ============================================

class CourseModule(Base):
    """A course module (e.g., "Introducción a Logs")
    Can be project-scoped or workspace-scoped.
    """
    __tablename__ = "course_modules"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PG_UUID(as_uuid=True), nullable=True)  # NULL for workspace courses
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Required for workspace courses
    module_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Course workflow fields
    status = Column(String(20), default="draft")  # draft, pending, approved, published, archived
    scope = Column(String(20), default="project")  # project, workspace
    version_number = Column(Integer, default=1)

    # Creation and review tracking
    created_by = Column(PG_UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_by = Column(PG_UUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    # Rejection info
    rejection_reason = Column(Text, nullable=True)
    change_description = Column(Text, nullable=True)  # Description of changes for new version

    # Relationships
    lessons = relationship("CourseLesson", back_populates="module", cascade="all, delete-orphan")


class CourseLesson(Base):
    """A lesson within a module (e.g., "Anatomía de un Log")"""
    __tablename__ = "course_lessons"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    module_id = Column(PG_UUID(as_uuid=True), ForeignKey("learning.course_modules.id", ondelete="CASCADE"))
    lesson_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # NULL for dynamic lessons
    exercise_data = Column(JSON)  # Exercise configuration
    is_dynamic = Column(Boolean, default=False)  # TRUE = generated on-the-fly
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    module = relationship("CourseModule", back_populates="lessons")


class LessonProgress(Base):
    """User progress on a specific lesson (always project scoped)"""
    __tablename__ = "lesson_progress"
    __table_args__ = {"schema": "learning"}

    user_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    project_id = Column(PG_UUID(as_uuid=True), primary_key=True, nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Reference for queries
    lesson_id = Column(PG_UUID(as_uuid=True), ForeignKey("learning.course_lessons.id", ondelete="CASCADE"), primary_key=True)
    completed_at = Column(DateTime, default=datetime.utcnow)
    score = Column(Integer)  # 0-100 for exercises
    attempts = Column(Integer, default=0)


class CourseCompletion(Base):
    """Course completion record and badge (always project scoped)"""
    __tablename__ = "course_completion"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), nullable=False, unique=True)  # One completion per project
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Reference for queries
    completed_at = Column(DateTime, default=datetime.utcnow)
    total_score = Column(Integer, default=0)
    badge_earned = Column(Boolean, default=True)
    certificate_url = Column(String(500))


class ExerciseAttempt(Base):
    """Record of user exercise attempts (for analytics, always project scoped)"""
    __tablename__ = "exercise_attempts"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Reference for queries
    lesson_id = Column(PG_UUID(as_uuid=True), ForeignKey("learning.course_lessons.id", ondelete="CASCADE"))
    anomaly_id = Column(String(255))  # Reference to specific anomaly
    user_answer = Column(JSON, nullable=False)
    is_correct = Column(Boolean)
    attempted_at = Column(DateTime, default=datetime.utcnow)


class LessonChangeHistory(Base):
    """Record of lesson content changes"""
    __tablename__ = "lesson_change_history"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    lesson_id = Column(PG_UUID(as_uuid=True), ForeignKey("learning.course_lessons.id", ondelete="CASCADE"))
    changed_by = Column(PG_UUID(as_uuid=True), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    change_type = Column(String(50), nullable=False)  # content, title, exercise, minor_edit
    change_description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    is_minor_edit = Column(Boolean, default=False)


# ============================================
# Pydantic Schemas (API Models)
# ============================================

class CourseModuleResponse(BaseModel):
    """Course module response (always project scoped)"""
    id: UUID
    project_id: UUID
    workspace_id: Optional[UUID] = None
    module_order: int
    title: str
    description: Optional[str] = None
    completed_lessons: int = 0
    total_lessons: int = 0
    lessons: list["CourseLessonResponse"] = []

    class Config:
        from_attributes = True


class CourseLessonResponse(BaseModel):
    """Course lesson response"""
    id: UUID
    module_id: UUID
    lesson_order: int
    title: str
    content: str
    exercise_data: Optional[dict] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LessonProgressUpdate(BaseModel):
    """Request to mark lesson as complete"""
    score: Optional[int] = None  # For exercises


class ExerciseValidationRequest(BaseModel):
    """Request to validate exercise answer"""
    lesson_id: UUID
    anomaly_id: str
    user_answer: dict


class ExerciseValidationResponse(BaseModel):
    """Response from exercise validation"""
    is_correct: bool
    feedback: str
    correct_answer: Optional[dict] = None
    explanation: str


class CourseProgressResponse(BaseModel):
    """Overall course progress for a user in a project"""
    project_id: UUID
    workspace_id: Optional[UUID] = None
    user_id: UUID
    modules: list[CourseModuleResponse]
    total_modules: int
    completed_modules: int
    total_lessons: int
    completed_lessons: int
    progress_percentage: float
    is_completed: bool
    completed_at: Optional[datetime] = None
    badge_earned: bool = False
    certificate_url: Optional[str] = None


class WorkspaceCourseListItem(BaseModel):
    """A course in a workspace (for listing all courses)"""
    project_id: UUID
    project_name: str
    course_id: UUID  # module_id del primer módulo
    title: str
    description: Optional[str] = None
    total_lessons: int
    completed_lessons: int
    is_completed: bool


class WorkspaceCoursesResponse(BaseModel):
    """Response with all courses in a workspace and its projects"""
    workspace_id: UUID
    courses: list[WorkspaceCourseListItem]


class CertificateRequest(BaseModel):
    """Request to generate certificate"""
    project_id: UUID
    user_name: str


class CertificateResponse(BaseModel):
    """Certificate data"""
    certificate_url: str
    download_url: str
    issued_at: datetime
    badge_url: str


# ============================================
# Additional ORM Models for Course Workflow
# ============================================

class CourseReview(Base):
    """Record of course reviews"""
    __tablename__ = "course_reviews"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_id = Column(PG_UUID(as_uuid=True), nullable=False)
    reviewer_id = Column(PG_UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False)  # pending_review, approved, rejected
    comments = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.utcnow)
    version_number = Column(Integer, nullable=False)


class CourseVersion(Base):
    """Snapshot of course content for versioning"""
    __tablename__ = "course_versions"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_module_id = Column(PG_UUID(as_uuid=True), nullable=False)
    version_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(PG_UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    change_description = Column(Text, nullable=True)


class CourseNotification(Base):
    """Notifications for course reviews"""
    __tablename__ = "course_notifications"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    course_id = Column(PG_UUID(as_uuid=True), nullable=True)
    type = Column(String(50), nullable=False)  # pending_review, approved, rejected, published
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# Additional Pydantic Schemas for Course Workflow
# ============================================

class CourseGenerateRequest(BaseModel):
    """Request to generate a course"""
    scope: str = "project"  # project, workspace
    name: Optional[str] = None


class CourseGenerateResponse(BaseModel):
    """Response from course generation"""
    course_id: UUID
    status: str
    modules_created: int
    lessons_created: int
    message: str


class CoursePreviewRequest(BaseModel):
    """Request to preview course data before generation"""
    project_id: UUID


class ProjectAnalysis(BaseModel):
    """Analysis of project data for course generation"""
    project_id: UUID
    project_name: str
    total_logs: int
    total_anomalies: int
    anomaly_categories: dict[str, int]  # {category: count}
    anomaly_severity_distribution: dict[str, int]  # {severity: count}
    log_formats: list[str]  # ["Bro/Zeek", "CSV", etc.]
    date_range: dict[str, str]  # {"start": "...", "end": "..."}
    can_generate_course: bool
    min_anomalies_required: int
    top_anomalies: list[dict]  # Sample anomalies for preview


class CoursePreviewResponse(BaseModel):
    """Response with preview data before course generation"""
    analysis: ProjectAnalysis
    suggested_modules: list[str]


class CourseUpdateRequest(BaseModel):
    """Request to update a course"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    scope: Optional[str] = None
    change_description: Optional[str] = None


class CourseUpdateResponse(BaseModel):
    """Response from course update"""
    course_id: UUID
    status: str
    message: str


class SubmitForReviewRequest(BaseModel):
    """Request to submit course for review"""
    comments: Optional[str] = None


class ReviewActionRequest(BaseModel):
    """Request to approve/reject a course"""
    comments: Optional[str] = None


class ReviewActionResponse(BaseModel):
    """Response from review action"""
    course_id: UUID
    status: str
    message: str


class PendingCoursesResponse(BaseModel):
    """Response with pending courses for review"""
    workspace_id: UUID
    courses: list[dict]


class LessonRefreshRequest(BaseModel):
    """Request to refresh lesson content with new anomalies"""
    preserve_selection: bool = False  # If True, tries to keep similar anomalies


class LessonRefreshResponse(BaseModel):
    """Response from lesson refresh"""
    lesson_id: UUID
    message: str
    anomalies_updated: int


class CourseRegenerateRequest(BaseModel):
    """Request to regenerate course with new data"""
    change_description: Optional[str] = None


class CourseRegenerateResponse(BaseModel):
    """Response from course regeneration"""
    new_course_id: UUID
    version_number: int
    modules_created: int
    lessons_created: int
    message: str


# ============================================
# Lesson Edit Models
# ============================================

class LessonUpdateRequest(BaseModel):
    """Request to update a lesson"""
    title: Optional[str] = None
    content: Optional[str] = None
    exercise_data: Optional[dict] = None
    is_minor_edit: bool = False
    change_description: Optional[str] = None


class LessonUpdateResponse(BaseModel):
    """Response from lesson update"""
    lesson_id: UUID
    status: str
    message: str
    course_status: Optional[str] = None  # New status of the parent course


class ExerciseUpdateRequest(BaseModel):
    """Request to update lesson exercise"""
    exercise_data: dict
    change_description: Optional[str] = None


class ExerciseUpdateResponse(BaseModel):
    """Response from exercise update"""
    lesson_id: UUID
    message: str


class LessonChangeHistory(BaseModel):
    """Record of a lesson change"""
    id: UUID
    lesson_id: UUID
    changed_by: UUID
    changed_at: datetime
    change_type: str  # content, title, exercise, minor_edit
    change_description: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    is_minor_edit: bool


class LessonHistoryResponse(BaseModel):
    """Response with lesson change history"""
    lesson_id: UUID
    changes: list[LessonChangeHistory]
