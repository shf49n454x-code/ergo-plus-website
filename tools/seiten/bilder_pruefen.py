#!/usr/bin/env python3
"""Prüft jedes <img> auf jeder Seite (Wurzel und blog/).

Übernommen von jonpride.de (scripts/bilder_pruefen.py), erweitert um WebP,
weil hier fast alle Bilder WebP sind, und um srcset-Dateien.

Drei Fehler, die keine Fehlermeldung werfen und trotzdem sichtbar sind:
  1. Datei fehlt                   -> leeres Bild
  2. width/height fehlen           -> Inhalt springt beim Laden (CLS)
  3. width/height passen nicht     -> Kasten im falschen Seitenverhältnis,
     zum Seitenverhältnis der Datei   Bild verzerrt oder falsch beschnitten

Die Maße kommen aus dem Dateikopf, ohne Bibliothek. Exitcode 1 bei Befund.

    python3 tools/seiten/bilder_pruefen.py
"""
import pathlib
import re
import struct
import sys

WURZEL = pathlib.Path(__file__).resolve().parents[2]


def masse(pfad: pathlib.Path):
    d = pfad.read_bytes()[:64 * 1024]
    if d[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", d[16:24])
    if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
        art = d[12:16]
        if art == b"VP8X":
            w = int.from_bytes(d[24:27], "little") + 1
            h = int.from_bytes(d[27:30], "little") + 1
            return w, h
        if art == b"VP8 ":
            w, h = struct.unpack("<HH", d[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if art == b"VP8L":
            b = int.from_bytes(d[21:25], "little")
            return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
        return None
    if d[:2] == b"\xff\xd8":
        i = 2
        while i < len(d) - 9:
            if d[i] != 0xFF:
                i += 1
                continue
            m = d[i + 1]
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                i += 2
                continue
            laenge = struct.unpack(">H", d[i + 2:i + 4])[0]
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", d[i + 5:i + 9])
                return w, h
            i += 2 + laenge
    return None  # SVG, GIF: nicht geprüft


def datei(seite: pathlib.Path, roh: str) -> pathlib.Path:
    roh = roh.split("?")[0]
    if roh.startswith("/"):
        return WURZEL / roh.lstrip("/")
    return (seite.parent / roh).resolve()


def pruefe(seite: pathlib.Path):
    text = seite.read_text(encoding="utf-8")
    befunde = []
    for t in re.finditer(r"<img\b[^>]*>", text, re.S):
        tag = t.group(0)
        q = re.search(r'\ssrc="([^"]+)"', tag)
        if not q:
            befunde.append(("kein src", tag[:70]))
            continue
        roh = q.group(1)
        if roh.startswith(("http://", "https://", "data:")):
            continue
        pfad = datei(seite, roh)
        if not pfad.exists():
            befunde.append(("Datei fehlt", roh))
            continue
        if not re.search(r'\salt="', tag):
            befunde.append(("kein alt-Attribut", roh))
        ss = re.search(r'srcset="([^"]+)"', tag)
        if ss:
            for teil in ss.group(1).split(","):
                u = teil.strip().split(" ")[0]
                if u and not datei(seite, u).exists():
                    befunde.append(("srcset-Datei fehlt", u))
            if "sizes=" not in tag:
                befunde.append(("srcset ohne sizes", roh))
        b = re.search(r'\swidth="(\d+)"', tag)
        h = re.search(r'\sheight="(\d+)"', tag)
        if not (b and h):
            befunde.append(("width/height fehlen", roh))
            continue
        echt = masse(pfad)
        if not echt:
            continue
        soll = echt[0] / echt[1]
        ist = int(b.group(1)) / int(h.group(1))
        if abs(ist - soll) / soll > 0.01:
            befunde.append((f"Seitenverhältnis {ist:.3f} laut Angabe, {soll:.3f} laut Datei ({echt[0]}x{echt[1]})", roh))
    return befunde


def main():
    seiten = sorted(WURZEL.glob("*.html")) + sorted((WURZEL / "blog").glob("*.html"))
    n = 0
    for s in seiten:
        for grund, wo in pruefe(s):
            print(f"{s.relative_to(WURZEL)}: {grund} – {wo}")
            n += 1
    if n:
        print(f"\n{n} Befunde.")
        return 1
    print(f"{len(seiten)} Seiten geprüft, alle Bilder in Ordnung.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
