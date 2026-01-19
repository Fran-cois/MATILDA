"""
Create a dataset to compare SPIDER (inclusion dependencies) and MATILDA (TGD rules).
The dataset will have controlled violations to test both algorithms.
"""

import sqlite3
import os
import shutil

# Paths
db_path = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/ComparisonDataset.db"
tsv_dir = "/Users/famat/PycharmProjects/MATILDA_ALL/NMATILDA/MATILDA/data/db/ComparisonDataset/tsv"

# Create directories
os.makedirs(os.path.dirname(db_path), exist_ok=True)
os.makedirs(tsv_dir, exist_ok=True)

# Remove existing database
if os.path.exists(db_path):
    os.remove(db_path)

# Create connection
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Creating tables...")

# Create tables for a simple university database
# students(id, name_id, department_id)
# departments(id, name)
# professors(id, name_id, department_id)
# courses(id, name_id, professor_id)

cursor.execute("""
    CREATE TABLE students (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT,
        arg3 TEXT,
        FOREIGN KEY (arg2) REFERENCES student_names (arg1),
        FOREIGN KEY (arg3) REFERENCES departments (arg1)
    )
""")

cursor.execute("""
    CREATE TABLE student_names (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT
    )
""")

cursor.execute("""
    CREATE TABLE departments (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT
    )
""")

cursor.execute("""
    CREATE TABLE professors (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT,
        arg3 TEXT,
        FOREIGN KEY (arg2) REFERENCES professor_names (arg1),
        FOREIGN KEY (arg3) REFERENCES departments (arg1)
    )
""")

cursor.execute("""
    CREATE TABLE professor_names (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT
    )
""")

cursor.execute("""
    CREATE TABLE courses (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT,
        arg3 TEXT,
        FOREIGN KEY (arg2) REFERENCES course_names (arg1),
        FOREIGN KEY (arg3) REFERENCES professors (arg1)
    )
""")

cursor.execute("""
    CREATE TABLE course_names (
        arg1 TEXT PRIMARY KEY,
        arg2 TEXT
    )
""")

print("Inserting data with controlled violations...")

# Insert departments (5 departments)
departments_data = []
for i in range(1, 6):
    dept_id = f"DEPT{i:03d}"
    dept_name = f"Department_{i}"
    departments_data.append((dept_id, dept_name))

cursor.executemany("INSERT INTO departments VALUES (?, ?)", departments_data)

# Insert student names
student_names_data = []
for i in range(1, 101):
    name_id = f"SN{i:03d}"
    name = f"Student_{i}"
    student_names_data.append((name_id, name))

cursor.executemany("INSERT INTO student_names VALUES (?, ?)", student_names_data)

# Insert students with some violations
students_data = []
for i in range(1, 101):  # 100 students (reduced from 120)
    student_id = f"S{i:03d}"
    
    if i <= 95:
        # Valid name reference
        name_id = f"SN{i:03d}" if i <= 100 else f"SN{(i % 100) + 1:03d}"
    else:
        # VIOLATION: reference to non-existent name (5 students = 5%)
        name_id = f"SN999"
    
    if i <= 90:
        # Valid department reference
        dept_id = f"DEPT{(i % 5) + 1:03d}"
    elif i <= 95:
        # VIOLATION: reference to non-existent department (5 students = 5%)
        dept_id = "DEPT999"
    else:
        # Missing department (5 students = 5%)
        dept_id = None
    
    students_data.append((student_id, name_id, dept_id))

cursor.executemany("INSERT INTO students VALUES (?, ?, ?)", students_data)

# Insert professor names
professor_names_data = []
for i in range(1, 21):
    name_id = f"PN{i:03d}"
    name = f"Professor_{i}"
    professor_names_data.append((name_id, name))

cursor.executemany("INSERT INTO professor_names VALUES (?, ?)", professor_names_data)

# Insert professors (all valid - 20 professors)
professors_data = []
for i in range(1, 21):
    prof_id = f"P{i:03d}"
    name_id = f"PN{i:03d}"
    dept_id = f"DEPT{(i % 5) + 1:03d}"
    professors_data.append((prof_id, name_id, dept_id))

cursor.executemany("INSERT INTO professors VALUES (?, ?, ?)", professors_data)

# Insert course names
course_names_data = []
for i in range(1, 51):
    name_id = f"CN{i:03d}"
    name = f"Course_{i}"
    course_names_data.append((name_id, name))

cursor.executemany("INSERT INTO course_names VALUES (?, ?)", course_names_data)

# Insert courses with some violations
courses_data = []
for i in range(1, 51):  # 50 courses (reduced from 60)
    course_id = f"C{i:03d}"
    
    # All valid name references
    name_id = f"CN{i:03d}"
    
    if i <= 48:
        # Valid professor reference
        prof_id = f"P{(i % 20) + 1:03d}"
    else:
        # VIOLATION: reference to non-existent professor (2 courses = 4%)
        prof_id = "P999"
    
    courses_data.append((course_id, name_id, prof_id))

cursor.executemany("INSERT INTO courses VALUES (?, ?, ?)", courses_data)

conn.commit()

# Calculate statistics
cursor.execute("SELECT COUNT(*) FROM students")
total_students = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM students s LEFT JOIN student_names sn ON s.arg2 = sn.arg1 WHERE sn.arg1 IS NULL")
invalid_student_names = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM students s LEFT JOIN departments d ON s.arg3 = d.arg1 WHERE s.arg3 IS NOT NULL AND d.arg1 IS NULL")
invalid_student_depts = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM students WHERE arg3 IS NULL")
missing_student_depts = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM professors")
total_professors = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM courses")
total_courses = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM courses c LEFT JOIN course_names cn ON c.arg2 = cn.arg1 WHERE cn.arg1 IS NULL")
invalid_course_names = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM courses c LEFT JOIN professors p ON c.arg3 = p.arg1 WHERE p.arg1 IS NULL")
invalid_course_profs = cursor.fetchone()[0]

conn.close()

print(f"\n✅ Database created: {db_path}")
print(f"\nStatistics:")
print(f"\nStudents: {total_students}")
print(f"  - Invalid name references: {invalid_student_names} ({invalid_student_names/total_students*100:.1f}%)")
print(f"  - Invalid department references: {invalid_student_depts} ({invalid_student_depts/total_students*100:.1f}%)")
print(f"  - Missing department: {missing_student_depts} ({missing_student_depts/total_students*100:.1f}%)")

print(f"\nProfessors: {total_professors}")
print(f"  - All valid (no violations)")

print(f"\nCourses: {total_courses}")
print(f"  - Invalid name references: {invalid_course_names} ({invalid_course_names/total_courses*100:.1f}%)")
print(f"  - Invalid professor references: {invalid_course_profs} ({invalid_course_profs/total_courses*100:.1f}%)")

print(f"\nExpected Inclusion Dependencies:")
print(f"• students.arg2 ⊆ student_names.arg1: ~{(total_students-invalid_student_names)/total_students*100:.1f}%")
print(f"• students.arg3 ⊆ departments.arg1: ~{(total_students-invalid_student_depts-missing_student_depts)/total_students*100:.1f}%")
print(f"• professors.arg2 ⊆ professor_names.arg1: 100%")
print(f"• professors.arg3 ⊆ departments.arg1: 100%")
print(f"• courses.arg2 ⊆ course_names.arg1: ~{(total_courses-invalid_course_names)/total_courses*100:.1f}%")
print(f"• courses.arg3 ⊆ professors.arg1: ~{(total_courses-invalid_course_profs)/total_courses*100:.1f}%")
