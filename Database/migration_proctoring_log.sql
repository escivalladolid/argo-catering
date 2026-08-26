-- Migration: proctoring log for tab-switch / app-exit events during exams.
-- Applied to the quiz_system database. A row is inserted each time a student
-- leaves the exam screen (loses window focus) while a LIVE exam is in progress.

CREATE TABLE IF NOT EXISTS exam_proctoring_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    user_id INT NOT NULL,
    event_type VARCHAR(30) NOT NULL DEFAULT 'TAB_SWITCH',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_proc_exam_user (exam_id, user_id),
    INDEX idx_proc_created (exam_id, created_at)
);
