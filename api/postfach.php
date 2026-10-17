<?php
/**
 * Abholstelle für das Büro: listet, liefert und löscht verschlüsselte Vorgänge.
 * Zugriff nur mit Bearer-Token (Hash steht in einstellungen-lokal.php, Token
 * selbst nur im Büro). Auch hier: nur Chiffretext, der Server kann nichts lesen.
 *
 *   GET    /api/postfach.php            → Liste
 *   GET    /api/postfach.php?id=…       → ein Umschlag
 *   DELETE /api/postfach.php?id=…       → nach erfolgreichem Import löschen
 */
declare(strict_types=1);
require __DIR__ . '/einstellungen.php';

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

function antwort(int $code, array $daten): never {
    http_response_code($code);
    echo json_encode($daten, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (TOKEN_SHA256 === '') antwort(503, ['ok' => false, 'meldung' => 'Abholung nicht eingerichtet (TOKEN_SHA256 fehlt).']);
$kopf = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
if (!preg_match('/^Bearer\s+(\S+)$/', $kopf, $m) || !hash_equals(TOKEN_SHA256, hash('sha256', $m[1]))) {
    usleep(300000);
    antwort(401, ['ok' => false, 'meldung' => 'Nicht berechtigt.']);
}

$id = (string)($_GET['id'] ?? '');
if ($id !== '' && !preg_match('/^[A-Za-z0-9-]{8,64}$/', $id)) antwort(400, ['ok' => false, 'meldung' => 'Ungültige ID.']);
$datei = $id !== '' ? postfach() . '/' . $id . '.json' : '';
$methode = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($methode === 'GET' && $id === '') {
    $liste = [];
    foreach (glob(postfach() . '/*.json') ?: [] as $f) {
        $liste[] = ['id' => basename($f, '.json'), 'bytes' => filesize($f), 'eingang' => gmdate('c', filemtime($f))];
    }
    usort($liste, fn($a, $b) => strcmp($a['eingang'], $b['eingang']));
    antwort(200, ['ok' => true, 'vorgaenge' => $liste, 'server_zeit' => gmdate('c')]);
}
if (!is_file($datei)) antwort(404, ['ok' => false, 'meldung' => 'Nicht vorhanden.']);
if ($methode === 'GET') {
    header('Content-Length: ' . filesize($datei));
    readfile($datei);
    exit;
}
if ($methode === 'DELETE') {
    antwort(unlink($datei) ? 200 : 500, ['ok' => true, 'geloescht' => $id]);
}
antwort(405, ['ok' => false, 'meldung' => 'Methode nicht erlaubt.']);
