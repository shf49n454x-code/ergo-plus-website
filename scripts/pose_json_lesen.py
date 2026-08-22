#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Liest den maschinenlesbaren POSE-JSON-Block aus einer POSE-Bogen-Mail
(oder einer .json-Datei aus dem "Sichern"-Knopf in pose-bogen.html) und
gibt strukturierte, geprüfte Daten aus.

Aufruf:
    python3 scripts/pose_json_lesen.py < mail.txt
    python3 scripts/pose_json_lesen.py mail.txt
    python3 scripts/pose_json_lesen.py POSE_Mustermann_2026-08-20.json
"""
import json
import sys

MARKER = "POSE-JSON v1: "

BEKANNTE_FELDER = {
    "datum", "nur_kv",
    "p_name", "p_strasse", "p_plz", "p_stadt", "p_telefon", "p_fax",
    "l_firma", "l_strasse", "l_plz", "l_stadt", "l_telefon", "l_fax", "l_email",
    "beruf", "pc_prozent", "schreiben_prozent", "telefon_prozent",
    "anders_prozent", "anders_text",
    "beschwerden", "klinik_von", "klinik_bis", "krank_tage",
    "skoliose", "skoliose_grad", "wollallergie",
    "alter", "gewicht", "geschlecht", "koerpergroesse",
    "mass_a", "mass_b", "mass_c", "mass_d", "mass_e", "mass_f", "mass_h",
    "lws", "boden", "boden_andere", "polsterfarbe", "erfahren",
}


class PoseJsonFehler(Exception):
    pass


def json_block_extrahieren(text):
    """Findet die Zeile 'POSE-JSON v1: {...}' im Mail-/Dateitext und gibt
    das geparste dict zurueck. Wirft PoseJsonFehler, wenn nichts gefunden
    oder das JSON kaputt ist."""
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if zeile.startswith(MARKER):
            roh = zeile[len(MARKER):]
            try:
                return json.loads(roh)
            except json.JSONDecodeError as e:
                raise PoseJsonFehler(f"POSE-JSON-Block gefunden, aber nicht lesbar: {e}") from e

    text_getrimmt = text.strip()
    if text_getrimmt.startswith("{"):
        try:
            return json.loads(text_getrimmt)
        except json.JSONDecodeError:
            pass

    raise PoseJsonFehler(
        f"Kein '{MARKER.strip()}'-Block gefunden und der Text ist kein reines JSON-Objekt."
    )


def validieren(daten):
    """Prueft grob auf Plausibilitaet und meldet Auffaelligkeiten - bricht
    aber nicht ab."""
    warnungen = []

    unbekannt = set(daten) - BEKANNTE_FELDER
    if unbekannt:
        warnungen.append(f"Unbekannte Felder (neuere Bogen-Version?): {sorted(unbekannt)}")

    prozente = [daten.get(k) for k in
                ("pc_prozent", "schreiben_prozent", "telefon_prozent", "anders_prozent")]
    summe = sum(int(p) for p in prozente if str(p).strip().isdigit())
    if summe and summe != 100:
        warnungen.append(f"Zeitaufteilung ergibt {summe} %, nicht 100 %")

    if not daten.get("p_name") and not daten.get("l_firma"):
        warnungen.append("Weder Name noch Firma angegeben - Bogen kaum zuordenbar")

    return warnungen


def zusammenfassung(daten):
    """Kurze, fuer Menschen lesbare Zeile."""
    wer = daten.get("p_name") or daten.get("l_firma") or "unbekannt"
    datum = daten.get("datum", "ohne Datum")
    kv = " (nur Kostenvoranschlag)" if daten.get("nur_kv") else ""
    return f"POSE-Bogen {wer} vom {datum}{kv}"


def main(argv):
    if len(argv) > 1:
        with open(argv[1], "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    try:
        daten = json_block_extrahieren(text)
    except PoseJsonFehler as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1

    for warnung in validieren(daten):
        print(f"Hinweis: {warnung}", file=sys.stderr)

    print(zusammenfassung(daten))
    print(json.dumps(daten, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
