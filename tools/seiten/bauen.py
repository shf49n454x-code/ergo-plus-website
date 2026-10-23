#!/usr/bin/env python3
"""Setzt die gemeinsamen Teile jeder Seite: Kopf, Navigation, Brotkrumen,
Kontaktband, Fußzeile, Cookie-Hinweis, Skript und Asset-Versionen.
Baut danach sitemap.xml neu.

    python3 tools/seiten/bauen.py            # schreiben
    python3 tools/seiten/bauen.py --pruefen  # nur prüfen (CI), Exitcode 1 bei Abweichung

Warum das ein Skript ist und kein Kopieren: Seit Oktober 2026 hat die Seite
mehrere Unterseiten statt eines Onepagers. Jede trägt dieselbe Navigation.
Von Hand gepflegt laufen die Kopien auseinander – genau das ist auf
jonpride.de mehrfach passiert (siehe LEARNINGS.md). Die Blöcke stehen
zwischen Markern; alles außerhalb der Marker bleibt unangetastet.

Neue Seite? In SEITEN eintragen, Marker setzen (siehe Vorlage unten), Skript laufen lassen.
"""
import datetime
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
BASIS = "https://ergo-plus.de"
TEL_HREF = "tel:+49602112807"
TEL_TEXT = "06021 12807"

# Seite → (Kurzname für Brotkrumen, Elternseite, Navigationspunkt)
# Elternseite None = keine Brotkrumen (Startseite). Kurzname None = H1 nehmen.
SEITEN = {
    "index.html": ("Startseite", None, None),
    "sitzloesungen.html": ("Sitzlösungen", "index.html", "sitzloesungen"),
    "ablauf-und-kosten.html": ("Ablauf & Kosten", "index.html", "ablauf"),
    "krankheitsbilder.html": ("Krankheitsbilder", "index.html", "krankheitsbilder"),
    "ueber-ergo-plus.html": ("Über uns", "index.html", "ueber"),
    "kontakt.html": ("Kontakt", "index.html", None),
    "faq.html": ("Häufige Fragen", "index.html", None),
    "impressum.html": ("Impressum", "index.html", None),
    "datenschutz.html": ("Datenschutz", "index.html", None),
    "blog/index.html": ("Ratgeber", "index.html", "ratgeber"),
    "404.html": (None, None, None),
}
# Ratgeber-Artikel hängen automatisch unter blog/index.html.

# Seiten mit eigener Oberfläche, die nur in die Sitemap gehören.
OHNE_RAHMEN = {"pose-bogen.html"}

NAV = [
    ("sitzloesungen", "/sitzloesungen.html", "Sitzlösungen"),
    ("ablauf", "/ablauf-und-kosten.html", "Ablauf & Kosten"),
    ("krankheitsbilder", "/krankheitsbilder.html", "Krankheitsbilder"),
    ("ratgeber", "/blog/", "Ratgeber"),
    ("ueber", "/ueber-ergo-plus.html", "Über uns"),
]

MARKER = {
    "KOPF": ("<!-- SEITE:KOPF -->", "<!-- /SEITE:KOPF -->"),
    "NAV": ("<!-- SEITE:NAV -->", "<!-- /SEITE:NAV -->"),
    "KRUMEN": ("<!-- SEITE:KRUMEN -->", "<!-- /SEITE:KRUMEN -->"),
    "FUSS": ("<!-- SEITE:FUSS -->", "<!-- /SEITE:FUSS -->"),
}


def url_von(pfad: str) -> str:
    if pfad == "index.html":
        return "/"
    if pfad.endswith("/index.html"):
        return "/" + pfad[: -len("index.html")]
    return "/" + pfad


def version(datei: str) -> str:
    return hashlib.sha256((WURZEL / datei).read_bytes()).hexdigest()[:10]


def h1_text(quelle: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", quelle, re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def alle_seiten():
    out = sorted(p.relative_to(WURZEL).as_posix() for p in WURZEL.glob("*.html"))
    out += sorted(p.relative_to(WURZEL).as_posix() for p in (WURZEL / "blog").glob("*.html"))
    return out


def eintrag(pfad: str):
    if pfad in SEITEN:
        return SEITEN[pfad]
    if pfad.startswith("blog/"):
        return (None, "blog/index.html", "ratgeber")
    return None


def kette(pfad: str, quellen: dict):
    """Liste (Name, URL) von der Startseite bis zur Seite."""
    out = []
    p = pfad
    while p:
        kurz, eltern, _ = eintrag(p)
        name = kurz or h1_text(quellen[p])
        out.append((name, url_von(p)))
        p = eltern
    return list(reversed(out))


# ── Bausteine ──────────────────────────────────────────────────────────

def kopf(pfad):
    v_css, v_js = version("assets/css/site.css"), version("assets/js/site.js")
    return (
        '\n  <link rel="stylesheet" href="/assets/fonts/fonts.css" />\n'
        f'  <link rel="stylesheet" href="/assets/css/site.css?v={v_css}" />\n'
        f'  <script src="/assets/js/site.js?v={v_js}" defer></script>\n  '
    )


def nav(pfad):
    aktiv = eintrag(pfad)[2]
    punkte = []
    for key, href, text in NAV:
        cur = ' aria-current="page"' if key == aktiv and url_von(pfad) == href else (
            ' aria-current="true"' if key == aktiv else "")
        punkte.append(f'        <li><a href="{href}"{cur}>{html.escape(text)}</a></li>')
    return f"""
<a class="skip" href="#inhalt">Zum Inhalt springen</a>
<header class="site-head">
  <div class="wrap site-head__in">
    <a class="site-head__logo" href="/"><img src="/logo-ergoplus.png" alt="ERGO-PLUS Startseite" width="110" height="65" /></a>
    <nav class="site-nav" id="site-nav" aria-label="Hauptnavigation">
      <ul>
{chr(10).join(punkte)}
      </ul>
      <div class="site-nav__extra">
        <a class="btn btn--act" href="/kontakt.html">Beratung anfragen</a>
        <a class="btn btn--line" href="{TEL_HREF}">{TEL_TEXT} anrufen</a>
      </div>
    </nav>
    <a class="site-head__tel" href="{TEL_HREF}">{TEL_TEXT}<small>Beratung am Telefon</small></a>
    <a class="btn btn--act site-head__cta" href="/kontakt.html">Beratung anfragen</a>
    <button class="burger" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Menü öffnen"><span></span><span></span><span></span></button>
  </div>
</header>
"""


def krumen(pfad, quellen):
    k = kette(pfad, quellen)
    teile = []
    for i, (name, url) in enumerate(k):
        if i == len(k) - 1:
            teile.append(f'      <li aria-current="page">{html.escape(name)}</li>')
        else:
            teile.append(f'      <li><a href="{url}">{html.escape(name)}</a></li>')
    ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": BASIS + u}
            for i, (n, u) in enumerate(k)
        ],
    }
    return f"""
  <nav class="crumbs wrap" aria-label="Brotkrumen">
    <ol>
{chr(10).join(teile)}
    </ol>
  </nav>
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
  """


def fuss(pfad):
    band = "" if pfad == "kontakt.html" else f"""
<section class="contact-band" aria-labelledby="kontaktband-titel">
  <div class="wrap contact-band__grid">
    <div>
      <h2 id="kontaktband-titel">Erzählen Sie uns, wie Sie heute sitzen.</h2>
      <p>Das erste Gespräch ist kostenlos und unverbindlich. Wir klären, was Sie brauchen, und wer die Kosten tragen kann.</p>
    </div>
    <div>
      <a class="contact-band__tel" href="{TEL_HREF}">{TEL_TEXT}</a>
      <div class="btn-row"><a class="btn btn--light" href="/kontakt.html">Beratung anfragen</a></div>
      <small>Oder schreiben Sie an <a href="mailto:info@ergo-plus.de">info@ergo-plus.de</a></small>
    </div>
  </div>
</section>"""
    return f"""{band}
<footer class="site-foot">
  <div class="wrap">
    <div class="site-foot__grid">
      <div class="site-foot__brand">
        <img src="/logo-ergoplus.png" alt="" width="110" height="65" loading="lazy" />
        <address>
          ERGO-PLUS Seating Concepts GmbH<br />
          Am Sportplatz 15<br />
          63867 Johannesberg<br />
          Telefon <a href="{TEL_HREF}">+49 6021 12807</a><br />
          <a href="mailto:info@ergo-plus.de">info@ergo-plus.de</a>
        </address>
      </div>
      <div>
        <h2>Sitzlösungen</h2>
        <ul>
          <li><a href="/sitzloesungen.html#vela-tango">VELA TANGO</a></li>
          <li><a href="/sitzloesungen.html#vela-blues">VELA BLUES</a></li>
          <li><a href="/sitzloesungen.html#mfs">MFS-Stuhlsystem</a></li>
          <li><a href="/sitzloesungen.html#elift">ELIFT 400</a></li>
          <li><a href="/sitzloesungen.html#opera">Opera 20 und SMARTMOVE</a></li>
          <li><a href="/sitzloesungen.html#speziell">Speziallösungen</a></li>
        </ul>
      </div>
      <div>
        <h2>Wissen</h2>
        <ul>
          <li><a href="/krankheitsbilder.html">Krankheitsbilder</a></li>
          <li><a href="/ablauf-und-kosten.html">Ablauf und Kostenübernahme</a></li>
          <li><a href="/blog/">Ratgeber</a></li>
          <li><a href="/faq.html">Häufige Fragen</a></li>
          <li><a href="/pose-bogen.html">POSE-Bogen</a></li>
        </ul>
      </div>
      <div>
        <h2>Unternehmen</h2>
        <ul>
          <li><a href="/ueber-ergo-plus.html">Über uns</a></li>
          <li><a href="/ueber-ergo-plus.html#team">Team</a></li>
          <li><a href="/kontakt.html">Kontakt</a></li>
          <li><a href="/impressum.html">Impressum</a></li>
          <li><a href="/datenschutz.html">Datenschutz</a></li>
        </ul>
      </div>
    </div>
    <div class="site-foot__base">
      <span>© {datetime.date.today().year} ERGO-PLUS Seating Concepts GmbH</span>
      <button type="button" id="cookie-settings-link">Cookie-Einstellungen</button>
    </div>
  </div>
</footer>

<div class="cookie-banner" id="cookie-banner" role="region" aria-label="Cookie-Hinweis">
  <p class="cookie-text">Wir verwenden technisch notwendige Cookies sowie, mit Ihrer Zustimmung, Google Analytics zur Reichweitenmessung. Mehr dazu in der <a href="/datenschutz.html">Datenschutzerklärung</a>.</p>
  <div class="cookie-btns">
    <button type="button" class="cookie-btn cookie-btn-essential" id="cookie-essential">Nur essenzielle</button>
    <button type="button" class="cookie-btn cookie-btn-accept" id="cookie-accept">Verstanden</button>
  </div>
</div>
"""


# ── Ersetzen zwischen Markern ─────────────────────────────────────────

def ersetzen(quelle: str, name: str, inhalt: str, pfad: str) -> str:
    a, z = MARKER[name]
    muster = re.compile(re.escape(a) + r".*?" + re.escape(z), re.S)
    if not muster.search(quelle):
        raise SystemExit(f"{pfad}: Marker {a} fehlt")
    return muster.sub(lambda _: a + inhalt + z, quelle, count=1)


def seite_bauen(pfad, quelle, quellen):
    q = ersetzen(quelle, "KOPF", kopf(pfad), pfad)
    q = ersetzen(q, "NAV", nav(pfad), pfad)
    if eintrag(pfad)[1]:
        q = ersetzen(q, "KRUMEN", krumen(pfad, quellen), pfad)
    q = ersetzen(q, "FUSS", fuss(pfad), pfad)
    return q


# ── Sitemap ───────────────────────────────────────────────────────────

def lastmod(pfad: str) -> str:
    try:
        d = subprocess.run(["git", "log", "-1", "--format=%cs", "--", pfad], cwd=WURZEL,
                           capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        d = ""
    return d or datetime.date.today().isoformat()


def sitemap(quellen) -> str:
    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for pfad in alle_seiten():
        if pfad == "404.html":
            continue
        if re.search(r'<meta name="robots" content="[^"]*noindex', quellen[pfad]):
            continue
        zeilen.append(f"  <url><loc>{BASIS}{url_von(pfad)}</loc><lastmod>{lastmod(pfad)}</lastmod></url>")
    zeilen.append("</urlset>")
    return "\n".join(zeilen) + "\n"


def main():
    pruefen = "--pruefen" in sys.argv
    seiten = alle_seiten()
    quellen = {p: (WURZEL / p).read_text(encoding="utf-8") for p in seiten}
    abweichend = []

    for pfad in seiten:
        if pfad in OHNE_RAHMEN:
            continue
        if eintrag(pfad) is None:
            abweichend.append(f"{pfad}: nicht in SEITEN eingetragen")
            continue
        neu = seite_bauen(pfad, quellen[pfad], quellen)
        if neu != quellen[pfad]:
            if pruefen:
                abweichend.append(f"{pfad}: Rahmen veraltet")
            else:
                (WURZEL / pfad).write_text(neu, encoding="utf-8")
                quellen[pfad] = neu

    sm = sitemap(quellen)
    sm_alt = (WURZEL / "sitemap.xml").read_text(encoding="utf-8") if (WURZEL / "sitemap.xml").exists() else ""
    # lastmod hängt am Commit, nicht am Inhalt: für die Prüfung nur die Adressen vergleichen.
    adressen = lambda s: re.findall(r"<loc>(.*?)</loc>", s)
    if adressen(sm) != adressen(sm_alt):
        if pruefen:
            abweichend.append("sitemap.xml: Adressen stimmen nicht mit den Seiten überein")
        else:
            (WURZEL / "sitemap.xml").write_text(sm, encoding="utf-8")
    elif not pruefen and sm != sm_alt:
        (WURZEL / "sitemap.xml").write_text(sm, encoding="utf-8")

    if abweichend:
        print("\n".join(abweichend))
        if pruefen:
            print("\n→ python3 tools/seiten/bauen.py ausführen und das Ergebnis committen.")
        sys.exit(1)
    print(f"{len(seiten)} Seiten {'geprüft' if pruefen else 'gebaut'}, sitemap.xml mit {len(adressen(sm))} Adressen.")


if __name__ == "__main__":
    main()
