# Search-Console-Daten automatisch abholen

Einmal einrichten, danach schreibt sich die Tabelle montags von selbst
fort. Kein manueller Export mehr.

## Warum dieser Umweg

Die Search-Console-API direkt aus einer Claude-Sitzung aufzurufen geht
nicht: der Egress-Proxy dieser Umgebung lässt `googleapis.com` nicht
durch. Apps Script läuft dagegen auf Googles eigenen Servern — dort ist
der Zugriff ohnehin erlaubt. Die fertige Tabelle liegt anschließend in
Google Drive, und Drive ist als Connector verbunden.

## Einrichtung (einmalig, etwa fünf Minuten)

1. **Tabelle anlegen.** In Google Drive eine leere Google-Tabelle
   erstellen, zum Beispiel `ERGO-PLUS Search Console`.

2. **Skript öffnen.** In der Tabelle: *Erweiterungen → Apps Script*.

3. **Code einfügen.** Den Inhalt von `Code.gs` in die Datei `Code.gs`
   des Projekts kopieren (den vorhandenen Beispielcode ersetzen).

4. **Manifest sichtbar machen und ersetzen.** Links auf *Projekt­einstellungen*,
   dort **„Manifestdatei appsscript.json im Editor anzeigen"** anhaken.
   Dann im Editor `appsscript.json` öffnen und durch die Datei aus diesem
   Ordner ersetzen. Ohne diesen Schritt fehlt die Berechtigung für die
   Search Console.

5. **Property eintragen.** In `Code.gs` oben bei `CONFIG.siteUrl` den
   Wert setzen, **genau** wie in der Search Console:
   - Domain-Property → `sc-domain:ergo-plus.de`
   - URL-Property → `https://ergo-plus.de/`

   Ein falsches Präfix ist der häufigste Fehler; das Skript sagt dann
   ausdrücklich, woran es lag.

6. **Einmal starten.** Oben die Funktion `triggerEinrichten` auswählen
   und ausführen. Google fragt nach Berechtigungen — das ist der Punkt,
   an dem der Zugriff erteilt wird. Danach ist die Tabelle gefüllt und
   der wöchentliche Trigger steht.

Das ausführende Google-Konto muss in der Search Console Zugriff auf die
Property haben. Ein Konto mit der Rolle *Eingeschränkt* reicht zum Lesen.

## Was in der Tabelle steht

| Blatt | Inhalt |
|---|---|
| Suchanfragen | Wonach gesucht wurde, mit Klicks, Impressionen, CTR, Position |
| Seiten | Welche Seite wie läuft |
| Anfrage x Seite | Welche Seite für welche Anfrage rankt |
| Verlauf | Tagesverlauf über den Zeitraum |
| Stand | Property, Zeitraum, Zeitpunkt der letzten Aktualisierung |

Sortiert ist nach **Impressionen**, nicht nach Klicks. Seiten mit vielen
Impressionen und wenigen Klicks sind die eigentlichen Baustellen: sie
werden gefunden, aber nicht geklickt — dort wirkt ein besserer Titel.

## Zwei Fallstricke

**Die letzten Tage fehlen absichtlich.** Search Console hinkt zwei bis
drei Tage hinterher. Ohne `tageAuslassen` sähe das Ende jedes Zeitraums
wie ein Einbruch aus.

**Nicht aufsummieren.** Die Zeilen unter *Suchanfragen* lassen
Anfragen mit sehr wenig Volumen aus Datenschutzgründen weg. Ihre Summe
ist deshalb kleiner als die tatsächliche Gesamtzahl. Für Gesamtwerte das
Blatt *Verlauf* nehmen.

## Danach

Sag Claude einfach den Namen der Tabelle. Der Drive-Connector liest sie,
und die Auswertung läuft auf echten Zahlen statt auf Schätzungen.
