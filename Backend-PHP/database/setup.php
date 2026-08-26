<?php
/**
 * Run this once to set up the database.
 * Access via browser: http://localhost/Capstone-Mobile-Quiz-System/Backend-PHP/database/setup.php
 * Or run from CLI: php setup.php
 */

$sqlFile = __DIR__ . '/schema.sql';
$sql = file_get_contents($sqlFile);

if ($sql === false) {
    die("ERROR: Could not read schema.sql\n");
}

try {
    $dsn = "mysql:host=127.0.0.1;port=3306;charset=utf8mb4";
    $pdo = new PDO($dsn, 'root', '', [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    ]);

    $pdo->exec("CREATE DATABASE IF NOT EXISTS quiz_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
    $pdo->exec("USE quiz_system");

    // Split by semicolons and execute each statement
    $statements = array_filter(
        array_map('trim', explode(';', $sql)),
        fn($s) => !empty($s) && !str_starts_with($s, '--')
    );

    $executed = 0;
    foreach ($statements as $stmt) {
        $clean = trim($stmt);
        if (!empty($clean)) {
            try {
                $pdo->exec($clean);
                $executed++;
            } catch (PDOException $e) {
                // Skip duplicate key errors from INSERT IGNORE
                if ($e->getCode() != 23000) {
                    echo "WARNING: " . $e->getMessage() . "\n";
                }
            }
        }
    }

    echo "SUCCESS: Executed $executed SQL statements.\n";
    echo "Database 'quiz_system' is ready.\n\n";
    echo "Test accounts (password: TestPass123):\n";
    echo "  Student: sofia.cruz / TestPass123\n";
    echo "  Student: miguel.reyes / TestPass123\n";
    echo "  Student: ana.garcia / TestPass123\n";
    echo "  Teacher: prof.domingo / TestPass123\n";

} catch (PDOException $e) {
    die("ERROR: " . $e->getMessage() . "\n");
}
