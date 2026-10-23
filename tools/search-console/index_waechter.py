#!/usr/bin/env python3
"""Prüft für jede Adresse der Sitemap, ob Google sie im Index hat.

Nutzt die URL Inspection API der Search Console mit demselben Service
Account wie fetch_gsc.py. Die Search-Analytics-Zahlen zeigen nur Seiten,
die schon Impressionen haben; eine Seite, die gar nicht im Index steht,
taucht dort nie auf und fällt niemandem auf. Genau das ist bei ergo-plus.de
passiert: 16 Ratgeber-Artikel, kein einziger im Index, und es hat Monate
gedauert, bis es jemand bemerkt hat.

Aufruf:
    python3 tools/search-console/index_waechter.py
    python3 tools/search-console/index_waechter.py --sitemap sitemap.xml --out data/search-console

Ergebnis:
    data/search-console/index.json   je Adresse: Status, letzter Crawl, Google-Canonical
    data/search-console/INDEX.md     dieselbe Liste lesbar, Probleme zuerst

Exitcode 0 auch wenn Seiten fehlen: Der Wächter berichtet, er blockiert
nichts. Exitcode 1 nur, wenn die Prüfung selbst nicht laufen konnte.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time
import xml.etree.ElementTree as ET

API = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

# Google erlaubt 600 Prüfungen pro Minute und 2000 pro Tag und Property.
# Bei rund 25 Adressen ist das weit weg; die Pause schont trotzdem das
# Minutenkontingent, falls die Sitemap einmal wächst.
PAUSE_S = 0.25
HOECHSTENS = 1500

# coverageState kommt als englischer Text. Was davon "im Index" heißt:
IM_INDEX = {"Submitted and indexed", "Indexed, not submitted in sitemap"}


def adressen_aus_sitemap(pfad: pathlib.Path) -> list[str]:
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    baum = ET.parse(pfad)
    return [loc.text.strip() for loc in baum.findall(".//s:loc", ns) if loc.text]


def zugangsdaten():
    roh = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not roh:
        sys.exit("GOOGLE_SERVICE_ACCOUNT_JSON ist nicht gesetzt "
                 "(siehe tools/search-console/README.md, Schritt 3).")
    from google.oauth2 import service_account  # type: ignore
    import google.auth.transport.requests  # type: ignore
    creds = service_account.Credentials.from_service_account_info(
        json.loads(roh), scopes=[SCOPE])
    creds.refresh(google.auth.transport.requests.Request())
    return creds


def pruefe(sitzung, creds, site: str, url: str) -> dict:
    antwort = sitzung.post(
        API,
        headers={"Authorization": f"Bearer {creds.token}"},
        json={"inspectionUrl": url, "siteUrl": site, "languageCode": "de"},
        timeout=60,
    )
    if antwort.status_code == 403:
        sys.exit("403 von der URL Inspection API. Der Service Account braucht "
                 "in der Search Console mindestens die Rolle 'Eingeschraenkt'.")
    if antwort.status_code == 429:
        sys.exit("429: Tageskontingent der URL Inspection API erschoepft.")
    antwort.raise_for_status()
    erg = antwort.json().get("inspectionResult", {}).get("indexStatusResult", {})
    return {
        "url": url,
        "im_index": erg.get("coverageState") in IM_INDEX,
        "urteil": erg.get("verdict", ""),               # PASS / NEUTRAL / FAIL
        "zustand": erg.get("coverageState", ""),        # Googles Begründung
        "abruf": erg.get("pageFetchState", ""),         # SUCCESSFUL, SOFT_404, ...
        "robots": erg.get("robotsTxtState", ""),
        "indexierung_erlaubt": erg.get("indexingState", ""),
        "letzter_crawl": erg.get("lastCrawlTime", ""),
        "canonical_google": erg.get("googleCanonical", ""),
        "canonical_seite": erg.get("userCanonical", ""),
    }


def bericht(ergebnisse: list[dict], site: str, stand: str) -> str:
    drin = [e for e in ergebnisse if e["im_index"]]
    fehlt = [e for e in ergebnisse if not e["im_index"]]
    zeilen = [
        f"# Index: {site}",
        "",
        f"Stand {stand}. **{len(drin)} von {len(ergebnisse)}** Adressen der "
        "Sitemap sind bei Google im Index.",
        "",
    ]
    if fehlt:
        zeilen += [
            "## Nicht im Index",
            "",
            "Googles Begruendung steht in *Zustand*, wie Google sie liefert. "
            "Haeufigste Faelle: *Discovered - currently not indexed* (Google "
            "kennt die Adresse, hat sie aber noch nicht gelesen), *Crawled - "
            "currently not indexed* (gelesen, fuer zu duenn befunden), *URL is "
            "unknown to Google* (nie gesehen), *Server error* oder ein "
            "Abruffehler unter *Abruf* (die Seite war nicht erreichbar).",
            "",
            "| Adresse | Zustand | Abruf | Letzter Crawl |",
            "|---|---|---|---|",
        ]
        for e in sorted(fehlt, key=lambda e: e["url"]):
            zeilen.append(f"| {e['url']} | {e['zustand'] or '–'} | "
                          f"{e['abruf'] or '–'} | {e['letzter_crawl'][:10] or 'nie'} |")
        zeilen.append("")
    abweichend = [e for e in drin if e["canonical_google"]
                  and e["canonical_google"] != e["url"]]
    if abweichend:
        zeilen += [
            "## Im Index, aber unter anderer Adresse",
            "",
            "Google fuehrt die Seite unter einer anderen kanonischen Adresse "
            "als der in der Sitemap.",
            "",
            "| Sitemap | Google-Canonical |",
            "|---|---|",
            *[f"| {e['url']} | {e['canonical_google']} |" for e in abweichend],
            "",
        ]
    if drin:
        zeilen += [
            "## Im Index",
            "",
            "| Adresse | Letzter Crawl |",
            "|---|---|",
            *[f"| {e['url']} | {e['letzter_crawl'][:10]} |"
              for e in sorted(drin, key=lambda e: e["url"])],
            "",
        ]
    zeilen += ["---", "", "Erzeugt von `tools/search-console/index_waechter.py`."]
    return "\n".join(zeilen) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site", default=os.environ.get("GSC_SITE_URL",
                                                    "sc-domain:ergo-plus.de"))
    p.add_argument("--sitemap", default="sitemap.xml")
    p.add_argument("--out", default="data/search-console")
    args = p.parse_args()

    import requests  # type: ignore

    adressen = adressen_aus_sitemap(pathlib.Path(args.sitemap))[:HOECHSTENS]
    if not adressen:
        sys.exit(f"Keine Adressen in {args.sitemap}.")
    creds = zugangsdaten()
    sitzung = requests.Session()
    ergebnisse = []
    for url in adressen:
        ergebnisse.append(pruefe(sitzung, creds, args.site, url))
        time.sleep(PAUSE_S)

    stand = dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    ordner = pathlib.Path(args.out)
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "index.json").write_text(json.dumps({
        "property": args.site,
        "abgerufen_am": dt.datetime.now(dt.timezone.utc).isoformat(),
        "im_index": sum(e["im_index"] for e in ergebnisse),
        "adressen": len(ergebnisse),
        "ergebnisse": ergebnisse,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    (ordner / "INDEX.md").write_text(bericht(ergebnisse, args.site, stand),
                                     encoding="utf-8")
    print(f"{sum(e['im_index'] for e in ergebnisse)} von {len(ergebnisse)} im Index.")


if __name__ == "__main__":
    main()
