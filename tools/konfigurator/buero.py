#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERGO-PLUS Büro-Werkzeug für den Konfigurator.

Holt verschlüsselte Vorgänge vom Webserver, entschlüsselt sie lokal und baut
daraus die Arbeitsunterlagen: Kostenvoranschlag-Entwurf, Begründung für den
Kostenträger, Vorlage für die ärztliche Stellungnahme, Montage-Checkliste für
Philip und eine POSE-JSON-Datei (kompatibel zu scripts/pose_json_lesen.py).

Der private Schlüssel verlässt nie diesen Rechner.

    python3 buero.py schluessel             # einmalig: Schlüsselpaar erzeugen
    python3 buero.py token                  # einmalig: Abhol-Token für den Server
    python3 buero.py abholen                # neue Vorgänge holen + Unterlagen bauen
    python3 buero.py entschluesseln DATEI   # einzelnen Umschlag lokal öffnen
    python3 buero.py dokumente ORDNER       # Unterlagen eines Vorgangs neu bauen
    python3 buero.py waechter               # Eskalation: Stau, Lücken, Rückrufe

Einstellungen über Umgebungsvariablen (oder ~/.ergo-plus/einstellungen.env):
    ERGO_URL               https://ergo-plus.de
    ERGO_SCHLUESSEL_PASS   Passwort des privaten Schlüssels
    ERGO_ABLAGE            Zielordner der Vorgänge (Standard: ./vorgaenge)
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   Meldungen aufs Handy (optional)
    ERGO_ANRUF_WEBHOOK     URL, die bei dringender Eskalation einen Anruf auslöst (optional)
"""
import argparse
import base64
import datetime as dt
import getpass
import hashlib
import html
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover
    sys.exit("Bitte zuerst installieren:  pip install cryptography")

HIER = Path(__file__).resolve().parent
REPO = HIER.parent.parent
KONFIG = Path.home() / ".ergo-plus"
PRIVAT = KONFIG / "privat.pem"
TOKEN_DATEI = KONFIG / "abhol-token"
OEFFENTLICH = REPO / "konfigurator" / "oeffentlicher-schluessel.json"
KATALOG = REPO / "konfigurator" / "katalog.json"

FIRMA = {
    "name": "ERGO plus Seating Concepts GmbH",
    "ort": "63867 Johannesberg",
    "telefon": "+49 6021 12807",
    "email": "info@ergo-plus.de",
    "register": "Amtsgericht Aschaffenburg, HRB 12470",
    "gf": "Joachim Stolz",
}


# ── Einstellungen ───────────────────────────────────────────────────
def env_laden():
    datei = KONFIG / "einstellungen.env"
    if datei.is_file():
        for zeile in datei.read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if zeile and not zeile.startswith("#") and "=" in zeile:
                k, v = zeile.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def ablage() -> Path:
    p = Path(os.environ.get("ERGO_ABLAGE", HIER / "vorgaenge"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def b64u(n: int) -> str:
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def passwort(neu=False) -> bytes:
    pw = os.environ.get("ERGO_SCHLUESSEL_PASS")
    if not pw:
        pw = getpass.getpass("Passwort für den privaten Schlüssel: ")
        if neu and pw != getpass.getpass("Wiederholen: "):
            sys.exit("Passwörter stimmen nicht überein.")
    if neu and len(pw) < 12:
        sys.exit("Bitte mindestens 12 Zeichen.")
    return pw.encode()


# ── Schlüssel & Token ───────────────────────────────────────────────
def cmd_schluessel(args):
    if PRIVAT.exists() and not args.ueberschreiben:
        sys.exit(f"{PRIVAT} existiert bereits. Mit --ueberschreiben neu erzeugen "
                 "(alte, noch nicht abgeholte Vorgänge sind dann NICHT mehr lesbar).")
    KONFIG.mkdir(mode=0o700, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.BestAvailableEncryption(passwort(neu=True)))
    PRIVAT.write_bytes(pem)
    os.chmod(PRIVAT, 0o600)
    pub = key.public_key().public_numbers()
    kid = hashlib.sha256(pub.n.to_bytes(384, "big")).hexdigest()[:16]
    jwk = {"kty": "RSA", "alg": "RSA-OAEP-256", "use": "enc", "kid": kid,
           "n": b64u(pub.n), "e": b64u(pub.e),
           "erzeugt": dt.date.today().isoformat()}
    ziel = Path(args.ausgabe) if args.ausgabe else OEFFENTLICH
    ziel.write_text(json.dumps(jwk, indent=2) + "\n", encoding="utf-8")
    print(f"Privater Schlüssel: {PRIVAT}  (Sicherungskopie offline ablegen, z. B. USB-Stick im Tresor)")
    print(f"Öffentlicher Schlüssel: {ziel}  → committen und hochladen")
    print(f"Schlüssel-ID: {kid}")


def cmd_token(args):
    KONFIG.mkdir(mode=0o700, exist_ok=True)
    token = secrets.token_urlsafe(32)
    TOKEN_DATEI.write_text(token, encoding="utf-8")
    os.chmod(TOKEN_DATEI, 0o600)
    print(f"Token gespeichert in {TOKEN_DATEI}")
    print("In api/einstellungen-lokal.php auf dem Server eintragen:")
    print(f"  define('TOKEN_SHA256', '{hashlib.sha256(token.encode()).hexdigest()}');")
    print(f"  define('BREMSE_SALZ', '{secrets.token_hex(16)}');")


def privater_schluessel():
    if not PRIVAT.is_file():
        sys.exit(f"Kein privater Schlüssel unter {PRIVAT}. Erst: buero.py schluessel")
    return serialization.load_pem_private_key(PRIVAT.read_bytes(), password=passwort())


# ── Entschlüsseln ───────────────────────────────────────────────────
def entschluesseln(umschlag: dict, key) -> dict:
    if umschlag.get("format") != "ergo-umschlag/1":
        raise ValueError("Unbekanntes Umschlag-Format")
    aes = key.decrypt(base64.b64decode(umschlag["schluessel"]),
                      padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    klar = AESGCM(aes).decrypt(base64.b64decode(umschlag["iv"]), base64.b64decode(umschlag["daten"]),
                               umschlag["id"].encode())
    daten = json.loads(klar)
    if daten.get("id") != umschlag["id"]:
        raise ValueError("ID im Inhalt passt nicht zum Umschlag")
    return daten


def sicherer_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9ÄÖÜäöüß._-]+", "-", s or "").strip("-")[:60] or "ohne-name"


def vorgang_ablegen(daten: dict, basis: Path) -> Path:
    name = sicherer_name(daten.get("pose", {}).get("p_name", ""))
    ordner = basis / f"{daten['vorgang']}_{name}" / daten["modus"]
    (ordner / "fotos").mkdir(parents=True, exist_ok=True)
    fotos = []
    for i, f in enumerate(daten.get("fotos", []), 1):
        m = re.match(r"data:image/(\w+);base64,(.*)", f.get("bild", ""), re.S)
        if not m:
            continue
        datei = ordner / "fotos" / f"{i:02d}-{sicherer_name(f.get('label'))}.{'jpg' if m.group(1) == 'jpeg' else m.group(1)}"
        datei.write_bytes(base64.b64decode(m.group(2)))
        fotos.append({"label": f.get("label"), "datei": str(datei.relative_to(ordner))})
    u = daten.get("unterschrift") or {}
    if u.get("bild", "").startswith("data:image/png;base64,"):
        (ordner / "unterschrift.png").write_bytes(base64.b64decode(u["bild"].split(",", 1)[1]))
        u = dict(u, bild="unterschrift.png")
    ohne_bilder = dict(daten, fotos=fotos, unterschrift=u)
    (ordner / "daten.json").write_text(json.dumps(ohne_bilder, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(ordner / "daten.json", 0o600)
    dokumente_bauen(ordner)
    return ordner


# ── Unterlagen ──────────────────────────────────────────────────────
def eur(x) -> str:
    s = f"{float(x or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " €"


def zahl(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def schriften():
    """Hausschriften aus dem Repo einbetten (PDF sieht dann aus wie die Website)."""
    f = REPO / "assets" / "fonts"
    regeln = []
    for fam, datei, w in [("Figtree", "figtree-latin-700-normal.woff2", 700), ("Figtree", "figtree-latin-800-normal.woff2", 800),
                          ("Noto Sans", "noto-sans-latin-400-normal.woff2", 400), ("Noto Sans", "noto-sans-latin-700-normal.woff2", 700)]:
        if (f / datei).is_file():
            regeln.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('{(f / datei).as_uri()}') format('woff2')}}")
    return "".join(regeln)


STIL = """<style>
@page{size:A4;margin:18mm 16mm}body{font-family:'Noto Sans',Arial,sans-serif;font-size:10.5pt;color:#1a2a3a;line-height:1.45}
h1{font-family:Figtree,Arial,sans-serif;color:#1a5276;font-size:17pt;margin:0 0 2mm}h2{font-family:Figtree,Arial,sans-serif;color:#1a5276;font-size:11.5pt;margin:6mm 0 2mm;border-bottom:.5pt solid #c8dae8;padding-bottom:1mm}
.kopf{display:flex;justify-content:space-between;border-bottom:2pt solid #1a5276;padding-bottom:3mm;margin-bottom:6mm}.kopf .f{font-size:9pt;color:#5d6d7e;text-align:right}
.entwurf{background:#fef3cd;color:#8a5606;border-radius:4px;padding:2mm 3mm;font-weight:700;margin-bottom:4mm}
table{width:100%;border-collapse:collapse}td,th{padding:1.6mm 1mm;vertical-align:top;text-align:left}th{font-size:8.5pt;text-transform:uppercase;color:#5d6d7e;border-bottom:1pt solid #1a5276}
td.z,th.z{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}tbody tr td{border-bottom:.4pt solid #e2ecf4}
tr.summe td{font-weight:700}tr.gesamt td{font-size:12pt;font-weight:800;color:#1a5276;border-top:1.2pt solid #1a5276}
.kv td:first-child{color:#5d6d7e;width:38%}.box{border:.6pt solid #c8dae8;border-radius:4px;padding:3mm;min-height:22mm}
.cb{display:inline-block;width:3.6mm;height:3.6mm;border:.8pt solid #1a2a3a;margin-right:2mm;vertical-align:-.6mm}
.fuss{margin-top:10mm;font-size:8pt;color:#5d6d7e;border-top:.4pt solid #c8dae8;padding-top:2mm}.sig{height:16mm}
</style>"""


def seite(titel, inhalt, entwurf=True):
    f = FIRMA
    return ("<!doctype html><html lang='de'><head><meta charset='utf-8'><title>" + e(titel) + "</title><style>" + schriften() + "</style>" + STIL + "</head><body>"
            f"<div class='kopf'><div><b style='font-family:Figtree,Arial;color:#1a5276;font-size:13pt'>ERGO plus</b><br>Seating Concepts GmbH</div>"
            f"<div class='f'>{e(f['ort'])}<br>{e(f['telefon'])} · {e(f['email'])}</div></div>"
            + ("<div class='entwurf'>ENTWURF – vor Versand von Joachim prüfen</div>" if entwurf else "")
            + inhalt +
            f"<div class='fuss'>{e(f['name'])} · {e(f['register'])} · Geschäftsführer: {e(f['gf'])}</div></body></html>")


def adresse(p):
    return "<br>".join(x for x in [e(p.get("p_name")), e(p.get("p_strasse")), e(" ".join(filter(None, [p.get("p_plz"), p.get("p_stadt")])))] if x)


def richtwerte(p, zusatz=None):
    """Einstell-Richtwerte aus den POSE-Maßen. Bewusst grob – Joachim entscheidet."""
    b, f, c, h = (zahl(p.get(k)) for k in ("mass_b", "mass_f", "mass_c", "mass_h"))
    r = []
    if b:
        r.append(("Sitzhöhe (Oberkante Polster)", f"ca. {b + (f or 0):.0f} cm", "B + F"))
    kw = zahl((zusatz or {}).get("kw_sitzhoehe"))
    if kw:
        r.append(("Sitzhöhe laut Ergänzung Kleinwuchs", f"{kw:.0f} cm", "Arbeitsplatz – hat Vorrang"))
    if c:
        r.append(("Sitztiefe", f"ca. {max(c - 6, 0):.0f} cm", "C − 5 bis 8 cm"))
    if h:
        r.append(("Armlehnenhöhe über Sitz", f"ca. {h:.0f} cm", "H"))
    lws = p.get("lws")
    if lws:
        r.append(("Lordosenstütze", {"flach": "flach / tief", "medium": "mittel", "stark gewölbt": "kräftig / höher"}.get(lws, lws), "G"))
    return r


def doc_kv(d):
    p, a, k = d.get("pose", {}), d.get("angebot") or {}, d.get("kostentraeger") or {}
    pos = a.get("positionen", [])
    s = a.get("summen", {})
    zeilen = "".join(f"<tr><td>{i}</td><td>{e(x['name'])}</td><td class='z'>{eur(x.get('netto'))}</td></tr>" for i, x in enumerate(pos, 1))
    warn = "<div class='entwurf'>Enthält BEISPIELPREISE aus dem Katalog – Preise prüfen.</div>" if a.get("beispielpreise") else ""
    inhalt = (f"<table><tr><td style='width:55%'>{adresse(p)}</td><td class='kv'><table class='kv'>"
              f"<tr><td>Vorgang</td><td>{e(d['vorgang'])}</td></tr><tr><td>Datum</td><td>{e(p.get('datum'))}</td></tr>"
              f"<tr><td>Kostenträger</td><td>{e(k.get('traeger'))}</td></tr><tr><td>Aktenzeichen</td><td>{e(k.get('aktenzeichen'))}</td></tr></table></td></tr></table>"
              f"<h1 style='margin-top:6mm'>Kostenvoranschlag</h1>{warn}"
              f"<p>Individuelle Sitzversorgung für {e(p.get('p_name'))}, ermittelt bei der Beratung und Vermessung vor Ort.</p>"
              f"<table><thead><tr><th>Pos.</th><th>Leistung</th><th class='z'>Netto</th></tr></thead><tbody>{zeilen}</tbody>"
              f"<tfoot><tr class='summe'><td></td><td>Summe netto</td><td class='z'>{eur(s.get('netto'))}</td></tr>"
              f"<tr><td></td><td>zzgl. MwSt {e(a.get('mwst'))} %</td><td class='z'>{eur(s.get('mwst'))}</td></tr>"
              f"<tr class='gesamt'><td></td><td>Gesamtbetrag brutto</td><td class='z'>{eur(s.get('brutto'))}</td></tr></tfoot></table>"
              "<p style='margin-top:6mm'>Die Versorgung umfasst Lieferung frei Verwendungsstelle, Einstellung, Anpassung und Einweisung vor Ort. "
              "Der Kostenvoranschlag ist 3 Monate gültig. Produktion beginnt nach Eingang der Kostenzusage.</p>")
    return seite("Kostenvoranschlag " + d["vorgang"], inhalt)


TEXTBAUSTEINE = {
    "mfs": "Aufgrund der Wirbelsäulenverkrümmung ist eine konventionelle Sitzgelegenheit nicht geeignet. Das MFS-Stuhlsystem wird mit Visco-Elementen individuell an die Körperkontur angepasst, entlastet die Wirbelsäule und ermöglicht ein schmerzarmes, längeres Sitzen am Arbeitsplatz.",
    "kleinwuchs": "Handelsübliche Arbeitsstühle sind für die Körpermaße nicht nutzbar: Sitzhöhe, Sitztiefe und Fußauflage passen nicht. Erforderlich ist eine Sitzlösung mit angepasster Sitzgeometrie und Fußabstützung, damit am vorhandenen Arbeitsplatz ergonomisch und ohne Fremdhilfe gearbeitet werden kann.",
    "schwer": "Das Körpergewicht übersteigt die zulässige Belastung handelsüblicher Bürostühle. Benötigt wird ein geprüfter Schwerlaststuhl mit verstärkter Mechanik und breiterer Sitzfläche, um sicheres Sitzen und Aufstehen zu gewährleisten.",
    "aufsteh": "Das selbstständige Aufstehen und Hinsetzen ist eingeschränkt. Die motorische Aufstehhilfe mit Bremse ermöglicht einen sicheren Positionswechsel und eine abgestützte Fortbewegung im Sitzen und senkt das Sturzrisiko.",
    "arthrodese": "Aufgrund der Versteifung bzw. Prothesenversorgung ist ein Sitzen auf einer durchgehenden Sitzfläche nicht beschwerdefrei möglich. Die geteilte Sitzfläche lässt sich seitengetrennt einstellen und entlastet die betroffene Seite.",
    "motor": "Die Mobilität im Innenbereich ist eingeschränkt. Der motorisierte Stuhl ermöglicht Höhen-, Sitz- und Rückenverstellung sowie Fortbewegung auf engem Raum ohne Fremdhilfe.",
    "ergo": "Die bestehenden Beschwerden erfordern einen orthopädisch einstellbaren Arbeitsstuhl, der auf die gemessenen Körpermaße angepasst wird, um Fehlhaltungen und Ausfallzeiten zu vermeiden.",
}


def doc_begruendung(d):
    p, v, k, z = d.get("pose", {}), d.get("versorgung") or {}, d.get("kostentraeger") or {}, d.get("zusatz") or {}
    linie = (v.get("linie") or {}).get("id", "ergo")
    massen = ", ".join(f"{x.upper()} {p['mass_' + x]} cm" for x in "abcdefh" if p.get("mass_" + x))
    try:
        titel = {k: v["titel"].replace("Ergänzung ", "") for k, v in json.loads(KATALOG.read_text(encoding="utf-8"))["zusatzboegen"].items()}
    except Exception:
        titel = {}
    zus = ", ".join(titel.get(x, x) for x in z.get("aktiv", []))
    opts = "".join(f"<li>{e(o['name'])}</li>" for o in v.get("optionen", []))
    inhalt = (f"<p>An: {e(k.get('traeger'))}{(' – ' + e(k.get('ansprechpartner'))) if k.get('ansprechpartner') else ''}<br>Aktenzeichen: {e(k.get('aktenzeichen'))}</p>"
              f"<h1>Begründung der Hilfsmittelversorgung</h1><p><b>Versicherte Person:</b> {e(p.get('p_name'))}, {e(p.get('beruf'))}</p>"
              f"<h2>Ausgangslage</h2><p>{e(p.get('beschwerden'))}</p>"
              f"<p>Körpergröße {e(p.get('koerpergroesse'))} cm, Gewicht {e(p.get('gewicht'))} kg. Maße: {e(massen)}."
              + (f" Skoliose {e(p.get('skoliose_grad'))}°." if p.get("skoliose") == "Ja" else "")
              + (f" Krankheitstage wegen Rückenbeschwerden im letzten Jahr: {e(p.get('krank_tage'))}." if p.get("krank_tage") else "") + "</p>"
              f"<h2>Erforderliche Versorgung</h2><p>{e(TEXTBAUSTEINE.get(linie, TEXTBAUSTEINE['ergo']))}</p>"
              f"<p><b>Modell:</b> {e((v.get('modell') or {}).get('name'))}</p>" + (f"<ul>{opts}</ul>" if opts else "")
              + (f"<p>Ergänzend erfasst (Ergänzungsbogen): {e(zus)}. Details im beigefügten POSE-Bogen.</p>" if zus else "")
              + "<h2>Warum keine einfachere Lösung</h2><p>[Joachim: konkret ergänzen – z. B. welche Stühle erprobt wurden und warum sie nicht geeignet waren.]</p>"
              "<p>Die Anpassung erfolgt vor Ort mit Einstellung und Einweisung. Für Rückfragen stehen wir gern zur Verfügung.</p>")
    return seite("Begründung " + d["vorgang"], inhalt)


def doc_arzt(d):
    p = d.get("pose", {})
    inhalt = (f"<h1>Ärztliche Stellungnahme zur Hilfsmittelversorgung</h1>"
              f"<p>Vorausgefüllt von ERGO-PLUS zur Vorlage bei der behandelnden Ärztin / dem behandelnden Arzt. Vorgang {e(d['vorgang'])}.</p>"
              f"<table class='kv'><tr><td>Patient/in</td><td>{e(p.get('p_name'))}</td></tr><tr><td>Anschrift</td><td>{adresse(p)}</td></tr>"
              f"<tr><td>Beruf</td><td>{e(p.get('beruf'))}</td></tr><tr><td>Angaben laut Beratung</td><td>{e(p.get('beschwerden'))}</td></tr></table>"
              "<h2>Diagnose(n) mit ICD-10</h2><div class='box'></div>"
              "<h2>Funktionseinschränkungen beim Sitzen am Arbeitsplatz</h2><div class='box'></div>"
              "<h2>Medizinische Notwendigkeit</h2><p><span class='cb'></span>Ein handelsüblicher Arbeitsstuhl ist aus medizinischen Gründen nicht ausreichend.<br>"
              "<span class='cb'></span>Eine individuell angepasste Sitzversorgung ist erforderlich, um die Arbeitsfähigkeit zu erhalten.</p>"
              "<table style='margin-top:12mm'><tr><td class='sig' style='border-bottom:.6pt solid #1a2a3a;width:45%'></td><td style='width:10%'></td><td style='border-bottom:.6pt solid #1a2a3a'></td></tr>"
              "<tr><td>Ort, Datum</td><td></td><td>Stempel und Unterschrift Ärztin / Arzt</td></tr></table>")
    return seite("Ärztliche Stellungnahme " + d["vorgang"], inhalt, entwurf=False)


def doc_montage(d):
    p, v = d.get("pose", {}), d.get("versorgung") or {}
    rw = "".join(f"<tr><td>{e(a)}</td><td><b>{e(b)}</b></td><td style='color:#5d6d7e'>{e(c)}</td><td><span class='cb'></span></td></tr>" for a, b, c in richtwerte(p, (d.get('zusatz') or {}).get('werte')))
    opts = "".join(f"<tr><td><span class='cb'></span>{e(o['name'])}</td></tr>" for o in v.get("optionen", []))
    inhalt = (f"<h1>Montage-Checkliste</h1><p>Vorgang <b>{e(d['vorgang'])}</b> · {e(p.get('p_name'))} · Polsterfarbe: <b>{e(p.get('polsterfarbe') or '—')}</b>"
              + (" · <b style='color:#c0392b'>WOLLALLERGIE – nur wollfreie Bezüge</b>" if p.get("wollallergie") == "Ja" else "") + "</p>"
              f"<h2>Modell</h2><p><span class='cb'></span><b>{e((v.get('modell') or {}).get('name'))}</b> – Seriennummer: ______________________</p>"
              f"<h2>Optionen</h2><table>{opts or '<tr><td>keine</td></tr>'}</table>"
              f"<h2>Einstell-Richtwerte aus den Maßen</h2><table><thead><tr><th>Einstellung</th><th>Wert</th><th>aus</th><th>ok</th></tr></thead><tbody>{rw}</tbody></table>"
              f"<p style='color:#5d6d7e'>Körpergewicht {e(p.get('gewicht'))} kg · Traglast Modell {e((v.get('modell') or {}).get('max_kg'))} kg · Boden: {e(', '.join(p.get('boden') or []))} → Rollen/Gleiter passend?</p>"
              "<h2>Endkontrolle</h2><p><span class='cb'></span>Alle Schrauben nachgezogen<br><span class='cb'></span>Funktionen geprüft (Höhe, Neigung, Bremse, Motor)<br>"
              "<span class='cb'></span>Fotos: seitlich, frontal, Typenschild<br><span class='cb'></span>Freigabe Joachim</p>")
    return seite("Montage " + d["vorgang"], inhalt, entwurf=False)


POSE_GESCHLECHT = {"Männlich": "M", "Weiblich": "W"}
POSE_FELDER = ["datum", "nur_kv", "p_name", "p_strasse", "p_plz", "p_stadt", "p_telefon", "p_fax", "l_firma", "l_strasse", "l_plz",
               "l_stadt", "l_telefon", "l_fax", "l_email", "beruf", "pc_prozent", "schreiben_prozent", "telefon_prozent", "anders_prozent",
               "anders_text", "beschwerden", "klinik_von", "klinik_bis", "krank_tage", "skoliose", "skoliose_grad", "wollallergie", "alter",
               "gewicht", "geschlecht", "koerpergroesse", "mass_a", "mass_b", "mass_c", "mass_d", "mass_e", "mass_f", "mass_h", "lws",
               "boden", "boden_andere", "polsterfarbe", "erfahren"]


def pose_v1(d):
    p = d.get("pose", {})
    out = {k: p.get(k, "") for k in POSE_FELDER}
    out["geschlecht"] = POSE_GESCHLECHT.get(p.get("geschlecht"), p.get("geschlecht", ""))
    out["nur_kv"] = bool(p.get("nur_kv"))
    out["boden"] = p.get("boden") or []
    return out


def uebersicht_md(d, ordner):
    p, v, k = d.get("pose", {}), d.get("versorgung") or {}, d.get("kostentraeger") or {}
    s = (d.get("angebot") or {}).get("summen", {})
    offen = d.get("offen") or []
    z = [f"# {d['vorgang']} – {p.get('p_name', '')}", "",
         f"- Modus: {'Vorab-Bogen vom Kunden' if d['modus'] == 'kunde' else 'Beratung vor Ort'}",
         f"- Freigegeben: {d.get('freigegeben', '')}",
         f"- Kontakt: {p.get('p_telefon', '')} · {p.get('l_email', '')} · {p.get('p_plz', '')} {p.get('p_stadt', '')}",
         f"- Kostenträger: {k.get('traeger', '—')} · Az. {k.get('aktenzeichen', '—')} · vermittelt: {k.get('vermittelt', '—')}",
         f"- Versorgung: {(v.get('modell') or {}).get('name', '—')}",
         f"- Angebot brutto: {eur(s.get('brutto')) if s else '—'}",
         f"- Ergänzungsbögen: {', '.join((d.get('zusatz') or {}).get('aktiv', [])) or '—'}",
         f"- Einwilligung Nachsorge-Kontakt: {'ja' if (d.get('einwilligung') or {}).get('nachsorge') else 'nein'}", ""]
    if offen:
        z += ["## Noch offen", *[f"- [ ] {x}" for x in offen], ""]
    z += ["## Dateien", *[f"- {f.name}" for f in sorted(ordner.iterdir()) if f.is_file()]]
    return "\n".join(z) + "\n"


def pdf(html_datei: Path):
    """PDF über headless Chromium, falls vorhanden. Sonst bleibt es bei HTML (im Browser drucken)."""
    kandidaten = [os.environ.get("ERGO_CHROMIUM"), shutil.which("chromium"), shutil.which("chromium-browser"),
                  shutil.which("google-chrome"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"]
    exe = next((c for c in kandidaten if c and Path(c).exists()), None)
    if not exe:
        return None
    ziel = html_datei.with_suffix(".pdf")
    try:
        subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={ziel}", html_datei.resolve().as_uri()],
                       check=True, capture_output=True, timeout=60)
        return ziel if ziel.exists() else None
    except Exception:
        return None


def dokumente_bauen(ordner: Path):
    d = json.loads((ordner / "daten.json").read_text(encoding="utf-8"))
    (ordner / "pose.json").write_text(json.dumps(pose_v1(d), ensure_ascii=False, indent=2), encoding="utf-8")
    docs = {"montage-checkliste.html": doc_montage} if d["modus"] == "berater" else {}
    if d["modus"] == "berater":
        docs = {"kostenvoranschlag.html": doc_kv, "begruendung.html": doc_begruendung,
                "aerztliche-stellungnahme.html": doc_arzt, "montage-checkliste.html": doc_montage}
    for name, fn in docs.items():
        datei = ordner / name
        datei.write_text(fn(d), encoding="utf-8")
        pdf(datei)
    (ordner / "UEBERSICHT.md").write_text(uebersicht_md(d, ordner), encoding="utf-8")


# ── Server-Kommunikation ────────────────────────────────────────────
def anfrage(methode, pfad, token):
    url = os.environ.get("ERGO_URL", "https://ergo-plus.de").rstrip("/") + pfad
    req = urllib.request.Request(url, method=methode, headers={"Authorization": "Bearer " + token, "User-Agent": "ergo-buero/1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def token_lesen():
    t = os.environ.get("ERGO_ABHOL_TOKEN") or (TOKEN_DATEI.read_text().strip() if TOKEN_DATEI.is_file() else "")
    if not t:
        sys.exit("Kein Abhol-Token. Erst: buero.py token")
    return t


def telegram(text, dringend=False):
    bot, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (bot and chat):
        print("[Telegram nicht eingerichtet] " + text)
        return False
    daten = json.dumps({"chat_id": chat, "text": text, "disable_notification": not dringend}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{bot}/sendMessage", data=daten, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception as ex:
        print("Telegram fehlgeschlagen:", ex)
        return False


def anruf(text):
    """Letzte Eskalationsstufe: ruft einen Webhook auf, der einen Telefonanruf auslöst
    (z. B. eigene Asterisk-Anlage oder ein SIP-Anbieter mit Sprachansage)."""
    url = os.environ.get("ERGO_ANRUF_WEBHOOK")
    if not url:
        return False
    req = urllib.request.Request(url, data=json.dumps({"text": text}).encode(), headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception as ex:
        print("Anruf-Webhook fehlgeschlagen:", ex)
        return False


def cmd_abholen(args):
    token, key, basis = token_lesen(), privater_schluessel(), ablage()
    liste = anfrage("GET", "/api/postfach.php", token).get("vorgaenge", [])
    if not liste:
        print("Keine neuen Vorgänge.")
        return
    neu = []
    for eintrag in liste:
        umschlag = anfrage("GET", "/api/postfach.php?id=" + eintrag["id"], token)
        roh = basis / ".roh" / (eintrag["id"] + ".json")
        roh.parent.mkdir(exist_ok=True)
        roh.write_text(json.dumps(umschlag), encoding="utf-8")
        try:
            daten = entschluesseln(umschlag, key)
        except Exception as ex:
            print(f"✗ {eintrag['id']}: nicht entschlüsselbar ({ex}) – bleibt auf dem Server")
            telegram(f"⚠️ ERGO-PLUS: Vorgang {umschlag.get('vorgang')} lässt sich nicht entschlüsseln. Schlüssel prüfen.", dringend=True)
            continue
        ordner = vorgang_ablegen(daten, basis)
        if not args.behalten:
            anfrage("DELETE", "/api/postfach.php?id=" + eintrag["id"], token)
        roh.unlink()
        neu.append((daten, ordner))
        print(f"✓ {daten['vorgang']} → {ordner}")
    for daten, ordner in neu:
        p = daten.get("pose", {})
        if daten["modus"] == "kunde":
            telegram(f"📝 Vorab-Bogen {daten['vorgang']}: {p.get('p_name')} ({p.get('p_plz')} {p.get('p_stadt')}). Termin vereinbaren: {p.get('p_telefon') or p.get('l_email')}")
        else:
            s = (daten.get("angebot") or {}).get("summen", {})
            telegram(f"✅ {daten['vorgang']} {p.get('p_name')}: KV-Entwurf {eur(s.get('brutto'))} brutto liegt bereit. Bitte prüfen und an {(daten.get('kostentraeger') or {}).get('traeger') or 'Kostenträger'} senden.")


def cmd_entschluesseln(args):
    umschlag = json.loads(Path(args.datei).read_text(encoding="utf-8"))
    ordner = vorgang_ablegen(entschluesseln(umschlag, privater_schluessel()), ablage())
    print(f"✓ {ordner}")


def cmd_dokumente(args):
    dokumente_bauen(Path(args.ordner))
    print("✓ Unterlagen neu gebaut")


def cmd_waechter(args):
    """Eskalationsleiter: still → Telegram → Telegram laut → Anruf."""
    meldungen = []
    # 1) Stau im Postfach: Büro-Rechner holt nicht ab
    try:
        liste = anfrage("GET", "/api/postfach.php", token_lesen()).get("vorgaenge", [])
        jetzt = dt.datetime.now(dt.timezone.utc)
        for x in liste:
            alter = (jetzt - dt.datetime.fromisoformat(x["eingang"])).total_seconds() / 60
            if alter > args.stau_anruf:
                if not anruf(f"Achtung. Ein Vorgang liegt seit {int(alter / 60)} Stunden ungelesen auf dem Server."):
                    meldungen.append(("dringend", f"🚨 Vorgang liegt seit {int(alter)} min ungelesen auf dem Server – Büro-Rechner prüfen!"))
            elif alter > args.stau:
                meldungen.append(("dringend", f"⚠️ {len(liste)} Vorgang/Vorgänge warten seit {int(alter)} min auf Abholung."))
                break
    except urllib.error.URLError as ex:
        meldungen.append(("dringend", f"🚨 Server nicht erreichbar ({ex.reason}). Tablets können nichts übertragen!"))
    # 2) Lücken in abgeholten Vorgängen → Kunde anrufen
    for daten_json in ablage().glob("*/*/daten.json"):
        d = json.loads(daten_json.read_text(encoding="utf-8"))
        status = daten_json.parent / ".erinnert"
        if d.get("offen") and not status.exists():
            p = d.get("pose", {})
            meldungen.append(("normal", f"📞 {d['vorgang']} {p.get('p_name')}: fehlt noch {', '.join(d['offen'][:4])}. Anrufen: {p.get('p_telefon') or '—'}"))
            status.write_text(dt.datetime.now().isoformat())
    if not meldungen:
        print("Alles ruhig.")
    for stufe, text in meldungen:
        telegram(text, dringend=(stufe == "dringend"))


def main():
    env_laden()
    ap = argparse.ArgumentParser(description="ERGO-PLUS Büro-Werkzeug für den Konfigurator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("schluessel"); s.add_argument("--ausgabe"); s.add_argument("--ueberschreiben", action="store_true"); s.set_defaults(fn=cmd_schluessel)
    sub.add_parser("token").set_defaults(fn=cmd_token)
    s = sub.add_parser("abholen"); s.add_argument("--behalten", action="store_true", help="auf dem Server nicht löschen"); s.set_defaults(fn=cmd_abholen)
    s = sub.add_parser("entschluesseln"); s.add_argument("datei"); s.set_defaults(fn=cmd_entschluesseln)
    s = sub.add_parser("dokumente"); s.add_argument("ordner"); s.set_defaults(fn=cmd_dokumente)
    s = sub.add_parser("waechter"); s.add_argument("--stau", type=int, default=30, help="Minuten bis Warnung")
    s.add_argument("--stau-anruf", type=int, default=240, help="Minuten bis Anruf"); s.set_defaults(fn=cmd_waechter)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
