-- 03_indexes.sql

-- Speeds up queries filtering by department (e.g., "Find all CSE students")
CREATE INDEX idx_students_department ON students(department_id);

-- Speeds up JOINs between enrollments and students/courses
CREATE INDEX idx_enrollments_student ON enrollments(student_id);
CREATE INDEX idx_enrollments_course ON enrollments(course_id);

-- Speeds up JOINs and lookups for a specific student's marks
CREATE INDEX idx_marks_student ON marks(student_id);
CREATE INDEX idx_marks_course ON marks(course_id);

-- Speeds up range queries for grades (e.g., "Find students with marks > 80")
CREATE INDEX idx_marks_score ON marks(marks);