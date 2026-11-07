#!/usr/bin/env python3
"""Baut die tiefen Seiten (Fragen, Produkte, Kostenträger, Autor) aus Markdown.

    python3 tools/seiten/tief.py            # schreiben
    python3 tools/seiten/tief.py --pruefen  # nur prüfen (CI), Exitcode 1 bei Abweichung

Quelle: tools/seiten/inhalte/<bereich>/<name>.md  →  <bereich>/<name>.html
Danach immer tools/seiten/bauen.py laufen lassen (setzt Kopf, Navigation,
Brotkrumen, Fußzeile und baut die Sitemap).

Warum Markdown: Antworten, Produkttexte und Kostenträger ändern sich. Wer
einen Satz korrigiert, soll nicht durch HTML müssen. Der Rahmen (Kurzantwort,
Quellen, Stand, Autor, strukturierte Daten) entsteht hier einheitlich, damit
keine Seite ohne Quelle oder Stand-Datum online geht.

Kopfzeilen einer Quelldatei (alle Pflicht, außer markiert):
    titel:        Title-Tag ohne Marke, höchstens 52 Zeichen (Marke kommt dazu)
    beschreibung: Meta-Description, 80–160 Zeichen
    h1:           Überschrift (bei Fragen: die Frage selbst)
    lead:         ein bis zwei Sätze unter der Überschrift
    kurz:         Kurzantwort, zwei bis drei Sätze (wird oben hervorgehoben)
    typ:          frage | produkt | kosten | person | seite
    kategorie:    nur bei Fragen, Gruppe auf der Übersicht
    stand:        JJJJ-MM-TT
    quellen:      Liste "Text | https://…" (Pflicht bei frage, produkt, kosten)
    weiter:       Liste "/pfad | Linktext", 3–5 Einträge
    hersteller:   nur bei Produkten (optional)
"""
import html
import json
import re
import sys
from pathlib import Path

import markdown

WURZEL = Path(__file__).resolve().parents[2]
QUELLE = WURZEL / "tools" / "seiten" / "inhalte"
BASIS = "https://ergo-plus.de"
TEL_HREF, TEL_TEXT = "tel:+49602112807", "06021 12807"
AUTOR_URL = "/team/joachim-stolz.html"
AUTOR_ID = BASIS + AUTOR_URL + "#person"
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]
PFLICHT = ["titel", "beschreibung", "h1", "lead", "kurz", "typ", "stand", "weiter"]


def lesen(datei: Path):
    text = datei.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        raise SystemExit(f"{datei}: Kopfbereich (--- … ---) fehlt")
    kopf, rumpf = {}, m.group(2)
    schluessel = None
    for zeile in m.group(1).splitlines():
        if not zeile.strip():
            continue
        if zeile.startswith("  - ") or zeile.startswith("- "):
            kopf.setdefault(schluessel, []).append(zeile.split("- ", 1)[1].strip())
            continue
        schluessel, _, wert = zeile.partition(":")
        schluessel, wert = schluessel.strip(), wert.strip()
        kopf[schluessel] = wert if wert else []
    fehlt = [k for k in PFLICHT if not kopf.get(k)]
    if kopf.get("typ") in ("frage", "produkt", "kosten") and not kopf.get("quellen"):
        fehlt.append("quellen")
    if fehlt:
        raise SystemExit(f"{datei}: Pflichtangaben fehlen: {', '.join(fehlt)}")
    if len(kopf["titel"]) > 52:
        raise SystemExit(f"{datei}: titel zu lang ({len(kopf['titel'])} > 52)")
    if not 80 <= len(kopf["beschreibung"]) <= 160:
        raise SystemExit(f"{datei}: beschreibung {len(kopf['beschreibung'])} Zeichen, Soll 80–160")
    return kopf, rumpf


def datum_lang(iso: str) -> str:
    j, m, t = iso.split("-")
    return f"{int(t)}. {MONATE[int(m) - 1]} {j}"


def paare(liste):
    out = []
    for eintrag in liste or []:
        a, _, b = eintrag.partition("|")
        out.append((a.strip(), b.strip()))
    return out


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def inline_md(s: str) -> str:
    """Kurzantwort/Lead: nur Fett, Kursiv und Links."""
    h = markdown.markdown(s)
    return re.sub(r"^<p>|</p>$", "", h.strip())


def strukturdaten(pfad, k, url, rumpf_text):
    seite = {
        "@type": "WebPage",
        "@id": url + "#page",
        "url": url,
        "name": k["h1"],
        "description": k["beschreibung"],
        "inLanguage": "de-DE",
        "isPartOf": {"@id": BASIS + "/#website"},
        "publisher": {"@id": BASIS + "/#business"},
        "author": {"@id": AUTOR_ID},
        "dateModified": k["stand"],
    }
    graph = [seite]
    if k["typ"] == "frage":
        seite["@type"] = ["WebPage", "FAQPage"]
        seite["mainEntity"] = {
            "@type": "Question",
            "name": k["h1"],
            "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", k["kurz"]).replace("**", "")},
        }
    elif k["typ"] == "produkt":
        produkt = {
            "@type": "Product",
            "@id": url + "#produkt",
            "name": k.get("produkt") or k["h1"],
            "description": k["beschreibung"],
            "category": "Therapeutischer Arbeitsstuhl",
        }
        if k.get("hersteller"):
            produkt["brand"] = {"@type": "Brand", "name": k["hersteller"]}
        seite["mainEntity"] = {"@id": url + "#produkt"}
        graph.append(produkt)
    elif k["typ"] == "kosten":
        seite["about"] = {"@type": "Organization", "name": k.get("traeger") or k["h1"]}
    elif k["typ"] == "person":
        seite["@type"] = "ProfilePage"
        seite["mainEntity"] = {"@id": AUTOR_ID}
        graph.append({
            "@type": "Person",
            "@id": AUTOR_ID,
            "name": "Joachim Stolz",
            "jobTitle": "Geschäftsführer",
            "worksFor": {"@id": BASIS + "/#business"},
            "url": url,
            "knowsAbout": ["Therapeutische Sitzversorgung", "Arbeitsplatzstühle bei Behinderung",
                           "Leistungen zur Teilhabe am Arbeitsleben", "Hilfsmittelversorgung"],
        })
    return {"@context": "https://schema.org", "@graph": graph}


def seite(pfad: str, k: dict, rumpf: str) -> str:
    url = BASIS + "/" + pfad
    titel = k["titel"] + " | ERGO-PLUS"
    rumpf_html = markdown.markdown(rumpf, extensions=["tables", "sane_lists"])
    # Tabellen bekommen den Rahmen der Seite
    rumpf_html = rumpf_html.replace("<table>", '<div class="table-wrap"><table class="table">').replace("</table>", "</table></div>")
    quellen = paare(k.get("quellen"))
    weiter = paare(k.get("weiter"))
    ld = json.dumps(strukturdaten(pfad, k, url, rumpf), ensure_ascii=False, indent=2)
    kurz_titel = "Kurz gesagt" if k["typ"] != "produkt" else "Auf einen Blick"
    quellen_html = ""
    if quellen:
        punkte = "\n".join(
            f'        <li><a href="{esc(u)}" rel="noopener">{esc(t)}</a></li>' for t, u in quellen)
        quellen_html = f"""
      <section class="sources" aria-labelledby="quellen-titel">
        <h2 id="quellen-titel">Quellen</h2>
        <ol>
{punkte}
        </ol>
        <p>Abgerufen und geprüft am {datum_lang(k["stand"])}. Keine Rechtsberatung: Im Einzelfall entscheidet der Kostenträger.</p>
      </section>""" if k["typ"] in ("frage", "kosten") else f"""
      <section class="sources" aria-labelledby="quellen-titel">
        <h2 id="quellen-titel">Quellen</h2>
        <ol>
{punkte}
        </ol>
        <p>Herstellerangaben, abgerufen am {datum_lang(k["stand"])}. Was davon für Sie passt, klären wir beim Probesitzen.</p>
      </section>"""
    weiter_html = "\n".join(f'      <li><a href="{esc(u)}">{esc(t)}</a></li>' for u, t in weiter)
    byline = (f'Verantwortlich für den Inhalt: <a href="{AUTOR_URL}"><strong>Joachim Stolz</strong></a>, Geschäftsführer, '
              f'über 30 Jahre in der ergotherapeutischen Sitzversorgung. Stand: <time datetime="{k["stand"]}">{datum_lang(k["stand"])}</time>')
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(titel)}</title>
  <meta name="description" content="{esc(k['beschreibung'])}" />
  <link rel="canonical" href="{url}" />
  <meta property="og:type" content="{'article' if k['typ'] in ('frage', 'kosten') else 'website'}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:title" content="{esc(titel)}" />
  <meta property="og:description" content="{esc(k['beschreibung'])}" />
  <meta property="og:image" content="{BASIS}/og-image.png" />
  <meta property="og:locale" content="de_DE" />
  <meta property="og:site_name" content="ERGO-PLUS Seating Concepts" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="icon" href="/favicon.ico" sizes="any" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
  <meta name="theme-color" content="#1a5276" />
  <link rel="alternate" type="text/plain" href="/llms.txt" title="LLM-readable summary" />
  <!-- SEITE:KOPF --><!-- /SEITE:KOPF -->
  <script type="application/ld+json">
{ld}
  </script>
</head>
<body>
<!-- SEITE:NAV --><!-- /SEITE:NAV -->
<main id="inhalt">
<!-- SEITE:KRUMEN --><!-- /SEITE:KRUMEN -->

  <header class="page-head">
    <div class="wrap page-head__grid">
      <div>
        <h1>{esc(k['h1'])}</h1>
        <p class="lead">{inline_md(k['lead'])}</p>
      </div>
      <p class="quick">Lieber gleich sprechen?<strong><a href="{TEL_HREF}">{TEL_TEXT}</a></strong>Das Erstgespräch ist kostenlos.</p>
    </div>
  </header>

  <section class="sec sec--white">
    <div class="wrap deep">
      <aside class="answer" aria-labelledby="kurz-titel">
        <h2 id="kurz-titel">{kurz_titel}</h2>
        <p>{inline_md(k['kurz'])}</p>
      </aside>
      <div class="prose">
{rumpf_html}
      </div>{quellen_html}
    </div>
  </section>

  <div class="wrap sec--tight"><div class="measure">
    <nav class="further" aria-labelledby="weiter-titel">
    <h2 id="weiter-titel">Weiterführend</h2>
    <ul>
{weiter_html}
    </ul>
  </nav>
    <p class="byline">{byline}</p>
  </div></div>
</main>
<!-- SEITE:FUSS --><!-- /SEITE:FUSS -->
</body>
</html>
"""


def fragen_liste(alle) -> str:
    """Block für faq.html: alle ausführlich beantworteten Fragen, nach Kategorie."""
    gruppen = {}
    for pfad, k in alle:
        if k["typ"] == "frage":
            gruppen.setdefault(k.get("kategorie", "Weitere Fragen"), []).append((pfad, k))
    teile = []
    for name, eintraege in gruppen.items():
        punkte = "\n".join(
            f'          <li><a href="/{p}">{esc(k["h1"])}</a><span>{esc(re.sub(r"[*]|\[([^\]]+)\]\([^)]+\)", r"\1", k["kurz"]).split(". ")[0].rstrip(".") + ".")}</span></li>'
            for p, k in sorted(eintraege, key=lambda e: e[1]["h1"]))
        teile.append(f"""        <div class="qlist__group">
          <h3>{esc(name)}</h3>
          <ul class="qlist">
{punkte}
          </ul>
        </div>""")
    return "\n" + "\n".join(teile) + "\n        "


def main():
    pruefen = "--pruefen" in sys.argv
    alle, abweichend = [], []
    for datei in sorted(QUELLE.rglob("*.md")):
        rel = datei.relative_to(QUELLE).with_suffix(".html").as_posix()
        k, rumpf = lesen(datei)
        alle.append((rel, k))
        neu = seite(rel, k, rumpf)
        ziel = WURZEL / rel
        if ziel.exists():
            # Rahmen setzt bauen.py; verglichen wird nur, was außerhalb der Marker steht.
            alt = ziel.read_text(encoding="utf-8")
            ohne = lambda s: re.sub(r"(<!-- SEITE:(\w+) -->).*?(<!-- /SEITE:\2 -->)", r"\1\3", s, flags=re.S)
            if ohne(alt) == ohne(neu):
                continue
        if pruefen:
            abweichend.append(f"{rel}: weicht von der Markdown-Quelle ab")
        else:
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(neu, encoding="utf-8")

    # Liste der ausführlichen Antworten in faq.html
    faq = WURZEL / "faq.html"
    q = faq.read_text(encoding="utf-8")
    a, z = "<!-- TIEF:FRAGEN -->", "<!-- /TIEF:FRAGEN -->"
    if a in q:
        neu_q = re.sub(re.escape(a) + ".*?" + re.escape(z), lambda _: a + fragen_liste(alle) + z, q, flags=re.S)
        if neu_q != q:
            if pruefen:
                abweichend.append("faq.html: Fragenliste veraltet")
            else:
                faq.write_text(neu_q, encoding="utf-8")

    if abweichend:
        print("\n".join(abweichend))
        print("\n→ python3 tools/seiten/tief.py und danach tools/seiten/bauen.py ausführen.")
        sys.exit(1)
    print(f"{len(alle)} tiefe Seiten {'geprüft' if pruefen else 'gebaut'}.")


if __name__ == "__main__":
    main()
