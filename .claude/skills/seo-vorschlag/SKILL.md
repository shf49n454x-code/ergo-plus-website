---
name: seo-vorschlag
description: Liest die Search-Console-Zahlen aus data/search-console/BERICHT.md und macht daraus einen konkreten Änderungsvorschlag als Entwurfs-PR — bessere Titles und Descriptions für die Seiten, die gefunden, aber nicht geklickt werden. Verwenden, wenn nach "was sagen die Zahlen", "SEO-Vorschlag", "warum klickt keiner" gefragt wird, oder wenn die wöchentliche Routine feuert.
---

# Aus Zahlen wird ein Vorschlag

Der wöchentliche Lauf holt die Search-Console-Daten ins Repo. Ohne diesen
Schritt bleiben sie dort liegen. Hier wird daraus eine Änderung, über die
Jan entscheiden kann.

**Das Ergebnis ist immer ein Entwurfs-PR. Niemals ein Merge.** Das ist
keine Höflichkeit, sondern die Regel des Projekts: Jede Produktionsänderung
läuft über Branch → PR → Prüfung → Freigabe durch Jan.

## Ablauf

### 1. Zahlen lesen

`data/search-console/BERICHT.md` und bei Bedarf `latest.json`. Zwei
Abschnitte tragen die Arbeit:

- **Viel gesehen, wenig geklickt** — die Seite wird gefunden, der
  Suchtreffer überzeugt aber nicht. Das ist ein Title-/Description-Problem,
  kein Inhaltsproblem.
- **Knapp vor Seite 1** — Position 8 bis 20. Der kürzeste Weg zu Klicks.

### 2. Prüfen, ob überhaupt genug Daten da sind

Unter **50 Impressionen** auf einer Seite ist jede Klickrate Zufall. Zwei
Klicks mehr oder weniger verschieben sie um Prozentpunkte.

Steht nichts Belastbares im Bericht: **keinen PR öffnen.** Sagen, dass die
Datenlage nicht reicht, und den Zeitraum nennen, ab dem sie es täte. Ein
PR mit erfundener Begründung ist schlechter als kein PR.

### 3. Die betroffene Seite ansehen

Erst die Datei öffnen, dann urteilen. Der Bericht nennt URLs, nicht
Dateien — `https://ergo-plus.de/blog/xyz.html` ist `blog/xyz.html`.

Konkret nachsehen:
- Steht die Suchanfrage, unter der die Seite gefunden wird, überhaupt im
  Title?
- Ist die Description länger als **etwa 155 Zeichen**? Dann schneidet
  Google sie ab, und der Satz endet im Nichts. Im Bestand gibt es
  Descriptions mit über 200 Zeichen — die sind die naheliegendsten
  Kandidaten.
- Verspricht der Title etwas anderes, als die Seite einlöst?

### 4. Vorschlag schreiben

Hausmaß, aus dem Bestand abgeleitet: **Title 32–64 Zeichen**,
**Description 120–155 Zeichen**.

Inhaltlich gilt, was für die ganze Seite gilt — `DESIGN.md` und die
Tonlage der bestehenden Texte. Die Zielgruppe sind Betroffene und
Angehörige in einer belastenden Lage, nicht Suchmaschinen. Keine
Schlagwortketten, kein „Nr. 1", keine Versprechen, die die Seite nicht
hält.

**Höchstens drei Seiten pro Lauf.** Ein PR, den Jan in fünf Minuten
gegenlesen kann, wird gelesen. Einer mit zwanzig Änderungen nicht.

### 5. Absichern

```bash
node tools/audit/audit.js
```

Muss 0 Befunde melden. Title und Description stehen im `<head>` neben
Open-Graph- und JSON-LD-Angaben — wer nur eine Stelle ändert,
hinterlässt widersprüchliche Angaben. Alle Stellen mitziehen.

### 6. Entwurfs-PR öffnen

Branch, Commit, Push, **Draft-PR**. In der Beschreibung für jede Änderung:

| | |
|---|---|
| Seite | welche Datei |
| Zahlen | Impressionen, Klicks, CTR, Position — aus dem Bericht |
| Vorher / Nachher | Title und Description im Wortlaut |
| Begründung | was an der alten Fassung die Klicks gekostet hat |

Die Zahlen kommen aus dem Bericht. **Nie schätzen, nie runden, nie
ausschmücken.** Wer hier eine Zahl erfindet, macht den ganzen Kreislauf
wertlos.

## Was dieser Kreislauf nicht kann

Er sieht nur, was Google zeigt. Ob ein Besucher am Ende anruft, steht
nirgends in diesen Daten. Eine bessere Klickrate ist ein Zwischenziel,
kein Geschäftsergebnis.

Und er wirkt erst, wenn es etwas zu messen gibt. Auf einer Seite mit einem
Klick in drei Monaten optimiert er Rauschen.
