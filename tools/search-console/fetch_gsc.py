#!/usr/bin/env python3
"""Search-Console-Daten abholen und ins Repo schreiben.

Läuft in GitHub Actions mit einem Google-Service-Account. Der private
Schlüssel steckt im Secret GOOGLE_SERVICE_ACCOUNT_JSON und taucht nirgends
im Repo auf.

Aufruf:
    python3 tools/search-console/fetch_gsc.py
    python3 tools/search-console/fetch_gsc.py --tage 180 --out data/search-console

Ergebnis:
    data/search-console/latest.json      alle Dimensionen, maschinenlesbar
    data/search-console/BERICHT.md       die Auffälligkeiten in Textform
    data/search-console/LETZTER-LAUF.md  was dieser Lauf getan hat

Einrichtung: siehe README.md im selben Ordner.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

API = "https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

# Search Console hinkt zwei bis drei Tage hinterher. Ohne diesen Abstand
# sieht das Ende jedes Zeitraums wie ein Einbruch aus.
NACHLAUF_TAGE = 3

# Was abgefragt wird. Die Kombination query+page ist die wertvollste:
# sie zeigt, welche Seite für welche Anfrage rankt.
ABFRAGEN = {
    "suchanfragen": ["query"],
    "seiten": ["page"],
    "anfrage_x_seite": ["query", "page"],
    "verlauf": ["date"],
}


def zugangsdaten():
    """Service-Account-Anmeldung aus dem Secret."""
    roh = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not roh:
        sys.exit(
            "GOOGLE_SERVICE_ACCOUNT_JSON ist nicht gesetzt.\n"
            "In GitHub: Settings > Secrets and variables > Actions > New secret.\n"
            "Inhalt ist die JSON-Schluesseldatei des Service Accounts."
        )
    try:
        info = json.loads(roh)
    except json.JSONDecodeError as e:
        sys.exit(f"Das Secret ist kein gueltiges JSON: {e}")

    try:
        from google.oauth2 import service_account  # type: ignore
        import google.auth.transport.requests  # type: ignore
    except ImportError:
        sys.exit("Bitte zuerst installieren: pip install google-auth requests")

    creds = service_account.Credentials.from_service_account_info(
        info, scopes=[SCOPE]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds, info.get("client_email", "(unbekannt)")


def frage_api(creds, site: str, koerper: dict) -> dict:
    import requests  # type: ignore

    antwort = requests.post(
        API.format(site=requests.utils.quote(site, safe="")),
        headers={"Authorization": f"Bearer {creds.token}"},
        json=koerper,
        timeout=60,
    )
    if antwort.status_code == 403:
        sys.exit(
            "403 von der Search Console.\n"
            "Der Service Account ist dort vermutlich nicht als Nutzer "
            "eingetragen. Search Console > Einstellungen > Nutzer und "
            "Berechtigungen > Nutzer hinzufuegen, mit der E-Mail des "
            "Service Accounts. Rolle 'Eingeschraenkt' reicht zum Lesen."
        )
    if antwort.status_code == 404:
        sys.exit(
            f"404 fuer die Property '{site}'.\n"
            "Domain-Property braucht das Praefix 'sc-domain:', "
            "URL-Property die vollstaendige URL mit Schraegstrich."
        )
    antwort.raise_for_status()
    return antwort.json()


def hole_alles(creds, site: str, dimensionen: list[str],
               von: str, bis: str, max_zeilen: int) -> list[dict]:
    """Blättert über die 25.000-Zeilen-Grenze der API hinweg."""
    alle: list[dict] = []
    schritt = min(max_zeilen, 25000)
    start = 0
    while len(alle) < max_zeilen:
        daten = frage_api(creds, site, {
            "startDate": von,
            "endDate": bis,
            "dimensions": dimensionen,
            "rowLimit": schritt,
            "startRow": start,
        })
        zeilen = daten.get("rows", [])
        alle.extend(zeilen)
        if len(zeilen) < schritt:
            break
        start += schritt
    return alle[:max_zeilen]


def als_tabelle(zeilen: list[dict], dimensionen: list[str]) -> list[dict]:
    raus = []
    for r in zeilen:
        eintrag = dict(zip(dimensionen, r.get("keys", [])))
        eintrag.update({
            "klicks": r.get("clicks", 0),
            "impressionen": r.get("impressions", 0),
            "ctr_prozent": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        })
        raus.append(eintrag)
    return raus


def bericht(daten: dict, site: str, von: str, bis: str) -> str:
    """Kurzer Text, der die Auffälligkeiten benennt statt alles aufzulisten."""
    zeilen = [
        f"# Search Console: {site}",
        "",
        f"Zeitraum {von} bis {bis}. Die letzten {NACHLAUF_TAGE} Tage sind "
        "ausgelassen, weil Search Console hinterherhinkt.",
        "",
    ]

    verlauf = daten.get("verlauf", [])
    if verlauf:
        klicks = sum(z["klicks"] for z in verlauf)
        impr = sum(z["impressionen"] for z in verlauf)
        ctr = round(100 * klicks / impr, 2) if impr else 0
        zeilen += [
            "## Gesamt",
            "",
            f"- Klicks: **{klicks}**",
            f"- Impressionen: **{impr}**",
            f"- Klickrate: **{ctr} %**",
            "",
            "Diese Zahlen stammen aus dem Tagesverlauf. Die Zeilen unter "
            "*Suchanfragen* duerfen nicht aufsummiert werden: Google laesst "
            "Anfragen mit wenig Volumen aus Datenschutzgruenden weg.",
            "",
        ]

    # Seiten, die gefunden, aber nicht geklickt werden: viele Impressionen,
    # schlechte Klickrate. Genau dort wirkt ein besserer Titel.
    seiten = [s for s in daten.get("seiten", []) if s["impressionen"] >= 50]
    schwach = sorted(seiten, key=lambda s: (s["ctr_prozent"], -s["impressionen"]))[:10]
    if schwach:
        zeilen += [
            "## Viel gesehen, wenig geklickt",
            "",
            "Ab 50 Impressionen, nach Klickrate aufsteigend. Hier lohnt sich "
            "ein besserer Titel oder eine bessere Description.",
            "",
            "| Seite | Impressionen | Klicks | CTR | Position |",
            "|---|---:|---:|---:|---:|",
        ]
        for s in schwach:
            zeilen.append(
                f"| {s['page']} | {s['impressionen']} | {s['klicks']} | "
                f"{s['ctr_prozent']} % | {s['position']} |"
            )
        zeilen.append("")

    # Position 8 bis 20: eine Seite weiter vorn ist realistisch erreichbar.
    schwelle = [a for a in daten.get("anfrage_x_seite", [])
                if 8 <= a["position"] <= 20 and a["impressionen"] >= 20]
    schwelle.sort(key=lambda a: -a["impressionen"])
    if schwelle:
        zeilen += [
            "## Knapp vor Seite 1",
            "",
            "Position 8 bis 20 bei mindestens 20 Impressionen. Der kuerzeste "
            "Weg zu mehr Klicks.",
            "",
            "| Suchanfrage | Seite | Impressionen | Position |",
            "|---|---|---:|---:|",
        ]
        for a in schwelle[:15]:
            zeilen.append(
                f"| {a['query']} | {a['page']} | {a['impressionen']} | "
                f"{a['position']} |"
            )
        zeilen.append("")

    zeilen += ["---", "",
               "Erzeugt von `tools/search-console/fetch_gsc.py`. "
               "Vollstaendige Daten in `latest.json`."]
    return "\n".join(zeilen) + "\n"


def laufbericht(ordner: pathlib.Path, zeilen: list[str], fehler: str = "") -> None:
    """Haelt fest, was dieser Lauf getan hat - auch wenn er gescheitert ist.

    Ohne diese Datei ist ein Lauf, der nichts bewirkt hat, von einem, bei
    dem es nichts zu tun gab, nicht zu unterscheiden: beide enden still und
    beide melden Erfolg. Genau daran ist hier schon dreimal Zeit
    verlorengegangen.
    """
    ordner.mkdir(parents=True, exist_ok=True)
    kopf = [
        "# Letzter Lauf",
        "",
        f"**{dt.datetime.now(dt.timezone.utc):%d.%m.%Y %H:%M} UTC** — "
        + ("**gescheitert**" if fehler else "erfolgreich"),
        "",
    ]
    if fehler:
        kopf += ["```", fehler.strip(), "```", ""]
    kopf += zeilen + [
        "",
        "---",
        "",
        "Erzeugt von `tools/search-console/fetch_gsc.py` bei jedem Lauf. "
        "Ist diese Datei aelter als der letzte Montag, ist der Workflow "
        "nicht gelaufen — das Audit meldet das ab zehn Tagen von allein.",
    ]
    (ordner / "LETZTER-LAUF.md").write_text("\n".join(kopf) + "\n",
                                            encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site", default=os.environ.get("GSC_SITE_URL",
                                                    "sc-domain:ergo-plus.de"))
    p.add_argument("--tage", type=int, default=90)
    p.add_argument("--max-zeilen", type=int, default=5000)
    p.add_argument("--out", default="data/search-console")
    args = p.parse_args()

    bis_d = dt.date.today() - dt.timedelta(days=NACHLAUF_TAGE)
    von_d = bis_d - dt.timedelta(days=args.tage)
    von, bis = von_d.isoformat(), bis_d.isoformat()

    ordner = pathlib.Path(args.out)

    try:
        creds, konto = zugangsdaten()
        print(f"Service Account: {konto}")
        print(f"Property: {args.site}")
        print(f"Zeitraum: {von} bis {bis}")

        daten = {}
        for name, dimensionen in ABFRAGEN.items():
            zeilen = hole_alles(creds, args.site, dimensionen, von, bis,
                                args.max_zeilen)
            daten[name] = als_tabelle(zeilen, dimensionen)
            print(f"  {name}: {len(daten[name])} Zeilen")
    # SystemExit gehoert bewusst dazu: zugangsdaten() und frage_api() beenden
    # das Programm mit sys.exit() und einer verstaendlichen Meldung. Ohne
    # SystemExit hier bliebe genau der haeufigste Fehlschlag - fehlendes oder
    # abgelaufenes Secret - unprotokolliert.
    except (Exception, SystemExit) as e:
        laufbericht(ordner,
                    [f"Property `{args.site}`, Zeitraum {von} bis {bis}.",
                     "",
                     "`latest.json` und `BERICHT.md` sind unveraendert "
                     "geblieben und zeigen weiterhin den vorherigen Stand."],
                    fehler=f"{type(e).__name__}: {e}")
        raise

    ordner.mkdir(parents=True, exist_ok=True)

    (ordner / "latest.json").write_text(json.dumps({
        "property": args.site,
        "zeitraum": {"von": von, "bis": bis},
        "abgerufen_am": dt.datetime.now(dt.timezone.utc).isoformat(),
        "daten": daten,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    (ordner / "BERICHT.md").write_text(
        bericht(daten, args.site, von, bis), encoding="utf-8")

    gesamt = {"klicks": 0, "impressionen": 0}
    for zeile in daten.get("verlauf", []):
        gesamt["klicks"] += zeile.get("klicks", 0)
        gesamt["impressionen"] += zeile.get("impressionen", 0)

    laufbericht(ordner, [
        f"Property `{args.site}`, Zeitraum {von} bis {bis} "
        f"({len(daten.get('verlauf', []))} Tage mit Daten).",
        "",
        "| Dimension | Zeilen |",
        "|---|---:|",
        *[f"| {name} | {len(zeilen)} |" for name, zeilen in daten.items()],
        "",
        f"Gesamt: **{gesamt['klicks']} Klicks**, "
        f"**{gesamt['impressionen']} Impressionen** (aus dem Tagesverlauf).",
    ])

    print(f"Geschrieben nach {ordner}/")


if __name__ == "__main__":
    main()
