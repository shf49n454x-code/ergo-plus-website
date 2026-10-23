#!/usr/bin/env python3
"""Prüft, ob ergo-plus.de wirklich erreichbar ist, so wie Besucher und Google sie sehen.

Ein grüner Deploy und eine Seite, die lokal funktioniert, sagen nichts darüber,
ob der Server draußen antwortet. Am 23.10.2026 zeigte ergo-plus.de die
STRATO-Platzhalterseite „Diese Internetpräsenz ist zur Zeit nicht erreichbar“,
ohne gültiges Zertifikat, und niemand hat es gemerkt, bis Google nur noch die
alte Startseite kannte. Dieser Wächter hätte es am ersten Tag gemeldet.

Prüft:
  1. TLS: Handshake mit gültigem Zertifikat für ergo-plus.de und www, Restlaufzeit.
  2. Weiterleitungen: http und www landen in einem Schritt auf https://ergo-plus.de/.
  3. Inhalt: Startseite liefert 200, ist unsere Seite und keine Platzhalterseite.
  4. Sitemap und robots.txt sind abrufbar.
  5. Jede Adresse der Live-Sitemap liefert 200 und keine Platzhalterseite.

Aufruf:
    python3 tools/erreichbarkeit/pruefen.py
    python3 tools/erreichbarkeit/pruefen.py --basis https://localhost:8443 --unsicher   (lokaler Test)

Exitcode 1, sobald eine Prüfung scheitert. Nur Standardbibliothek.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

DOMAIN = "ergo-plus.de"
ZIEL = f"https://{DOMAIN}/"
ZERTIFIKAT_MINDESTENS_TAGE = 14

# Woran man eine Hoster-Platzhalterseite erkennt. STRATO zuerst, weil die
# Seite dort liegt; die anderen, falls sie einmal umzieht.
PLATZHALTER = [
    "Diese Internetpräsenz ist zur Zeit nicht erreichbar",
    "This website is currently not available",
    "Powered by STRATO",
    "Domain im Kundenbereich",
    "Diese Domain wurde soeben registriert",
    "Hier entsteht eine neue Internetpräsenz",
]
# Woran man unsere Seite erkennt.
KENNUNG = "ERGO-PLUS"

AGENT = "ergo-plus-erreichbarkeit/1.0 (+https://ergo-plus.de/)"


class OhneWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: D401
        return None


def abrufen(url: str, kontext: ssl.SSLContext, folgen: bool = True,
            zeit: int = 20) -> tuple[int, dict, str]:
    """Status, Kopfzeilen und Text. Fehlerstatus kommen zurück statt Ausnahme."""
    handler = [urllib.request.HTTPSHandler(context=kontext)]
    if not folgen:
        handler.append(OhneWeiterleitung())
    oeffner = urllib.request.build_opener(*handler)
    anfrage = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with oeffner.open(anfrage, timeout=zeit) as r:
            return r.status, dict(r.headers), r.read(400_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), (e.read(50_000) or b"").decode("utf-8", "replace")


def platzhalter_in(text: str) -> str:
    for p in PLATZHALTER:
        if p.lower() in text.lower():
            return p
    return ""


def pruefe_tls(host: str, port: int, kontext: ssl.SSLContext) -> dict:
    try:
        with socket.create_connection((host, port), timeout=15) as roh:
            with kontext.wrap_socket(roh, server_hostname=host) as s:
                zert = s.getpeercert()
        if not zert:  # bei --unsicher gibt es keine geprüften Felder
            return {"ok": True, "hinweis": "nicht geprüft (--unsicher)"}
        ende = dt.datetime.strptime(zert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=dt.timezone.utc)
        rest = (ende - dt.datetime.now(dt.timezone.utc)).days
        aussteller = dict(x[0] for x in zert.get("issuer", ())).get("organizationName", "")
        return {"ok": rest >= ZERTIFIKAT_MINDESTENS_TAGE,
                "hinweis": f"gültig bis {ende:%d.%m.%Y} ({rest} Tage), {aussteller}".strip(", "),
                "rest_tage": rest}
    except ssl.SSLCertVerificationError as e:
        return {"ok": False, "hinweis": f"Zertifikat ungültig: {e.verify_message}"}
    except ssl.SSLError as e:
        return {"ok": False, "hinweis": f"TLS-Fehler: {e.reason or e}"}
    except OSError as e:
        return {"ok": False, "hinweis": f"keine Verbindung: {e}"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--basis", default=f"https://{DOMAIN}",
                   help="Basisadresse für Inhaltsprüfungen (lokal: https://localhost:8443)")
    p.add_argument("--unsicher", action="store_true",
                   help="Zertifikat nicht prüfen und Domain-Prüfungen auslassen (nur lokal)")
    p.add_argument("--out", default="data/erreichbarkeit")
    args = p.parse_args()

    kontext = ssl.create_default_context()
    if args.unsicher:
        kontext.check_hostname = False
        kontext.verify_mode = ssl.CERT_NONE
    basis = args.basis.rstrip("/")
    pruefungen: list[dict] = []

    def eintrag(name: str, ok: bool, hinweis: str) -> None:
        pruefungen.append({"pruefung": name, "ok": bool(ok), "hinweis": hinweis})
        print(("OK    " if ok else "FEHLER") + f"  {name}: {hinweis}")

    if not args.unsicher:
        for host in (DOMAIN, f"www.{DOMAIN}"):
            t = pruefe_tls(host, 443, kontext)
            eintrag(f"TLS {host}", t["ok"], t["hinweis"])
        for von in (f"http://{DOMAIN}/", f"http://www.{DOMAIN}/", f"https://www.{DOMAIN}/"):
            try:
                status, kopf, _ = abrufen(von, kontext, folgen=False)
                ort = kopf.get("Location", "")
                eintrag(f"Weiterleitung {von}", status in (301, 308) and ort == ZIEL,
                        f"{status} nach {ort or '(keine)'}; erwartet 301 nach {ZIEL}")
            except Exception as e:  # noqa: BLE001
                eintrag(f"Weiterleitung {von}", False, f"{type(e).__name__}: {e}")

    try:
        status, kopf, text = abrufen(basis + "/", kontext)
        ph = platzhalter_in(text)
        eintrag("Startseite", status == 200 and not ph and KENNUNG in text,
                f"{status}" + (f", Platzhalterseite erkannt („{ph}“)" if ph else "")
                + ("" if KENNUNG in text else f", „{KENNUNG}“ fehlt im Text"))
        hsts = kopf.get("Strict-Transport-Security", "")
        if hsts:
            eintrag("HSTS", True, hsts)
    except Exception as e:  # noqa: BLE001
        eintrag("Startseite", False, f"{type(e).__name__}: {e}")

    try:
        status, _, robots = abrufen(basis + "/robots.txt", kontext)
        ph = platzhalter_in(robots)
        hat_sitemap = "sitemap:" in robots.lower()
        eintrag("robots.txt", status == 200 and hat_sitemap and not ph,
                f"{status}" + (f", Platzhalterseite erkannt („{ph}“)" if ph else "")
                + ("" if hat_sitemap else ", keine Sitemap-Zeile"))
    except Exception as e:  # noqa: BLE001
        eintrag("robots.txt", False, f"{type(e).__name__}: {e}")

    adressen: list[str] = []
    try:
        status, _, xml = abrufen(basis + "/sitemap.xml", kontext)
        if status == 200 and not platzhalter_in(xml):
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            adressen = [l.text.strip() for l in ET.fromstring(xml).findall(".//s:loc", ns) if l.text]
        eintrag("Sitemap", status == 200 and bool(adressen), f"{status}, {len(adressen)} Adressen")
    except Exception as e:  # noqa: BLE001
        eintrag("Sitemap", False, f"{type(e).__name__}: {e}")

    kaputt = []
    for url in adressen:
        pfad = urllib.parse.urlsplit(url).path or "/"
        try:
            status, _, text = abrufen(basis + pfad, kontext)
            if status != 200 or platzhalter_in(text):
                kaputt.append(f"{pfad} ({status}{', Platzhalter' if platzhalter_in(text) else ''})")
        except Exception as e:  # noqa: BLE001
            kaputt.append(f"{pfad} ({type(e).__name__})")
    if adressen:
        eintrag("Alle Sitemap-Adressen", not kaputt,
                f"{len(adressen) - len(kaputt)} von {len(adressen)} liefern 200"
                + (": " + ", ".join(kaputt[:10]) if kaputt else ""))

    ok = all(x["ok"] for x in pruefungen)
    jetzt = dt.datetime.now(dt.timezone.utc)
    ordner = pathlib.Path(args.out)
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "status.json").write_text(json.dumps({
        "basis": basis, "geprueft_am": jetzt.isoformat(), "ok": ok,
        "pruefungen": pruefungen}, ensure_ascii=False, indent=1), encoding="utf-8")
    zeilen = [
        "# Erreichbarkeit",
        "",
        f"**{jetzt:%d.%m.%Y %H:%M} UTC** — " + ("alles in Ordnung" if ok else "**gestört**"),
        "",
        "| Prüfung | Ergebnis | Hinweis |",
        "|---|---|---|",
        *[f"| {x['pruefung']} | {'ok' if x['ok'] else '**FEHLER**'} | {x['hinweis']} |"
          for x in pruefungen],
        "",
        "---",
        "",
        "Erzeugt von `tools/erreichbarkeit/pruefen.py`, täglich über "
        "`.github/workflows/erreichbarkeit.yml`.",
    ]
    (ordner / "ERREICHBARKEIT.md").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
