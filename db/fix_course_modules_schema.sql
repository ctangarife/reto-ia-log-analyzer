-- Fix course_modules schema for v2 courses table structure
-- This migration makes project_id nullable and adds proper FK for course_id

BEGIN;

-- Make project_id nullable (since we now use course_id as the main reference)
ALTER TABLE learning.course_modules ALTER COLUMN project_id DROP NOT NULL;

-- Add foreign key constraint for course_id
ALTER TABLE learning.course_modules
ADD CONSTRAINT course_modules_course_id_fkey
FOREIGN KEY (course_id) REFERENCES learning.courses(id) ON DELETE CASCADE;

-- Drop the old unique constraint on project_id + module_order since we now use course_id
-- (This might fail if it doesn't exist, so we use IF EXISTS)
DO $$
BEGIN
    ALTER TABLE learning.course_modules DROP CONSTRAINT IF EXISTS course_modules_project_id_module_order_key;
EXCEPTION
    WHEN others THEN null;
END $$;

-- Add new unique constraint on course_id + module_order
ALTER TABLE learning.course_modules
ADD CONSTRAINT course_modules_course_id_module_order_key
UNIQUE (course_id, module_order);

COMMIT;
