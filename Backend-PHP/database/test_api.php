<?php
// Test script: tests API endpoints
// Run: php test_api.php

$BASE = 'http://127.0.0.1/Capstone-Mobile-Quiz-System/Backend-PHP/api/';

function api($method, $url, $body = null, $token = null) {
    $ch = curl_init($url);
    $headers = ['Content-Type: application/json'];
    if ($token) $headers[] = "Authorization: Bearer $token";
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 10,
    ]);
    if ($body !== null) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body));
    }
    $resp = curl_exec($ch);
    curl_close($ch);
    return json_decode($resp, true);
}

echo "=== LOGIN (sofia.cruz) ===\n";
$login = api('POST', $BASE . 'login.php', ['username' => 'sofia.cruz', 'password' => 'TestPass123']);
echo json_encode($login, JSON_PRETTY_PRINT) . "\n\n";

$token = $login['data']['session_token'] ?? null;

echo "=== GET classes ===\n";
$classes = api('GET', $BASE . 'classes.php', null, $token);
echo json_encode($classes, JSON_PRETTY_PRINT) . "\n\n";

echo "=== GET class_detail?id=1 ===\n";
$detail = api('GET', $BASE . 'class_detail.php?id=1', null, $token);
echo json_encode($detail, JSON_PRETTY_PRINT) . "\n\n";

echo "=== GET exams ===\n";
$exams = api('GET', $BASE . 'exams.php', null, $token);
echo json_encode($exams, JSON_PRETTY_PRINT) . "\n\n";

echo "=== GET exam_questions?id=1 ===\n";
$questions = api('GET', $BASE . 'exam_questions.php?id=1', null, $token);
echo json_encode($questions, JSON_PRETTY_PRINT) . "\n\n";

echo "=== GET results ===\n";
$results = api('GET', $BASE . 'results.php', null, $token);
echo json_encode($results, JSON_PRETTY_PRINT) . "\n\n";

echo "=== GET profile ===\n";
$profile = api('GET', $BASE . 'profile.php', null, $token);
echo json_encode($profile, JSON_PRETTY_PRINT) . "\n\n";

echo "=== POST join class (code: 2H5N7R) ===\n";
$join = api('POST', $BASE . 'classes/join.php', ['class_code' => '2H5N7R'], $token);
echo json_encode($join, JSON_PRETTY_PRINT) . "\n\n";

echo "All tests done!\n";
