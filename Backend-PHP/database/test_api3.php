<?php
$BASE = 'http://127.0.0.1/Capstone-Mobile-Quiz-System/Backend-PHP/api/';

function raw_api($method, $url, $body = null, $token = null) {
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
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return "HTTP $code: $resp";
}

$loginResp = raw_api('POST', $BASE . 'login.php', ['username' => 'sofia.cruz', 'password' => 'TestPass123']);
echo "LOGIN: $loginResp\n\n";

$login = json_decode(str_replace('/^HTTP [0-9]+: /', '', $loginResp), true);
preg_match('/session_token":"([^"]+)/', $loginResp, $m);
$token = $m[1] ?? null;

echo "JOIN (9K3L6T): " . raw_api('POST', $BASE . 'classes/join.php', ['class_code' => '9K3L6T'], $token) . "\n\n";
echo "JOIN (XXXXXX): " . raw_api('POST', $BASE . 'classes/join.php', ['class_code' => 'XXXXXX'], $token) . "\n\n";
echo "SUBMIT (exam 4): " . raw_api('POST', $BASE . 'exams/submit.php', [
    'exam_id' => 4,
    'answers' => ['16'=>'B','17'=>'A','18'=>'B','19'=>'C','20'=>'B'],
    'time_used_secs' => 600
], $token) . "\n\n";
