<?php
$pdo = new PDO('mysql:host=127.0.0.1;dbname=quiz_system', 'root', '');

// Add start_time and end_time
$pdo->exec("ALTER TABLE exams ADD COLUMN IF NOT EXISTS start_time DATETIME DEFAULT NULL AFTER duration_minutes");
$pdo->exec("ALTER TABLE exams ADD COLUMN IF NOT EXISTS end_time DATETIME DEFAULT NULL AFTER start_time");

// Backfill existing rows: start_time = created_at, end_time = created_at + duration_minutes
$pdo->exec("UPDATE exams SET start_time = created_at WHERE start_time IS NULL");
$pdo->exec("UPDATE exams SET end_time = DATE_ADD(created_at, INTERVAL duration_minutes MINUTE) WHERE end_time IS NULL");

echo "OK";
