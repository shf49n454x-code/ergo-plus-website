<?php
/**
 * Gemeinsame Einstellungen für eingang.php und postfach.php.
 * Geheimes (Token-Hash, Salz, Speicherort) gehört in einstellungen-lokal.php –
 * diese Datei liegt nur auf dem Server und nicht im Repo (.gitignore).
 * Vorlage: einstellungen-lokal.beispiel.php
 */
declare(strict_types=1);
if (is_file(__DIR__ . '/einstellungen-lokal.php')) require __DIR__ . '/einstellungen-lokal.php';

defined('TOKEN_SHA256')   || define('TOKEN_SHA256', '');          // sha256 des Abhol-Tokens
defined('BREMSE_SALZ')    || define('BREMSE_SALZ', 'bitte-in-einstellungen-lokal-setzen');
defined('MAX_BYTES')      || define('MAX_BYTES', 25 * 1048576);    // 10 Fotos à ~1,6 MB + Daten
defined('MAX_PRO_STUNDE') || define('MAX_PRO_STUNDE', 40);
// Möglichst AUSSERHALB des Web-Verzeichnisses ablegen. Fallback: api/postfach/ (per .htaccess gesperrt).
defined('POSTFACH_PFAD')  || define('POSTFACH_PFAD', __DIR__ . '/postfach');

function postfach(): string {
    $p = POSTFACH_PFAD;
    if (!is_dir($p)) {
        @mkdir($p, 0700, true);
        @file_put_contents($p . '/.htaccess', "Require all denied\nDeny from all\n");
    }
    return $p;
}
