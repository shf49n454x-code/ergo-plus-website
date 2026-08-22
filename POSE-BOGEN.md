# POSE-Bogen

Digitaler Ersatz für den papierenen POSE-Bogen (Persönlicher-Office-Sitz-Ergebnisbogen) –
das Kundenaufnahmeformular für die individuelle Sitzberatung bei ERGO-PLUS.

- **Seite:** [`pose-bogen.html`](pose-bogen.html)
- **Lese-Skript für die E-Mail-Antwort:** [`scripts/pose_json_lesen.py`](scripts/pose_json_lesen.py)

## Warum eine reine Client-Seite ohne Backend

Der Bogen erfasst Gesundheitsdaten (Beschwerden, diagnostizierte Skoliose, Klinikaufenthalte).
Damit diese Daten nirgends zentral gespeichert werden, ist die Seite bewusst als reine
Browser-Anwendung gebaut – ohne Server, ohne Datenbank, ohne Analytics/Tracking:

- Alle Eingaben bleiben ausschließlich im Browser des Geräts, auf dem der Bogen ausgefüllt wird.
- Der Entwurf wird automatisch in `localStorage` zwischengespeichert, damit nichts verloren geht,
  falls der Tab versehentlich geschlossen wird – auch das verlässt das Gerät nicht.
- Übertragen wird nur, wenn die Nutzerin/der Nutzer aktiv auf „Per E-Mail senden“ tippt; das öffnet
  lediglich das lokale E-Mail-Programm mit einem vorausgefüllten Entwurf an `info@ergo-plus.de` –
  der eigentliche Versand erfolgt dort, nicht durch die Website.
- Die Seite bindet bewusst keine Analytics-/Tracking-Skripte der Website ein (z. B. kein GA4), damit
  keine Formulardaten unbeabsichtigt mitgeschnitten werden.

## Funktionen

- Adressen (Privat- und Lieferadresse), Zeitaufteilung am Arbeitsplatz, Beschwerden & Gesundheit,
  Körpermaße A–H mit Skizze, Fußbodenoberfläche, gewünschte Polsterfarbe.
- Datum wird automatisch mit dem heutigen Tag vorbelegt.
- Live-Warnung, falls die Prozentangaben zur Zeitaufteilung nicht 100 % ergeben.
- Automatische Entwurf-Zwischenspeicherung und -Wiederherstellung über `localStorage`.
- Druckansicht als A4-Blatt (Browser-Druckdialog → als PDF speichern).
- E-Mail-Entwurf per `mailto:` an `info@ergo-plus.de`, inklusive eines maschinenlesbaren
  `POSE-JSON v1: {...}`-Blocks am Ende der Mail (siehe [`AUTOMATISIERUNG.md`](AUTOMATISIERUNG.md)).
- Sichern/Laden des ausgefüllten Bogens als `.json`-Datei (z. B. um an einem anderen Gerät
  weiterzuarbeiten).

## Den POSE-JSON-Block wieder einlesen

```bash
python3 scripts/pose_json_lesen.py < mail.txt
python3 scripts/pose_json_lesen.py POSE_Mustermann_2026-08-20.json
```

Das Skript findet den `POSE-JSON v1: {...}`-Block, prüft ihn grob auf Plausibilität
(z. B. Prozentsumme, bekannte Felder) und gibt die Daten strukturiert aus.

## Roadmap

Der geplante nächste Schritt – automatischer Angebotsentwurf im Faktura-System – ist in
[`AUTOMATISIERUNG.md`](AUTOMATISIERUNG.md) dokumentiert.
