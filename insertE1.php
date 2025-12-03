<?php
/**
 * insertE1.php - Insert PZEM data from ESP32 into MySQL
 * URL: insertE1.php?devid=e089&mcid=m-001&amp=0.000&volt=234.1&pf=0.00&energy=0.24
 */

// Database configuration
$db_host = "localhost";
$db_user = "root3"; //change to your user
$db_pass = "pS@0922648640Sp"; //change to your pass
$db_name = "iot_db"; //change to your database

// Get parameters from URL
$devid  = isset($_GET['devid'])  ? $_GET['devid']        : '';
$mcid   = isset($_GET['mcid'])   ? $_GET['mcid']         : '';
$amp    = isset($_GET['amp'])    ? floatval($_GET['amp'])    : 0;
$volt   = isset($_GET['volt'])   ? floatval($_GET['volt'])   : 0;
$pf     = isset($_GET['pf'])     ? floatval($_GET['pf'])     : 0;
$energy = isset($_GET['energy']) ? floatval($_GET['energy']) : 0;

// Validate required fields
if (empty($devid) || empty($mcid)) {
    echo "Error: devid and mcid are required";
    exit;
}

// Connect to database
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);

// Check connection
if ($conn->connect_error) {
    echo "Connection failed: " . $conn->connect_error;
    exit;
}

// Prepare and execute insert statement
$sql = "INSERT INTO electric (devid, mcid, amp, volt, pf, energy) 
        VALUES (?, ?, ?, ?, ?, ?)";

$stmt = $conn->prepare($sql);
$stmt->bind_param("ssdddd", $devid, $mcid, $amp, $volt, $pf, $energy);

if ($stmt->execute()) {
    echo "OK";
} else {
    echo "Error: " . $stmt->error;
}

$stmt->close();
$conn->close();
?>
