<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$conn = new mysqli("localhost", "root3", "pS@0922648640Sp", "iot_db");

if ($conn->connect_error) {
    die(json_encode(["error" => $conn->connect_error]));
}

$hours = isset($_GET['hours']) ? intval($_GET['hours']) : 24;
$devid = isset($_GET['devid']) ? $_GET['devid'] : '';

// Build query
if ($devid) {
    $sql = "SELECT * FROM electric WHERE devid = '$devid' AND timestamp >= DATE_SUB(NOW(), INTERVAL $hours HOUR) ORDER BY timestamp ASC LIMIT 500";
} else {
    $sql = "SELECT * FROM electric WHERE timestamp >= DATE_SUB(NOW(), INTERVAL $hours HOUR) ORDER BY timestamp ASC LIMIT 500";
}

$result = $conn->query($sql);

$labels = [];
$voltage = [];
$current = [];
$pf = [];
$energy = [];
$power = [];

while ($row = $result->fetch_assoc()) {
    $labels[] = $row['timestamp'];
    $voltage[] = floatval($row['volt']);
    $current[] = floatval($row['amp']);
    $pf[] = floatval($row['pf']);
    $energy[] = floatval($row['energy']);
    $power[] = floatval($row['volt']) * floatval($row['amp']);
}

// Get latest
$sql2 = "SELECT * FROM electric ORDER BY id DESC LIMIT 1";
$latest = $conn->query($sql2)->fetch_assoc();

$data = [
    'labels' => $labels,
    'voltage' => $voltage,
    'current' => $current,
    'pf' => $pf,
    'energy' => $energy,
    'power' => $power,
    'latest' => $latest,
    'count' => count($labels)
];

$conn->close();
echo json_encode($data);
?>
