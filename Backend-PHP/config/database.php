<?php
/**
 * Database connection helper.
 * Every endpoint calls getDbConnection() to get a PDO instance.
 */

/**
 * Align PHP's clock with the MySQL server clock.
 *
 * All exam scheduling / status logic is driven by MySQL NOW() (the "server
 * time" reference). If PHP's default timezone differs from MySQL's, then
 * date()/strtotime() produce wall-clock strings that MySQL interprets
 * differently, causing freshly scheduled/reopened exams to instantly auto-close
 * (their end_time ends up in the past). Deriving PHP's timezone from the DB
 * keeps both clocks identical so every date computation is consistent.
 */
function syncPhpTimezone(PDO $pdo): void {
    try {
        $offsetSec = (int) $pdo->query('SELECT TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW())')->fetchColumn();
        if ($offsetSec % 3600 === 0) {
            $hours = (int) ($offsetSec / 3600);
            $tz = $hours === 0
                ? 'UTC'
                : 'Etc/GMT' . ($hours > 0 ? '-' . $hours : '+' . abs($hours));
            date_default_timezone_set($tz);
        }
    } catch (Exception $e) {
        // Non-whole-hour offsets keep the default timezone.
    }
}

function getDbConnection(): PDO {
    $host = '127.0.0.1';
    $port = '3306';
    $dbname = 'quiz_system';
    $username = 'root';
    $password = ''; // default XAMPP MySQL has no root password

    $dsn = "mysql:host=$host;port=$port;dbname=$dbname;charset=utf8mb4";

    try {
        $pdo = new PDO($dsn, $username, $password, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        syncPhpTimezone($pdo);
        return $pdo;
    } catch (PDOException $e) {
        http_response_code(500);
        header('Content-Type: application/json');
        echo json_encode([
            'success' => false,
            'error' => 'Database connection failed.',
            'code' => 'DB_CONNECTION_ERROR',
        ]);
        exit;
    }
}