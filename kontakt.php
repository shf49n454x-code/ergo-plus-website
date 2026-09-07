<?php
/**
 * Nimmt das Kontaktformular entgegen und schickt es per E-Mail weiter.
 *
 * Bewusst ohne CAPTCHA: die Zielgruppe ist aelter und teilweise
 * koerperlich eingeschraenkt, ein Bilderraetsel waere genau die falsche
 * Huerde. Stattdessen Honeypot, Mindest-Ausfuellzeit und eine einfache
 * Frequenzbremse.
 *
 * Antwortet immer JSON. Das Formular zeigt danach den wahren Stand an
 * statt pauschal Erfolg zu melden.
 */

declare(strict_types=1);

// ── Einstellungen ───────────────────────────────────────────────────
const EMPFAENGER      = 'info@ergo-plus.de';
// Absender bewusst identisch mit dem Empfaenger: diese Adresse existiert
// auf der Domain garantiert, also weist kein Mailserver die Nachricht
// wegen eines unbekannten Absenders ab. Antworten gehen trotzdem an den
// Besucher, dafuer sorgt das Reply-To weiter unten.
// Wer lieber ein eigenes noreply-Postfach nutzt: hier eintragen, aber
// vorher bei Strato als Postfach oder Alias anlegen.
const ABSENDER        = 'info@ergo-plus.de';
const BETREFF         = 'Beratungsanfrage ueber ergo-plus.de';
const MIN_SEKUNDEN    = 3;      // schneller ausgefuellt = maschinell
const MAX_PRO_STUNDE  = 5;      // pro Absender
const MAX_LAENGE      = 5000;   // Zeichen je Feld

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

function antwort(int $code, string $meldung, bool $ok = false): never {
    http_response_code($code);
    echo json_encode(['ok' => $ok, 'meldung' => $meldung],
                     JSON_UNESCAPED_UNICODE);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    antwort(405, 'Nur POST.');
}

// ── Eingaben einsammeln ─────────────────────────────────────────────
function feld(string $name): string {
    $wert = $_POST[$name] ?? '';
    if (!is_string($wert)) return '';
    return trim(mb_substr($wert, 0, MAX_LAENGE));
}

$vorname  = feld('first');
$nachname = feld('last');
$telefon  = feld('phone');
$email    = feld('email');
$produkt  = feld('product');
$text     = feld('message');

// ── Spamfilter ──────────────────────────────────────────────────────
// Honeypot: fuer Menschen unsichtbar, Bots fuellen ihn aus.
if (feld('website') !== '') {
    // Nicht verraten, dass es aufgefallen ist.
    antwort(200, 'Danke.', true);
}

// Mindest-Ausfuellzeit. Der Zeitstempel wird beim Laden per JavaScript
// gesetzt; fehlt er, wurde das Formular ohne Browser abgeschickt.
$geladen = (int) (feld('ts') ?: 0);
$jetzt   = (int) (microtime(true) * 1000);
if ($geladen <= 0 || ($jetzt - $geladen) < MIN_SEKUNDEN * 1000) {
    antwort(200, 'Danke.', true);
}

// Frequenzbremse. Gespeichert wird nur ein Hash der IP, nie die IP
// selbst, und die Datei wird nach einer Stunde hinfaellig.
$kennung = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . '|' . date('YmdH'));
$spur    = sys_get_temp_dir() . '/ep-kontakt-' . $kennung;
$anzahl  = is_file($spur) ? (int) file_get_contents($spur) : 0;
if ($anzahl >= MAX_PRO_STUNDE) {
    antwort(429, 'Es sind schon mehrere Anfragen von hier eingegangen. '
                 . 'Bitte rufen Sie uns an: +49 6021 12807');
}

// ── Pruefung ────────────────────────────────────────────────────────
$fehlt = [];
if ($vorname === '')  $fehlt[] = 'Vorname';
if ($nachname === '') $fehlt[] = 'Nachname';
if ($email === '')    $fehlt[] = 'E-Mail';
if ($fehlt) {
    antwort(400, 'Bitte ausfuellen: ' . implode(', ', $fehlt));
}
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    antwort(400, 'Die E-Mail-Adresse sieht nicht richtig aus.');
}

// Header-Injection: Zeilenumbrueche in Feldern, die in Kopfzeilen
// landen, wuerden fremde Empfaenger einschleusen lassen.
foreach ([$vorname, $nachname, $email] as $kopfzeilenfeld) {
    if (preg_match('/[\r\n]/', $kopfzeilenfeld)) {
        antwort(400, 'Ungueltige Eingabe.');
    }
}

// ── Mail zusammenbauen ──────────────────────────────────────────────
$name = $vorname . ' ' . $nachname;

$koerper = "Neue Beratungsanfrage ueber ergo-plus.de\n"
    . str_repeat('-', 42) . "\n\n"
    . "Name:     $name\n"
    . "E-Mail:   $email\n"
    . "Telefon:  " . ($telefon !== '' ? $telefon : '(nicht angegeben)') . "\n"
    . "Produkt:  " . ($produkt !== '' ? $produkt : '(keine Auswahl)') . "\n\n"
    . "Nachricht:\n"
    . ($text !== '' ? $text : '(keine Nachricht)') . "\n\n"
    . str_repeat('-', 42) . "\n"
    . 'Eingegangen: ' . date('d.m.Y H:i') . " Uhr\n";

$kopf = [
    'From: ERGO-PLUS Website <' . ABSENDER . '>',
    'Reply-To: ' . mb_encode_mimeheader($name, 'UTF-8') . ' <' . $email . '>',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
    'X-Mailer: ergo-plus.de',
];

$gesendet = @mail(
    EMPFAENGER,
    mb_encode_mimeheader(BETREFF, 'UTF-8'),
    $koerper,
    implode("\r\n", $kopf),
    '-f' . ABSENDER          // Envelope-Absender, wichtig fuer SPF
);

if (!$gesendet) {
    // Ehrlich bleiben: lieber die Telefonnummer nennen, als Empfang zu
    // behaupten, den es nicht gab.
    antwort(500, 'Die Nachricht konnte gerade nicht zugestellt werden. '
                 . 'Bitte rufen Sie uns an: +49 6021 12807');
}

@file_put_contents($spur, (string) ($anzahl + 1));

antwort(200, 'Ihre Anfrage ist bei uns eingegangen. Wir melden uns in der '
             . 'Regel innerhalb von 1-2 Werktagen bei Ihnen.', true);
