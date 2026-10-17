<?php
/**
 * Nimmt verschlüsselte Vorgänge aus dem Konfigurator (/konfigurator/) entgegen.
 *
 * Der Server sieht nur Chiffretext: Die Daten werden im Browser mit dem
 * öffentlichen Schlüssel von ERGO-PLUS verschlüsselt, entschlüsseln kann
 * nur das Büro (tools/konfigurator/buero.py). Hier wird nichts gelesen,
 * nichts gemailt, nichts geloggt außer Größe und Zeitpunkt.
 *
 * Wiederholte Sendungen derselben ID (Tablet hatte kurz Netz) sind harmlos:
 * die Antwort ist „ok", gespeichert wird nur einmal.
 */
declare(strict_types=1);
require __DIR__ . '/einstellungen.php';

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

function antwort(int $code, string $meldung, array $extra = []): never {
    http_response_code($code);
    echo json_encode(['ok' => $code < 300, 'meldung' => $meldung] + $extra, JSON_UNESCAPED_UNICODE);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') antwort(405, 'Nur POST.');
$laenge = (int)($_SERVER['CONTENT_LENGTH'] ?? 0);
if ($laenge <= 0) antwort(400, 'Leere Anfrage.');
if ($laenge > MAX_BYTES) antwort(413, 'Vorgang zu groß (max. ' . intdiv(MAX_BYTES, 1048576) . ' MB). Bitte weniger Fotos anhängen.');

// ── Frequenzbremse pro Absender (gehashte IP, nichts Klartextiges) ──
$bremse = postfach() . '/.bremse';
if (!is_dir($bremse)) @mkdir($bremse, 0700, true);
$ipHash = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . BREMSE_SALZ);
$bremsDatei = $bremse . '/' . substr($ipHash, 0, 32);
$jetzt = time();
$zeiten = array_filter(
    is_file($bremsDatei) ? array_map('intval', file($bremsDatei, FILE_IGNORE_NEW_LINES) ?: []) : [],
    fn($t) => $t > $jetzt - 3600
);
if (count($zeiten) >= MAX_PRO_STUNDE) antwort(429, 'Zu viele Sendungen. Bitte später erneut versuchen.');

$roh = file_get_contents('php://input', false, null, 0, MAX_BYTES + 1);
if ($roh === false || strlen($roh) > MAX_BYTES) antwort(413, 'Vorgang zu groß.');
$u = json_decode($roh, true);
if (!is_array($u)) antwort(400, 'Ungültiges Format.');

// ── Umschlag prüfen: nur Form, nie Inhalt ──
$b64 = '/^[A-Za-z0-9+\/]+={0,2}$/';
if (($u['format'] ?? '') !== 'ergo-umschlag/1') antwort(400, 'Unbekanntes Format.');
if (($u['alg'] ?? '') !== 'RSA-OAEP-256+A256GCM') antwort(400, 'Unbekanntes Verfahren.');
$id = (string)($u['id'] ?? '');
if (!preg_match('/^[A-Za-z0-9-]{8,64}$/', $id)) antwort(400, 'Ungültige ID.');
if (!preg_match('/^[A-Z0-9-]{4,40}$/', (string)($u['vorgang'] ?? ''))) antwort(400, 'Ungültige Vorgangsnummer.');
if (!in_array($u['modus'] ?? '', ['berater', 'kunde'], true)) antwort(400, 'Ungültiger Modus.');
foreach (['schluessel', 'iv', 'daten'] as $k) {
    if (!is_string($u[$k] ?? null) || !preg_match($b64, $u[$k])) antwort(400, 'Feld ' . $k . ' ungültig.');
}
if (strlen(base64_decode($u['iv'], true) ?: '') !== 12) antwort(400, 'IV ungültig.');
$wrapped = strlen(base64_decode($u['schluessel'], true) ?: '');
if ($wrapped < 256 || $wrapped > 1024) antwort(400, 'Schlüssel ungültig.');

$ziel = postfach() . '/' . $id . '.json';
if (is_file($ziel)) antwort(200, 'Bereits angekommen.', ['id' => $id, 'wiederholt' => true]);

$tmp = $ziel . '.' . bin2hex(random_bytes(4)) . '.tmp';
$sauber = json_encode([
    'format' => $u['format'], 'alg' => $u['alg'], 'kid' => (string)($u['kid'] ?? ''),
    'id' => $id, 'vorgang' => $u['vorgang'], 'modus' => $u['modus'],
    'erstellt' => (string)($u['erstellt'] ?? ''), 'eingang' => gmdate('c'),
    'schluessel' => $u['schluessel'], 'iv' => $u['iv'], 'daten' => $u['daten'],
], JSON_UNESCAPED_SLASHES);
if (file_put_contents($tmp, $sauber, LOCK_EX) === false || !rename($tmp, $ziel)) {
    @unlink($tmp);
    antwort(500, 'Speichern fehlgeschlagen. Das Tablet versucht es automatisch erneut.');
}
@chmod($ziel, 0600);
$zeiten[] = $jetzt;
@file_put_contents($bremsDatei, implode("\n", $zeiten), LOCK_EX);

antwort(201, 'Angekommen.', ['id' => $id]);
