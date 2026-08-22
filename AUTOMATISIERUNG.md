# Automatisierung: POSE-Bogen → Angebotsentwurf

Roadmap-Dokument für den geplanten nächsten Ausbauschritt des [POSE-Bogens](POSE-BOGEN.md).
Hier nur Kontext und offene Punkte – nichts davon ist bereits gebaut oder angebunden.

## Zielbild

Joachim (Inhaber ERGO-PLUS) füllt den POSE-Bogen digital aus (oder lässt ihn beim Kunden vor Ort
ausfüllen), die Daten landen automatisiert in einem Faktura-Tool, daraus entsteht automatisch ein
Angebotsentwurf, er passt ihn an, und er geht an den Kunden raus.

## Ist-Zustand

Aktuell werden für Angebote/Rechnungen/Mahnungen drei Werkzeuge genutzt:

- **weclapp** (~150 €/Monat)
- eine **Zweitsoftware nur für XRechnung**, weil die weclapp-XRechnung-Anbindung bisher nicht
  gelang – XRechnung ist Pflicht für Zahlungen von Integrationsämtern.
- **Excel** für Mahnungen.

Zusätzlich zum POSE-Bogen gibt es noch einen Add-on-Bogen für Sonderfälle (liegt noch nicht vor).

## Stufen

- **Stufe 1 (fertig):** Der digitale POSE-Bogen selbst, mit maschinenlesbarem `POSE-JSON v1:`-Block
  am Ende der E-Mail.
- **Stufe 1b (fertig):** [`scripts/pose_json_lesen.py`](scripts/pose_json_lesen.py) liest diesen
  Block wieder ein und validiert ihn grob.
- **Stufe 2 (noch nicht gebaut):** Automatischer Angebotsentwurf im Faktura-System per API.
  Bewusst noch nicht angebunden – ohne verifizierten API-Zugang und echte Feldnamen des
  Zielsystems wäre eine geratene Integration gegen ein echtes Geschäftssystem ein Risiko, kein
  Fortschritt. Für Stufe 2 fehlen noch:
  - der Add-on-Bogen,
  - API-Zugang zum gewählten Faktura-System,
  - aktueller Artikel-/Preisstand,
  - Joachims Zuordnungsregeln (welche Maße → welches Modell).
- **Stufe 3 (Konzept):** Versand des vom Faktura-System erzeugten PDF an den Kunden, mit expliziter
  Freigabe durch Joachim statt vollautomatisch.

## Offene Systemfrage: weclapp vs. Lexware Office XL

Bisheriger Rechercheergebnisstand: Lexware Office XL bringt XRechnung **und** die nötige
Public API im selben Tarif mit und wäre ca. 1.400 €/Jahr günstiger als die aktuelle
Drei-Werkzeuge-Lösung – das ist aber noch nicht final entschieden.

Bei einer eventuellen Migration: alte Rechnungen **nicht** per API neu anlegen – das verstößt
gegen die Pflicht zur fortlaufenden Rechnungsnummer und gegen GoBD. Stattdessen einen
GoBD-konformen Export als Archiv verwenden.

## Datenschutz-Leitplanke

Der Bogen enthält Gesundheitsdaten (Beschwerden, Skoliose, Klinikaufenthalt). Jede künftige
Automatisierungsstufe muss diese Leitplanke respektieren: Die Verarbeitung bleibt clientseitig
bzw. lokal bei Joachim, keine zentrale Datenhaltung Dritter ohne ausdrückliche, geprüfte
Auftragsverarbeitung.
