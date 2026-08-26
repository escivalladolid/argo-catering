# Quiz System — Backend API Reference

PHP backend under `Backend-PHP/api/`. All endpoints return JSON.

## Base URL

| Context | URL |
|---|---|
| PC (browser/curl) | `http://127.0.0.1/Capstone-Mobile-Quiz-System/Backend-PHP/api/` |
| Android app (via `adb reverse tcp:8080 tcp:80`) | `http://127.0.0.1:8080/Capstone-Mobile-Quiz-System/Backend-PHP/api/` |

## Authentication

- Login first to get a session token.
- Send it on every request:

```
Authorization: Bearer <token>
```

- Roles enforced per endpoint: `STUDENT` and/or `TEACHER`.

## Response envelope

Success:

```json
{ "success": true, "data": { ... } }
```

Error:

```json
{ "success": false, "error": "message", "code": "ERROR_CODE" }
```

Common codes: `UNAUTHORIZED`, `SESSION_EXPIRED`, `FORBIDDEN`, `NOT_FOUND`,
`METHOD_NOT_ALLOWED`, `INVALID_JSON`, `MISSING_FIELDS`, `INVALID_ID`,
`NOT_ENROLLED`, `EXAM_NOT_OPEN`, `EXAM_CLOSED`, `ALREADY_SUBMITTED`.

POST bodies are raw JSON (`Content-Type: application/json`).

---

## Auth & Account

| Method | Endpoint | Role | Body / params |
|---|---|---|---|
| POST | `login.php` | public | `username` **or** `email`, `password` → returns user + `token` |
| POST | `forgot_password.php` | public | `email` |
| GET  | `profile.php` | STUDENT | — |
| GET  | `teacher/profile.php` | TEACHER | — |
| POST | `teacher/change_password.php` | TEACHER | `current_password`, `new_password` |
| POST | `teacher/update_profile.php` | TEACHER | `first_name`?, `last_name`?, `email`? |

---

## Student

| Method | Endpoint | Role | Body / params |
|---|---|---|---|
| GET  | `classes.php` | STUDENT | — |
| GET  | `class_detail.php` | STUDENT | `?id=` class id |
| POST | `classes/join.php` | STUDENT | `class_code` |
| GET  | `exams.php` | STUDENT | — |
| GET  | `results.php` | STUDENT | `?exam_id=` |
| GET  | `leaderboard.php` | STUDENT | — |

---

## Exam taking (STUDENT)

| Method | Endpoint | Body / params | Description |
|---|---|---|---|
| POST | `exam_start.php` | `exam_id` | Starts/validates the attempt; returns `time_started`, `deadline` (server-local time). |
| GET  | `exam_questions.php` | `?id=` exam id | Returns `exam`, `questions[]`, `submitted`, `previous_answers`, `score`. On resume it pre-fills each question's `student_answer` from the submission or from auto-saved temp answers. |
| POST | `exam_save_answer.php` | `exam_id`, `question_id`, `answer` | Auto-saves one answer into `exam_temp_answers` (upsert by exam+student). Rejected with `EXAM_CLOSED` once the exam closes. |
| POST | `exam_record_exit.php` | `exam_id` | Records a screen-switch / tab-switch for anti-cheating. |
| POST | `exams/submit.php` | `exam_id`, `answers` (object `{question_id: answer}`), `time_used_secs`?, `exit_attempts`?, `auto_submitted`? | Grades the attempt and stores the submission. Idempotent: resubmitting returns the existing result with `already_submitted: true`. |

`exam_questions.php` question object (note: `correct_answer` is never exposed):

```json
{
  "question_id": 31,
  "question_text": "...",
  "question_type": "MC",           // MC | TF | ID | ENUM
  "options": ["opt A", "opt B"],   // null for ID/ENUM
  "points": 1,
  "answer_matching": "EXACT",
  "student_answer": "opt A"        // only when resuming with saved answers
}
```

---

## Teacher

| Method | Endpoint | Body / params |
|---|---|---|
| GET  | `teacher/classes.php` | — |
| GET  | `teacher/class_detail.php` | `?id=` class id |
| POST | `teacher/create_class.php` | `subject_name`, `subject_code`, `block` |
| POST | `teacher/update_class.php` | `class_id`, `subject_name`?, `subject_code`?, `block`? |
| POST | `teacher/delete_class.php` | `class_id` |
| POST | `teacher/archive_class.php` | `class_id` |
| GET  | `teacher/exams.php` | — |
| GET  | `teacher/all_exams.php` | — |
| GET  | `teacher/exam_detail.php` | `?id=` exam id |
| POST | `teacher/create_exam.php` | `class_id`, `exam_name`, `duration_minutes`, `passing_score` (+ questions, schedule fields) |
| POST | `teacher/update_exam.php` | `exam_id`, `questions`?, `status`?, `start_time`?, `end_time`?, `randomize_questions`?, `randomize_options`? |
| POST | `teacher/update_exam_status.php` | `exam_id`, `status` |
| POST | `teacher/close_exam.php` | `exam_id` |
| POST | `teacher/delete_exam.php` | `exam_id` |
| POST | `teacher/update_exit_attempts.php` | `exam_id`, `max_exit_attempts` |
| POST | `teacher/import_questions.php` | `exam_id`, `questions` (array) |
| POST | `teacher/update_question.php` | `question_id`, `question_text`?, `question_type`?, `options`?, `correct_answer`?, `points`?, `answer_matching`? |
| POST | `teacher/delete_question.php` | `question_id` |
| GET  | `teacher/check_exam_activity.php` | `?id=` exam id |
| GET  | `teacher/live_monitoring.php` | `?id=` exam id |
| GET  | `teacher/exam_review.php` | `?exam_id=` `?student_id=` |
| GET  | `teacher/reports.php` | `?id=` class id |
| GET  | `teacher/analytics.php` | `?id=` class id |
| GET  | `teacher/reports_analytics.php` | `?class_id=` `?exam_id=` |

### Question types

Stored as full ENUM words in the DB: `MULTIPLE_CHOICE`, `TRUE_FALSE`,
`IDENTIFICATION`, `ENUMERATION`. The API normalizes them to short forms:
`MC`, `TF`, `ID`, `ENUM`.

---

## Notes

- `answers` in `exams/submit.php` is an object keyed by question id
  (string keys), e.g. `{"31": "go die", "34": "True"}`. Single-letter MC
  answers (`"B"`) are resolved to option text during grading/review via
  `resolveOptionLetter()`.
- Auto-saved temp answers live in `exam_temp_answers` (keyed by exam+user)
  and are merged back into `exam_questions.php` responses so an interrupted
  attempt can be resumed.
