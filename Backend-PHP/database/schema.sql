-- RMC Quiz and Examination System Database Schema
-- Run this in phpMyAdmin or MySQL CLI to set up the database

CREATE DATABASE IF NOT EXISTS quiz_system
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE quiz_system;

-- ============================================================
-- 1. Core / Auth tables
-- ============================================================

CREATE TABLE IF NOT EXISTS roles (
    role_id    INT AUTO_INCREMENT PRIMARY KEY,
    role_name  VARCHAR(20) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    first_name    VARCHAR(100) NOT NULL,
    last_name     VARCHAR(100) NOT NULL,
    username      VARCHAR(100) NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    student_id    VARCHAR(30)  DEFAULT NULL,
    year_level    VARCHAR(20)  DEFAULT NULL,
    section       VARCHAR(50)  DEFAULT NULL,
    status        ENUM('ACTIVE','INACTIVE','BANNED') DEFAULT 'ACTIVE',
    role_id       INT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    token      VARCHAR(64) NOT NULL UNIQUE,
    expires_at DATETIME    NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS activity_logs (
    log_id      INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    action      VARCHAR(50)  NOT NULL,
    description TEXT         DEFAULT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS password_resets (
    reset_id    INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    reset_token VARCHAR(64) NOT NULL,
    expires_at  DATETIME    NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 2. Class & enrollment tables
-- ============================================================

CREATE TABLE IF NOT EXISTS classes (
    class_id     INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(20)  NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    block        VARCHAR(50)  NOT NULL,
    class_code   VARCHAR(10)  NOT NULL UNIQUE,
    teacher_id   INT NOT NULL,
    status       ENUM('ACTIVE','ARCHIVED') DEFAULT 'ACTIVE',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    class_id      INT NOT NULL,
    enrolled_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_enrollment (user_id, class_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 3. Exam, question, and submission tables
-- ============================================================

CREATE TABLE IF NOT EXISTS exams (
    exam_id             INT AUTO_INCREMENT PRIMARY KEY,
    class_id            INT NOT NULL,
    exam_name           VARCHAR(150) NOT NULL,
    description         TEXT         DEFAULT NULL,
    duration_minutes    INT          NOT NULL DEFAULT 60,
    start_time          DATETIME     DEFAULT NULL,
    end_time            DATETIME     DEFAULT NULL,
    is_closed           TINYINT(1)   NOT NULL DEFAULT 0,
    closed_at           DATETIME     DEFAULT NULL,
    passing_score       INT          DEFAULT 70,
    status              ENUM('DRAFT','SCHEDULED','LIVE','CLOSED','ARCHIVED') DEFAULT 'DRAFT',
    total_points        INT          NOT NULL DEFAULT 100,
    randomize_questions TINYINT(1)   DEFAULT 0,
    randomize_options   TINYINT(1)   DEFAULT 0,
    max_exit_attempts   INT          DEFAULT 3,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS questions (
    question_id     INT AUTO_INCREMENT PRIMARY KEY,
    exam_id         INT NOT NULL,
    question_text   TEXT NOT NULL,
    question_type   ENUM('MULTIPLE_CHOICE','TRUE_FALSE','IDENTIFICATION','ENUMERATION') DEFAULT 'MULTIPLE_CHOICE',
    options         JSON        DEFAULT NULL,
    correct_answer  VARCHAR(500) DEFAULT NULL,
    points          INT         DEFAULT 1,
    answer_matching ENUM('EXACT','IGNORE_CASE') DEFAULT 'EXACT',
    order_num       INT NOT NULL DEFAULT 0,
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS exam_submissions (
    submission_id   INT AUTO_INCREMENT PRIMARY KEY,
    exam_id         INT NOT NULL,
    user_id         INT NOT NULL,
    answers_json    JSON         DEFAULT NULL,
    score           INT          DEFAULT NULL,
    correct_count   INT          DEFAULT NULL,
    total_questions INT          DEFAULT NULL,
    time_used_secs  INT          DEFAULT NULL,
    exit_attempts   INT          DEFAULT 0,
    auto_submitted  TINYINT(1)   DEFAULT 0,
    submitted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_submission (exam_id, user_id),
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS exam_temp_answers (
    temp_id      INT AUTO_INCREMENT PRIMARY KEY,
    exam_id      INT NOT NULL,
    user_id      INT NOT NULL,
    answers_json JSON DEFAULT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_temp_answer (exam_id, user_id),
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 4. Seed data: roles + test users + classes + exams + questions
-- ============================================================

INSERT IGNORE INTO roles (role_id, role_name) VALUES (1, 'STUDENT'), (2, 'TEACHER');

-- Password for all test accounts: TestPass123
SET @teacher_hash = '$2y$10$qCDKEOWi8KtwlNVRMStO7OIvFmDbsrPbLUN2aAZ3qUkVBTfnE8MNm';
SET @student_hash = '$2y$10$qCDKEOWi8KtwlNVRMStO7OIvFmDbsrPbLUN2aAZ3qUkVBTfnE8MNm';

-- Teacher accounts
INSERT IGNORE INTO users (user_id, first_name, last_name, username, email, password_hash, status, role_id)
VALUES
(1, 'Ricardo', 'Domingo', 'prof.domingo', 'domingo@rmc.edu.ph', @teacher_hash, 'ACTIVE', 2),
(2, 'Maria', 'Santos', 'prof.santos', 'santos@rmc.edu.ph', @teacher_hash, 'ACTIVE', 2),
(3, 'Juan', 'Reyes', 'prof.reyes', 'reyes@rmc.edu.ph', @teacher_hash, 'ACTIVE', 2);

-- Student accounts
INSERT IGNORE INTO users (user_id, first_name, last_name, username, email, password_hash, student_id, year_level, section, status, role_id)
VALUES
(4, 'Sofia', 'Cruz', 'sofia.cruz', 'sofia.cruz@rmc.edu.ph', @student_hash, '136578100123', '3rd Year', 'BSIT 3-A', 'ACTIVE', 1),
(5, 'Miguel', 'Reyes', 'miguel.reyes', 'miguel.reyes@rmc.edu.ph', @student_hash, '136578100124', '3rd Year', 'BSIT 3-A', 'ACTIVE', 1),
(6, 'Ana', 'Garcia', 'ana.garcia', 'ana.garcia@rmc.edu.ph', @student_hash, '136578100125', '2nd Year', 'BSIT 2-B', 'ACTIVE', 1);

-- Classes (teacher_id references users.user_id)
INSERT IGNORE INTO classes (class_id, subject_code, subject_name, block, class_code, teacher_id, status)
VALUES
(1, 'IT 301', 'Software Engineering', 'BSIT 3-A', '7F3K9Q', 1, 'ACTIVE'),
(2, 'IT 302', 'Database Systems',     'BSIT 3-A', '8G2M4P', 2, 'ACTIVE'),
(3, 'IT 303', 'Web Development',       'BSIT 3-A', '2H5N7R', 3, 'ACTIVE'),
(4, 'IT 201', 'Data Structures',       'BSIT 2-B', '9K3L6T', 2, 'ACTIVE');

-- Enrollments
INSERT IGNORE INTO enrollments (user_id, class_id) VALUES
(4, 1), (4, 2), (4, 3),
(5, 1), (5, 2),
(6, 4);

-- Exams
INSERT IGNORE INTO exams (exam_id, class_id, exam_name, description, duration_minutes, passing_score, status, total_points)
VALUES
(1, 1, 'Midterm Exam',  'Covers SDLC, Agile, and requirements gathering.', 60, 70, 'LIVE', 100),
(2, 2, 'Quiz 1',        'Covers relational database basics and ER modeling.', 30, 70, 'DRAFT', 50),
(3, 3, 'Prelim Exam',   'Covers HTML, CSS, and JavaScript fundamentals.', 90, 70, 'CLOSED', 100),
(4, 1, 'Quiz 1',        'Covers Software Development Life Cycle models.', 30, 70, 'LIVE', 50),
(5, 4, 'Midterm Exam',  'Covers arrays, linked lists, and trees.', 60, 70, 'LIVE', 100);

-- Questions for Exam 1 (Midterm Exam - Software Engineering)
INSERT IGNORE INTO questions (exam_id, question_text, question_type, options, correct_answer, points, order_num)
VALUES
(1, 'What does SDLC stand for?', 'MULTIPLE_CHOICE', '["Software Development Life Cycle","System Design Life Cycle","Software Data Life Cycle","System Development Logic Cycle"]', 'Software Development Life Cycle', 1, 1),
(1, 'Which methodology uses sprints of 1-4 weeks?', 'MULTIPLE_CHOICE', '["Waterfall","Scrum","V-Model","Spiral"]', 'Scrum', 1, 2),
(1, 'What is the first phase of the Waterfall model?', 'MULTIPLE_CHOICE', '["Design","Implementation","Requirements Gathering","Testing"]', 'Requirements Gathering', 1, 3),
(1, 'Which document defines what the software should do?', 'MULTIPLE_CHOICE', '["User Manual","Requirements Document","Test Plan","Source Code"]', 'Requirements Document', 1, 4),
(1, 'What is a use case diagram used for?', 'MULTIPLE_CHOICE', '["Coding","Database design","Describing system functionality from user perspective","Performance testing"]', 'Describing system functionality from user perspective', 1, 5),
(1, 'Which of these is NOT an Agile methodology?', 'MULTIPLE_CHOICE', '["Scrum","Kanban","Waterfall","XP"]', 'Waterfall', 1, 6),
(1, 'What is a sprint retrospective?', 'MULTIPLE_CHOICE', '["A daily meeting","A review of what went well and what to improve","A product demo","A coding session"]', 'A review of what went well and what to improve', 1, 7),
(1, 'Who is responsible for removing impediments in Scrum?', 'MULTIPLE_CHOICE', '["Product Owner","Scrum Master","Development Team","Project Manager"]', 'Scrum Master', 1, 8),
(1, 'What is the purpose of a backlog?', 'MULTIPLE_CHOICE', '["Store completed work","Prioritized list of features and tasks","Bug tracking","Team schedule"]', 'Prioritized list of features and tasks', 1, 9),
(1, 'Which testing is done by the end user?', 'MULTIPLE_CHOICE', '["Unit Testing","Integration Testing","User Acceptance Testing","System Testing"]', 'User Acceptance Testing', 1, 10);

-- Questions for Exam 4 (Quiz 1 - Software Engineering)
INSERT IGNORE INTO questions (exam_id, question_text, question_type, options, correct_answer, points, order_num)
VALUES
(4, 'What is the most sequential SDLC model?', 'MULTIPLE_CHOICE', '["Agile","Waterfall","Scrum","Kanban"]', 'Waterfall', 1, 1),
(4, 'How long is a typical Scrum sprint?', 'MULTIPLE_CHOICE', '["1-4 weeks","2-3 months","6 months","1 year"]', '1-4 weeks', 1, 2),
(4, 'What is a user story?', 'MULTIPLE_CHOICE', '["A bug report","A feature written from the user perspective","A technical document","A database schema"]', 'A feature written from the user perspective', 1, 3),
(4, 'Which role prioritizes the product backlog?', 'MULTIPLE_CHOICE', '["Scrum Master","Developer","Product Owner","Tester"]', 'Product Owner', 1, 4),
(4, 'What is the output of the requirements phase?', 'MULTIPLE_CHOICE', '["Source code","Software requirements specification","Test cases","UML diagrams"]', 'Software requirements specification', 1, 5);

-- Questions for Exam 3 (Prelim Exam - Web Development)
INSERT IGNORE INTO questions (exam_id, question_text, question_type, options, correct_answer, points, order_num)
VALUES
(3, 'What does HTML stand for?', 'MULTIPLE_CHOICE', '["Hyper Text Markup Language","High Tech Modern Language","Hyper Transfer Markup Language","Home Tool Markup Language"]', 'Hyper Text Markup Language', 1, 1),
(3, 'Which CSS property changes text color?', 'MULTIPLE_CHOICE', '["font-color","text-color","color","foreground-color"]', 'color', 1, 2),
(3, 'Which tag creates a hyperlink in HTML?', 'MULTIPLE_CHOICE', '["<link>","<a>","<href>","<url>"]', '<a>', 1, 3),
(3, 'What does the box model in CSS include?', 'MULTIPLE_CHOICE', '["Margin, border, padding, content","Width, height, depth","Font, color, size","Position, layout, design"]', 'Margin, border, padding, content', 1, 4),
(3, 'Which JavaScript method selects an element by ID?', 'MULTIPLE_CHOICE', '["getElementByClass()","querySelector()","getElementById()","findElement()"]', 'getElementById()', 1, 5);

-- Exam submissions for Exam 3 (Prelim Exam - completed by Sofia)
INSERT IGNORE INTO exam_submissions (exam_id, user_id, answers_json, score, correct_count, total_questions, time_used_secs)
VALUES
(3, 4, '{"1":"Hyper Text Markup Language","2":"color","3":"<a>","4":"Margin, border, padding, content","5":"getElementById()"}', 85, 4, 5, 3600);

-- ============================================================
-- 5. Indexes for performance
-- ============================================================

CREATE INDEX idx_sessions_token     ON sessions(token);
CREATE INDEX idx_enrollments_user   ON enrollments(user_id);
CREATE INDEX idx_enrollments_class  ON enrollments(class_id);
CREATE INDEX idx_exams_class        ON exams(class_id);
CREATE INDEX idx_questions_exam     ON questions(exam_id);
CREATE INDEX idx_submissions_user   ON exam_submissions(user_id);
CREATE INDEX idx_submissions_exam   ON exam_submissions(exam_id);
