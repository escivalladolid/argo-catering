<?php
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
    if ($body !== null) curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body));
    $resp = curl_exec($ch);
    curl_close($ch);
    return json_decode($resp, true);
}

$login = api('POST', $BASE . 'login.php', ['username' => 'sofia.cruz', 'password' => 'TestPass123']);
$token = $login['data']['session_token'];

echo "=== JOIN CLASS (code: 9K3L6T - class she's not in) ===\n";
$join = api('POST', $BASE . 'classes/join.php', ['class_code' => '9K3L6T'], $token);
echo json_encode($join, JSON_PRETTY_PRINT) . "\n\n";

echo "=== JOIN CLASS again (should say already enrolled) ===\n";
$join2 = api('POST', $BASE . 'classes/join.php', ['class_code' => '9K3L6T'], $token);
echo json_encode($join2, JSON_PRETTY_PRINT) . "\n\n";

echo "=== JOIN CLASS (bad code) ===\n";
$join3 = api('POST', $BASE . 'classes/join.php', ['class_code' => 'XXXXXX'], $token);
echo json_encode($join3, JSON_PRETTY_PRINT) . "\n\n";

echo "=== SUBMIT EXAM (exam 1 - Midterm) ===\n";
$submit = api('POST', $BASE . 'exams/submit.php', [
    'exam_id' => 1,
    'answers' => ['1'=>'A','2'=>'B','3'=>'C','4'=>'B','5'=>'C','6'=>'C','7'=>'B','8'=>'B','9'=>'B','10'=>'C'],
    'time_used_secs' => 1200
], $token);
echo json_encode($submit, JSON_PRETTY_PRINT) . "\n\n";

echo "=== SUBMIT EXAM again (should say already submitted) ===\n";
$submit2 = api('POST', $BASE . 'exams/submit.php', [
    'exam_id' => 1,
    'answers' => ['1'=>'A'],
    'time_used_secs' => 60
], $token);
echo json_encode($submit2, JSON_PRETTY_PRINT) . "\n\n";

echo "=== RESULTS after submission ===\n";
$results = api('GET', $BASE . 'results.php', null, $token);
echo json_encode($results, JSON_PRETTY_PRINT) . "\n";
