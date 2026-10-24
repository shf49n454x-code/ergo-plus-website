# Search-Console-Daten automatisch abholen

Ein Service Account holt die Zahlen woechentlich direkt von Google, die
GitHub Action legt sie im Repo ab. Kein manueller Export, kein Connector
dazwischen.

Ergebnis nach jedem Lauf:

| Datei | Inhalt |
|---|---|
| `data/search-console/latest.json` | alle Dimensionen, maschinenlesbar |
| `data/search-console/BERICHT.md` | die Auffaelligkeiten in Textform |
| `data/search-console/index.json`, `INDEX.md` | je Adresse der Sitemap: im Index ja/nein, Googles Begruendung, letzter Crawl, Canonical |

## Warum dieser Weg

Die Search-Console-API direkt aus einer Claude-Sitzung aufzurufen geht
nicht: der Egress-Proxy laesst `googleapis.com` nicht durch. GitHub
Actions hat diese Einschraenkung nicht.

Der Vorteil gegenueber einem Export in eine Google-Tabelle: die Daten
liegen **im Repo**, neben dem Code. Claude liest sie in jeder Sitzung
direkt, ohne Umweg.

## Einrichtung (einmalig)

### 1. Service Account

Falls schon einer existiert — etwa aus einem anderen Projekt —
**diesen wiederverwenden**. Dann entfaellt dieser Schritt und es bleibt
nur Schritt 2.

Sonst in der [Google Cloud Console](https://console.cloud.google.com):

1. Projekt anlegen (oder ein bestehendes waehlen)
2. *APIs & Dienste → Bibliothek* → **Google Search Console API** aktivieren
3. *IAM → Dienstkonten* → Dienstkonto erstellen
4. Beim Dienstkonto: *Schluessel → Schluessel hinzufuegen → JSON*

Die JSON-Datei enthaelt einen privaten Schluessel. Sie gehoert **nicht**
ins Repo und nicht in einen Chat — nur in das GitHub-Secret aus Schritt 3.

### 2. Service Account in der Search Console eintragen

Search Console → *Einstellungen → Nutzer und Berechtigungen → Nutzer
hinzufuegen*. Als E-Mail die Adresse des Dienstkontos eintragen; sie
steht in der JSON-Datei unter `client_email` und sieht aus wie
`name@projekt-id.iam.gserviceaccount.com`.

Rolle **Eingeschraenkt** reicht zum Lesen.

Ohne diesen Schritt antwortet die API mit 403 — das Skript sagt das dann
auch so.

### 3. Secret in GitHub hinterlegen

Repo → *Settings → Secrets and variables → Actions → New repository
secret*

- Name: `GOOGLE_SERVICE_ACCOUNT_JSON`
- Wert: der **komplette Inhalt** der JSON-Datei

Weicht die Property vom Standard ab, zusaetzlich unter *Variables* eine
Variable `GSC_SITE_URL` anlegen. Voreingestellt ist
`sc-domain:ergo-plus.de`.

- Domain-Property → `sc-domain:ergo-plus.de`
- URL-Property → `https://ergo-plus.de/`

Ein falsches Praefix ist der haeufigste Fehler; das Skript nennt bei 404
gleich die wahrscheinliche Ursache.

### 4. Einmal von Hand starten

Repo → *Actions → Search Console → Run workflow*. Danach laeuft er
montags um 05:00 UTC von selbst.

## Was im Bericht steht

`BERICHT.md` listet nicht alles auf, sondern nur, was eine Entscheidung
nach sich zieht:

**Viel gesehen, wenig geklickt** — Seiten ab 50 Impressionen, nach
Klickrate aufsteigend. Sie werden gefunden, aber nicht geklickt; dort
wirkt ein besserer Titel oder eine bessere Description.

**Knapp vor Seite 1** — Anfrage-Seite-Paare auf Position 8 bis 20 mit
mindestens 20 Impressionen. Der kuerzeste Weg zu mehr Klicks.

## Index-Waechter

`index_waechter.py` fragt fuer jede Adresse aus `sitemap.xml` die URL
Inspection API ab. Die Zahlen in `BERICHT.md` zeigen nur Seiten, die
schon Impressionen haben. Eine Seite, die nie im Index war, taucht dort
nie auf. Im Oktober 2026 stand genau deshalb monatelang kein einziger
Ratgeber-Artikel bei Google, ohne dass es jemand gemerkt hat.

Gleicher Service Account, gleiche Rolle, keine neue Freigabe. Kontingent:
2000 Pruefungen pro Tag und Property; die Sitemap hat rund 25 Adressen.
Laeuft im Montagslauf direkt nach dem Datenabruf und bei jedem PR, der
die Skripte aendert (dann ohne Commit).

## Zwei Fallstricke

**Die letzten drei Tage fehlen absichtlich.** Search Console hinkt zwei
bis drei Tage hinterher. Ohne diesen Abstand saehe das Ende jedes
Zeitraums wie ein Einbruch aus.

**Suchanfragen nicht aufsummieren.** Google laesst Anfragen mit sehr
wenig Volumen aus Datenschutzgruenden weg. Die Summe der Zeilen unter
*Suchanfragen* ist deshalb kleiner als die tatsaechliche Gesamtzahl. Fuer
Gesamtwerte den Tagesverlauf nehmen — genau das tut der Bericht.

## Lokal ausfuehren

```bash
pip install google-auth requests
export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat schluessel.json)"
python3 tools/search-console/fetch_gsc.py --tage 90
```

Aus der Claude-Umgebung heraus schlaegt das fehl (Egress-Proxy). Vom
eigenen Rechner aus funktioniert es.
