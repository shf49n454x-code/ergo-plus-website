<?php
// Kopieren nach einstellungen-lokal.php (nur auf dem Server, nie ins Repo).
// Token erzeugen und Hash eintragen:  python3 tools/konfigurator/buero.py token
define('TOKEN_SHA256', 'HIER-SHA256-DES-TOKENS');
define('BREMSE_SALZ', 'HIER-ZUFALLSWERT');
// Strato: Ordner neben dem Web-Verzeichnis, z. B. dirname(__DIR__, 2) . '/ergo-postfach'
// define('POSTFACH_PFAD', dirname(__DIR__, 2) . '/ergo-postfach');
