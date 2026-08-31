-- 04_test_queries.sql

-- ==========================================
-- POINT LOOKUPS (Ideal targets for caching)
-- ==========================================
-- 1. Find student by ID
SELECT * FROM students WHERE student_id = 50000;

-- 2. Find student by roll number
SELECT * FROM students WHERE roll_number = 'ROLL0050000';

-- 3. Get all marks for a specific student
SELECT * FROM marks WHERE student_id = 50000;

-- 4. Get all enrolled courses for a specific student
SELECT * FROM enrollments WHERE student_id = 50000;


-- ==========================================
-- JOIN QUERIES (Higher CPU/Disk cost)
-- ==========================================
-- 5. Student details with their department name
SELECT s.name, s.roll_number, d.department_name 
FROM students s 
JOIN departments d ON s.department_id = d.department_id 
WHERE s.student_id = 12345;

-- 6. Student with their enrolled course names
SELECT s.name, c.course_name, e.semester 
FROM students s
JOIN enrollments e ON s.student_id = e.student_id
JOIN courses c ON e.course_id = c.course_id
WHERE s.student_id = 12345;

-- 7. Student with courses and marks (Heavy JOIN)
SELECT s.name, c.course_name, m.marks, m.grade
FROM students s
JOIN marks m ON s.student_id = m.student_id
JOIN courses c ON m.course_id = c.course_id
WHERE s.student_id = 12345;


-- ==========================================
-- AGGREGATION QUERIES (Good for longer TTL caching)
-- ==========================================
-- 8. Number of students per department
SELECT d.department_name, COUNT(s.student_id) as total_students
FROM departments d
JOIN students s ON d.department_id = s.department_id
GROUP BY d.department_name;

-- 9. Average marks per department
SELECT d.department_name, AVG(m.marks) as avg_marks
FROM departments d
JOIN students s ON d.department_id = s.department_id
JOIN marks m ON s.student_id = m.student_id
GROUP BY d.department_name;

-- 10. Number of students in each course
SELECT course_id, COUNT(student_id) as enrolled_count
FROM enrollments
GROUP BY course_id
ORDER BY enrolled_count DESC
LIMIT 10;


-- ==========================================
-- RANGE QUERIES 
-- ==========================================
-- 11. Top students with marks above 95
SELECT student_id, course_id, marks 
FROM marks 
WHERE marks > 95 
LIMIT 20;

-- 12. Students admitted in 2022 in department 1 (CSE)
SELECT * FROM students 
WHERE admission_year = 2022 AND department_id = 1 
LIMIT 20;