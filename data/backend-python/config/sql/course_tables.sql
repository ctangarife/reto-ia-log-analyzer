-- Course Progress Tables for LogsAnomaly Learning System
-- These tables track user progress through the mini-course

-- Create learning schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS learning;

-- Course modules and lessons (static content)
CREATE TABLE IF NOT EXISTS learning.course_modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    module_order INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, module_order)
);

CREATE TABLE IF NOT EXISTS learning.course_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id UUID NOT NULL REFERENCES learning.course_modules(id) ON DELETE CASCADE,
    lesson_order INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    exercise_data JSONB,  -- Exercise configuration if applicable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(module_id, lesson_order)
);

-- User progress tracking
CREATE TABLE IF NOT EXISTS learning.lesson_progress (
    user_id UUID NOT NULL,
    project_id UUID NOT NULL,
    lesson_id UUID NOT NULL REFERENCES learning.course_lessons(id) ON DELETE CASCADE,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score INT,  -- Exercise score (0-100) if applicable
    attempts INT DEFAULT 0,
    PRIMARY KEY (user_id, project_id, lesson_id)
);

-- Course completion and badges
CREATE TABLE IF NOT EXISTS learning.course_completion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    project_id UUID NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_score INT DEFAULT 0,
    badge_earned BOOLEAN DEFAULT TRUE,
    certificate_url VARCHAR(500),
    UNIQUE(user_id, project_id)
);

-- Exercise attempts (for dynamic exercises using project logs)
CREATE TABLE IF NOT EXISTS learning.exercise_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    project_id UUID NOT NULL,
    lesson_id UUID NOT NULL REFERENCES learning.course_lessons(id) ON DELETE CASCADE,
    anomaly_id VARCHAR(255),  -- Reference to anomaly from project
    user_answer JSONB NOT NULL,
    is_correct BOOLEAN,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_lesson_progress_user ON learning.lesson_progress(user_id, project_id);
CREATE INDEX IF NOT EXISTS idx_lesson_progress_lesson ON learning.lesson_progress(lesson_id);
CREATE INDEX IF NOT EXISTS idx_exercise_attempts_user ON learning.exercise_attempts(user_id, project_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON learning.course_modules TO anomaly_user;
GRANT SELECT, INSERT, UPDATE ON learning.course_lessons TO anomaly_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON learning.lesson_progress TO anomaly_user;
GRANT SELECT, INSERT, UPDATE ON learning.course_completion TO anomaly_user;
GRANT SELECT, INSERT, UPDATE ON learning.exercise_attempts TO anomaly_user;

-- Grant usage on schema
GRANT USAGE ON SCHEMA learning TO anomaly_user;
