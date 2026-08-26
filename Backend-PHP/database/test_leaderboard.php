<?php
$BASE = 'http://127.0.0.1/Capstone-Mobile-Quiz-System/Backend-PHP/api/';
$ch = curl_init($BASE . 'login.php');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
    CURLOPT_POSTFIELDS => json_encode(['username' => 'sofia.cruz', 'password' => 'TestPass123']),
    CURLOPT_RETURNTRANSFER => true,
]);
$login = json_decode(curl_exec($ch), true);
curl_close($ch);
$token = $login['data']['session_token'];

$ch2 = curl_init($BASE . 'leaderboard.php');
curl_setopt_array($ch2, [
    CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token],
    CURLOPT_RETURNTRANSFER => true,
]);
echo json_encode(json_decode(curl_exec($ch2), true), JSON_PRETTY_PRINT);
curl_close($ch2);
