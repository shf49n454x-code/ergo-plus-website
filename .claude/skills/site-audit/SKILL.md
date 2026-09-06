---
name: site-audit
description: Prüft die ERGO-PLUS-Website auf Barrierefreiheit, Ladeverhalten und strukturelle Fehler. Verwenden vor jedem Merge, nach jedem Design- oder Content-Eingriff und bei jeder geplanten Kontrolle. Auch dann aufrufen, wenn nach "Performance", "Ladezeit", "Barrierefreiheit", "WCAG", "Core Web Vitals" oder "läuft die Seite noch sauber" gefragt wird.
---

# Site-Audit

Ein Werkzeug, ein Aufruf, harte Schwellen. Nicht schätzen — messen.

```bash
node tools/audit/audit.js            # alles (Standard)
node tools/audit/audit.js --static   # ohne Browser, sehr schnell
node tools/audit/audit.js --json     # Maschinenausgabe
```

Beendet sich mit Code 1, sobald eine Schwelle gerissen wird. Genau so
gehört es in eine Prüfung vor dem Merge.

## Voraussetzungen

`axe-core` muss vorhanden sein, sonst bleibt die Barrierefreiheit
ungeprüft (das Werkzeug sagt das dann auch):

```bash
npm install
```

Playwright wird unter `/opt/node22/lib/node_modules/playwright` gesucht,
danach im normalen Auflösungspfad. Chromium unter `/opt/pw-browsers/chromium`,
sonst der Standardbrowser von Playwright. Fehlt beides, laufen nur die
strukturellen Prüfungen — der Rest wird übersprungen, nicht stillschweigend
als bestanden gemeldet.

## Was geprüft wird

| Prüfung | Schwelle | Warum |
|---|---|---|
| axe-core | 0 Verstöße | Die Zielgruppe hat körperliche Einschränkungen. Ein Verstoß hier trifft genau die Menschen, für die die Seite existiert. |
| LCP | ≤ 2500 ms | Core Web Vitals "gut" |
| CLS | ≤ 0,1 | Core Web Vitals "gut" |
| Seitengewicht | 400 KB Start, 600 KB Blogübersicht, sonst 350 KB | Zielgruppe surft oft mobil und nicht auf Glasfaser |
| Tote interne Links | 0 | |
| Fehlende Assets | 0 | inklusive aller `srcset`-Kandidaten |
| Undefinierte CSS-Variablen | 0 | `var(--x)` ohne Definition fällt still aus — genau so ist hier schon einmal eine Kontrastkorrektur wirkungslos geblieben |
| Uneinheitliche Telefonnummern | genau 1 Ziel | siehe unten |
| Doppeltes Titelbild in der Blog-Übersicht | 0 | siehe unten |
| Google Fonts extern | keine | siehe unten |

## Zwei Regeln, die aus echten Fehlern stammen

**Telefonnummer.** Auf der Startseite stand `tel:+4960211280` — die letzte
Ziffer fehlte. Das war der einzige Telefonlink der Startseite und damit
das Ende praktisch jedes Weges durch die Seite. Zwei weitere Seiten hatten
eigene Varianten. Richtig ist `+49 6021 12807` (Impressum, JSON-LD).
Das Audit besteht nur, wenn **alle** `tel:`-Links auf dasselbe Ziel zeigen.

**Doppelte Titelbilder.** Zwei Karten mit demselben Foto fallen sofort
auf. Das Raster ist je nach Fensterbreite 3-, 2- oder einspaltig
(Breakpoints 960 px und 600 px), deshalb reicht es nicht, die beiden
Karten im Quelltext auseinanderzuziehen: Position 2 und 5 stehen bei drei
Spalten direkt untereinander in derselben Spalte. Das Audit meldet jedes
mehrfach verwendete Kartenbild — die Lösung ist ein eigenes Bild, nicht
eine andere Reihenfolge.

**Schriften.** Figtree und Noto Sans liegen unter `assets/fonts` und werden
über `assets/fonts/fonts.css` geladen. Nicht auf Google Fonts zurückbauen:
der externe Stylesheet-Link blockiert das Rendering (gemessener FCP bei
nicht erreichbarem CDN: 12,6 s) und baut eine Verbindung zu einem
Drittanbieter auf, die die Datenschutzerklärung so nicht mehr beschreibt.

## Vor Änderungen an Farben

Erst `DESIGN.md` lesen. Die dort dokumentierten Paarungen sind auf WCAG AA
geprüft; die Tabelle nennt zu jedem Token, worauf es liegen darf.
Faustregeln aus der Messung:

- `--c-teal` (#148f77) trägt **kein** Weiß (4,0:1). Für weiße Schrift
  `--c-teal-dk` nehmen.
- `--c-amber` (#d68910) trägt **kein** Weiß (2,8:1). Als Fläche mit
  dunkler Schrift (`--c-text`) kombinieren, dann stimmt es (5,2:1).
- Teal als **Schrift** auf hellem Teal-Untergrund braucht `--c-teal-dkr`
  (#0d6350); `--c-teal-dk` reicht dort knapp nicht.

## Fallstrick beim Messen

Der Cookie-Banner erscheint verzögert. Wer axe sofort nach `load` laufen
lässt, misst ihn nicht mit — so sind zwei Kontrastfehler eine Weile
unentdeckt geblieben. `tools/audit/audit.js` wartet deshalb, bevor es
prüft. Kein eigenes, schnelleres Skript danebenstellen.

## Was das Audit nicht kann

Es misst lokal, ohne Netzlatenz und ohne echte Endgeräte. Es sagt nichts
über Rankings, Inhalte oder darüber, ob das Kontaktformular tatsächlich
jemanden erreicht. Für die inhaltliche Seite gibt es `SEO-FIBEL.md`.
