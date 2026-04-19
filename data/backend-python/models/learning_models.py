"""
Learning/Course Models
Models for the interactive mini-course system

Structure:
- courses: Main course entity (workflow, versioning, etc.)
- course_modules: Children of courses (4 fixed modules per course)
- course_lessons: Children of modules (lessons within a module)
"""
from datetime import datetime
from typing import Optional, List
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

class Course(Base):
    """Main course entity - represents a complete course with 4 modules

    A course belongs to a project and contains exactly 4 modules:
    1. Introducción a los Logs
    2. Tipos de Anomalías Detectadas
    3. Análisis Práctico
    4. Evaluación Final
    """
    __tablename__ = "courses"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Course workflow fields
    status = Column(String(20), default="draft")  # draft, pending, approved, published, archived
    scope = Column(String(20), default="project")  # project, workspace
    version_number = Column(Integer, default=1)

    # Creation and review tracking
    created_by = Column(PG_UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_by = Column(PG_UUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    # Rejection info
    rejection_reason = Column(Text, nullable=True)
    change_description = Column(Text, nullable=True)

    # Relationships
    modules = relationship("CourseModule", back_populates="course", cascade="all, delete-orphan")


class CourseModule(Base):
    """A module within a course (e.g., "Introducción a los Logs")

    Each course has exactly 4 fixed modules.
    """
    __tablename__ = "course_modules"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_id = Column(PG_UUID(as_uuid=True), ForeignKey("learning.courses.id", ondelete="CASCADE"), nullable=False)
    module_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Legacy fields (kept for backward compatibility during migration)
    project_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Use course.project_id instead
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Use course.workspace_id instead

    # Relationships
    course = relationship("Course", back_populates="modules")
    lessons = relationship("CourseLesson", back_populates="module", cascade="all, delete-orphan")


class CourseLesson(Base):
    """A lesson within a module (e.g., "¿Qué es un Log?")"""
    __tablename__ = "course_lessons"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    module_id = Column(PG_UUID(as_uuid=True), ForeignKey("learning.course_modules.id", ondelete="CASCADE"))
    lesson_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    exercise_data = Column(JSON)
    is_dynamic = Column(Boolean, default=False)  # Reserved for future use
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    module = relationship("CourseModule", back_populates="lessons")


class LessonProgress(Base):
    """User progress on a specific lesson"""
    __tablename__ = "lesson_progress"
    __table_args__ = {"schema": "learning"}

    user_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    project_id = Column(PG_UUID(as_uuid=True), primary_key=True, nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True)
    lesson_id = Column(PG_UUID(as_uuid=True), ForeignKey("learning.course_lessons.id", ondelete="CASCADE"), primary_key=True)
    completed_at = Column(DateTime, default=datetime.utcnow)
    score = Column(Integer)
    attempts = Column(Integer, default=0)


class CourseCompletion(Base):
    """Course completion record and badge"""
    __tablename__ = "course_completion"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), nullable=False, unique=True)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True)
    completed_at = Column(DateTime, default=datetime.utcnow)
    total_score = Column(Integer, default=0)
    badge_earned = Column(Boolean, default=True)
    certificate_url = Column(String(500))


class ExerciseAttempt(Base):
    """Record of user exercise attempts"""
    __tablename__ = "exercise_attempts"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), nullable=False)
    workspace_id = Column(PG_UUID(as_uuid=True), nullable=True)
    lesson_id = Column(PG_UUID(as_uuid=True), ForeignKey("learning.course_lessons.id", ondelete="CASCADE"))
    anomaly_id = Column(String(255))
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
    change_type = Column(String(50), nullable=False)
    change_description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    is_minor_edit = Column(Boolean, default=False)


# Legacy workflow models (for backward compatibility)
class CourseReview(Base):
    """Record of course reviews"""
    __tablename__ = "course_reviews"
    __table_args__ = {"schema": "learning"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_id = Column(PG_UUID(as_uuid=True), nullable=False)
    reviewer_id = Column(PG_UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False)
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
    type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# Pydantic Schemas (API Models)
# ============================================

# ============================================
# Course Response Models
# ============================================

class CourseResponse(BaseModel):
    """Main course response"""
    id: UUID
    project_id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    status: str
    scope: str
    version_number: int
    created_by: UUID
    created_at: datetime
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    change_description: Optional[str] = None

    # Stats
    module_count: int = 0
    lesson_count: int = 0

    class Config:
        from_attributes = True


class CourseListItem(BaseModel):
    """Course item for listing"""
    id: UUID
    project_id: UUID
    project_name: str
    name: str
    description: Optional[str] = None
    status: str
    module_count: int
    lesson_count: int
    created_at: datetime
    created_by: UUID


class CourseModuleResponse(BaseModel):
    """Course module response"""
    id: UUID
    course_id: UUID
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


class CourseProgressResponse(BaseModel):
    """Overall course progress for a user in a project"""
    course_id: Optional[UUID] = None
    course_name: Optional[str] = None
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


# ============================================
# Course Generation Models
# ============================================

class CourseGenerateRequest(BaseModel):
    """Request to generate a course"""
    scope: str = "project"
    name: Optional[str] = None


class CourseGenerateResponse(BaseModel):
    """Response from course generation"""
    course_id: UUID
    status: str
    modules_created: int
    lessons_created: int
    message: str


class CourseLimitsCheck(BaseModel):
    """Response from course limits validation"""
    can_create: bool
    reason: Optional[str] = None
    current_counts: dict


class ProjectAnalysis(BaseModel):
    """Analysis of project data for course generation"""
    project_id: UUID
    project_name: str
    total_logs: int
    total_anomalies: int
    anomaly_categories: dict[str, int]
    anomaly_severity_distribution: dict[str, int]
    log_formats: list[str]
    date_range: dict[str, str]
    can_generate_course: bool
    min_anomalies_required: int
    top_anomalies: list[dict]


class CoursePreviewResponse(BaseModel):
    """Response with preview data before course generation"""
    analysis: ProjectAnalysis
    suggested_modules: list[str]


# ============================================
# Course Management Models
# ============================================

class CourseUpdateRequest(BaseModel):
    """Request to update a course"""
    name: Optional[str] = None
    description: Optional[str] = None
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
    archive_existing: bool = False  # For publish: whether to archive existing published course


class ReviewActionResponse(BaseModel):
    """Response from review action"""
    course_id: UUID
    status: str
    message: str
    archived_course_id: Optional[UUID] = None  # If a course was archived during publish


class PendingCoursesResponse(BaseModel):
    """Response with pending courses for review"""
    workspace_id: UUID
    courses: list[dict]


# ============================================
# Lesson Progress Models
# ============================================

class LessonProgressUpdate(BaseModel):
    """Request to mark lesson as complete"""
    score: Optional[int] = None


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


class FinalExamAnswer(BaseModel):
    """Single answer in final exam"""
    anomaly_id: str
    anomaly_type: str  # Security, Performance, Network, Behavior, General
    severity: str  # Critical, High, Medium, Low
    action: str  # User's proposed action (description)


class FinalExamSubmissionRequest(BaseModel):
    """Submit complete final exam with all answers"""
    lesson_id: UUID
    answers: List[FinalExamAnswer]


class FinalExamAnswerResult(BaseModel):
    """Result for a single exam answer"""
    anomaly_id: str
    log_entry: str
    user_type: str
    correct_type: str
    user_severity: str
    correct_severity: str
    is_correct_type: bool
    is_correct_severity: bool
    points: int  # 0, 10, or 20


class FinalExamValidationResponse(BaseModel):
    """Final exam results with scoring"""
    passed: bool
    score: int  # 0-100
    passing_score: int
    feedback: str
    results: List[FinalExamAnswerResult]
    can_retake: bool
    certificate_earned: bool


# ============================================
# Certificate Models
# ============================================

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
    course_status: Optional[str] = None


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
    change_type: str
    change_description: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    is_minor_edit: bool


class LessonHistoryResponse(BaseModel):
    """Response with lesson change history"""
    lesson_id: UUID
    changes: list[LessonChangeHistory]


# ============================================
# Legacy/Other Models
# ============================================

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


class LessonRefreshRequest(BaseModel):
    """Request to refresh lesson content with new anomalies"""
    preserve_selection: bool = False


class LessonRefreshResponse(BaseModel):
    """Response from lesson refresh"""
    lesson_id: UUID
    message: str
    anomalies_updated: int


class WorkspaceCourseListItem(BaseModel):
    """A course in a workspace"""
    project_id: UUID
    project_name: str
    course_id: UUID
    name: str
    description: Optional[str] = None
    total_lessons: int
    completed_lessons: int
    is_completed: bool


class WorkspaceCoursesResponse(BaseModel):
    """Response with all courses in a workspace"""
    workspace_id: UUID
    courses: list[WorkspaceCourseListItem]
