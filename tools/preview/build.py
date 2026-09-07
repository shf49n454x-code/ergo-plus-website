#!/usr/bin/env python3
"""Baut aus dem Repository eine Vorschau fuer GitHub Pages.

Aufruf:  python3 tools/preview/build.py <zielverzeichnis>

Die Vorschau ist dieselbe Seite, aber an drei Stellen anders. Jede dieser
drei Abweichungen hat einen Grund, der nicht offensichtlich ist:

1. Pages liegt unter /ergo-plus-website/, nicht auf der Domainwurzel.
   Ohne Praefix laedt kein Bild und keine Schrift.

2. Die Vorschau darf nicht in den Index. Sie ist eine vollstaendige Kopie
   der Seite; ohne noindex konkurriert sie bei Google mit ergo-plus.de.
   Genau das war lange der Fall - die robots.txt erlaubte dort das Crawlen.

3. Quelldateien und PHP fliegen raus. details/, originals/ und
   team-originals/ sind Ausgangsmaterial, auf das keine Seite verweist:
   34 MB, die sonst oeffentlich abrufbar mitliefen. Und Pages fuehrt kein
   PHP aus, sondern wuerde kontakt.php als Klartext ausliefern.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

PREFIX = "/ergo-plus-website"

# Verzeichnisse, die in der Vorschau nichts zu suchen haben. Entweder
# Werkzeug (nicht Teil der Website) oder Quellmaterial ohne Verweis.
RAUS = [
    ".git", ".github", ".claude", "tools", "scripts", "data", "node_modules",
    "details", "originals", "team-originals",
]
RAUS_DATEIEN = ["kontakt.php", ".gitignore", ".htaccess", "_headers"]

# Alle Markdown-Dateien und die npm-Dateien im Wurzelverzeichnis sind
# interne Dokumentation bzw. Werkzeug. Sie gehoeren nicht auf eine
# oeffentliche Vorschau - einzeln aufzaehlen hiesse, die naechste zu
# vergessen.
def _intern(name: str) -> bool:
    return name.endswith(".md") or name.startswith("package")

ATTRIBUT = re.compile(r'\b(href|src|action|poster)="(/(?!/)[^"]*)"')
SRCSET = re.compile(r'\bsrcset="([^"]*)"')
CSS_URL = re.compile(r'url\((["\']?)(/(?!/)[^)"\']*)\1\)')
ROBOTS_META = re.compile(r'<meta\s+name="robots"[^>]*>')

ROBOTS_TXT = (
    "# Vorschau-Kopie unter github.io - nicht die echte Seite.\n"
    "# Ohne diese Sperre konkurriert sie bei Google mit ergo-plus.de.\n"
    "User-agent: *\n"
    "Disallow: /\n"
)


def _srcset(treffer: re.Match) -> str:
    teile = []
    for eintrag in treffer.group(1).split(","):
        eintrag = eintrag.strip()
        if eintrag.startswith("/") and not eintrag.startswith("//"):
            eintrag = PREFIX + eintrag
        teile.append(eintrag)
    return 'srcset="' + ", ".join(teile) + '"'


def _css_url(treffer: re.Match) -> str:
    return f"url({treffer.group(1)}{PREFIX}{treffer.group(2)}{treffer.group(1)})"


def html_umbauen(text: str) -> str:
    text = ATTRIBUT.sub(lambda m: f'{m.group(1)}="{PREFIX}{m.group(2)}"', text)
    text = SRCSET.sub(_srcset, text)
    text = CSS_URL.sub(_css_url, text)

    if ROBOTS_META.search(text):
        text = ROBOTS_META.sub(
            '<meta name="robots" content="noindex, nofollow" />', text, count=1)
        text = ROBOTS_META.sub("", text)      # etwaige Dubletten entfernen
    else:
        text = text.replace(
            "</head>",
            '  <meta name="robots" content="noindex, nofollow" />\n</head>', 1)
    return text


def bauen(quelle: Path, ziel: Path) -> int:
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True)

    for eintrag in quelle.iterdir():
        if eintrag.name in RAUS or eintrag.name in RAUS_DATEIEN:
            continue
        if eintrag.is_file() and _intern(eintrag.name):
            continue
        if eintrag.is_dir():
            shutil.copytree(eintrag, ziel / eintrag.name, symlinks=True)
        else:
            shutil.copy2(eintrag, ziel / eintrag.name)

    geaendert = 0
    for datei in sorted(ziel.rglob("*.html")):
        alt = datei.read_text(encoding="utf-8")
        neu = html_umbauen(alt)
        if neu != alt:
            datei.write_text(neu, encoding="utf-8")
            geaendert += 1

    css = ziel / "assets/fonts/fonts.css"
    if css.is_file():
        alt = css.read_text(encoding="utf-8")
        neu = CSS_URL.sub(_css_url, alt)
        if neu != alt:
            css.write_text(neu, encoding="utf-8")
            geaendert += 1

    (ziel / "robots.txt").write_text(ROBOTS_TXT, encoding="utf-8")
    return geaendert


def pruefen(ziel: Path) -> list[str]:
    """Kein Verweis darf ins Leere zeigen oder das Praefix vergessen.

    Ein falscher Pfad faellt in der Vorschau nicht auf - die Seite laedt,
    nur das Bild fehlt. Deshalb hier nachrechnen statt hinsehen.
    """
    befunde = []
    attr = re.compile(r'\b(href|src|action|poster)="([^"]*)"')
    for datei in sorted(ziel.rglob("*.html")):
        text = datei.read_text(encoding="utf-8")
        ziele = [m.group(2) for m in attr.finditer(text)]
        for m in SRCSET.finditer(text):
            ziele += [e.strip().split()[0] for e in m.group(1).split(",") if e.strip()]
        for z in ziele:
            if not z.startswith("/") or z.startswith("//"):
                continue
            if not z.startswith(PREFIX + "/"):
                befunde.append(f"{datei.name}: {z} ohne Praefix")
                continue
            rest = z[len(PREFIX) + 1:].split("#")[0].split("?")[0]
            if rest and not (ziel / rest).exists():
                befunde.append(f"{datei.name}: {z} zeigt ins Leere")
    return befunde


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Aufruf: build.py <zielverzeichnis>")
    quelle = Path(__file__).resolve().parents[2]
    ziel = Path(sys.argv[1]).resolve()
    if ziel == quelle or quelle in ziel.parents:
        sys.exit("Ziel darf nicht im Repository liegen.")

    geaendert = bauen(quelle, ziel)
    befunde = pruefen(ziel)
    print(f"{geaendert} Dateien umgeschrieben.")
    if befunde:
        print(f"\n{len(befunde)} Befund(e):")
        for b in befunde[:20]:
            print("  -", b)
        sys.exit(1)
    print("Alle Verweise tragen das Praefix und zeigen auf vorhandene Dateien.")


if __name__ == "__main__":
    main()
