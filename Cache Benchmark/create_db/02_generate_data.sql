-- 02_generate_data.sql

BEGIN;

-- 1. Insert Departments
INSERT INTO departments (department_name)
VALUES ('CSE'), ('ECE'), ('EE'), ('ME'), ('CE'), ('IT');

-- 2. Insert Courses (120 courses, 20 per department)
INSERT INTO courses (course_code, course_name, credits, department_id)
SELECT 
    d.department_name || '-' || lpad(g.id::text, 3, '0'),
    'Course ' || d.department_name || ' ' || g.id,
    floor(random() * 3 + 2)::int, -- Credits between 2 and 4
    d.department_id
FROM departments d
CROSS JOIN generate_series(1, 20) as g(id);

-- 3. Insert Faculty (300 faculty, 50 per department)
INSERT INTO faculty (name, department_id)
SELECT 
    (ARRAY['Dr. Sharma', 'Dr. Patel', 'Dr. Singh', 'Prof. Kumar', 'Dr. Das', 'Prof. Gupta', 'Dr. Ghosh', 'Dr. Roy', 'Prof. Bose', 'Dr. Chatterjee'])[floor(random() * 10 + 1)] || ' ' || g.id,
    d.department_id
FROM departments d
CROSS JOIN generate_series(1, 50) as g(id);

-- 4. Insert 1,000,000 Students
INSERT INTO students (roll_number, name, email, age, department_id, admission_year)
SELECT 
    'ROLL' || lpad(id::text, 7, '0'),
    (ARRAY['Aarav', 'Vihaan', 'Aditya', 'Rohan', 'Karan', 'Priya', 'Sneha', 'Ananya', 'Riya', 'Neha'])[floor(random() * 10 + 1)] || ' ' || 
    (ARRAY['Sharma', 'Patel', 'Singh', 'Kumar', 'Das', 'Gupta', 'Ghosh', 'Roy', 'Bose', 'Chatterjee'])[floor(random() * 10 + 1)],
    'student' || id || '@college.edu',
    floor(random() * 5 + 18)::int, -- Age 18-22
    floor(random() * 6 + 1)::int,  -- Dept 1-6
    floor(random() * 4 + 2020)::int -- Year 2020-2023
FROM generate_series(1, 1000000) AS id;

-- 5. Insert Enrollments (5 courses per student = 5,000,000 rows)
INSERT INTO enrollments (student_id, course_id, semester, academic_year)
SELECT 
    s.student_id,
    floor(random() * 120 + 1)::int, -- Random course 1-120
    floor(random() * 8 + 1)::int,   -- Semester 1-8
    2023
FROM students s
CROSS JOIN generate_series(1, 5);

-- 6. Insert Marks (Matches the 5,000,000 enrollments)
WITH calculated_marks AS (
    SELECT student_id, course_id, floor(random() * 60 + 40)::int AS score
    FROM enrollments
)
INSERT INTO marks (student_id, course_id, marks, grade)
SELECT 
    student_id, 
    course_id, 
    score,
    CASE 
        WHEN score >= 90 THEN 'O'
        WHEN score >= 80 THEN 'E'
        WHEN score >= 70 THEN 'A'
        WHEN score >= 60 THEN 'B'
        WHEN score >= 50 THEN 'C'
        ELSE 'F'
    END
FROM calculated_marks;
COMMIT;