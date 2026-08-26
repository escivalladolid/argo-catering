-- ============================================================
-- MIGRATION: Exam lifecycle single source of truth
-- ============================================================
-- Converts the old status vocabulary to the new canonical set:
--   DRAFT, SCHEDULED, LIVE, CLOSED, ARCHIVED
--
-- 1. Map legacy values while the old ENUM is still in place.
-- 2. Rebuild the column ENUM with only the canonical values.
-- 3. Seed start/end times so automatic transitions work for
--    exams that are currently LIVE/SCHEDULED without times.
--
-- Run with:  mysql -u root quiz_system < migration_status_lifecycle.sql
-- ============================================================

USE quiz_system;

-- Map legacy statuses to the canonical vocabulary.
UPDATE exams SET status = 'LIVE'      WHERE status IN ('ONGOING');
UPDATE exams SET status = 'SCHEDULED' WHERE status IN ('UPCOMING');
UPDATE exams SET status = 'CLOSED'    WHERE status IN ('COMPLETED');

-- Rebuild the ENUM to only the canonical set.
ALTER TABLE exams
    MODIFY COLUMN status ENUM('DRAFT','SCHEDULED','LIVE','CLOSED','ARCHIVED') NOT NULL DEFAULT 'DRAFT';

-- Seed sensible times for any LIVE exam that has none, so the
-- automatic SCHEDULED->LIVE / LIVE->CLOSED transitions work.
UPDATE exams
SET start_time = COALESCE(start_time, NOW()),
    end_time   = COALESCE(end_time, DATE_ADD(NOW(), INTERVAL duration_minutes MINUTE))
WHERE status = 'LIVE';
