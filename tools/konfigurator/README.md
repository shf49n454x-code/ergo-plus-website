# Konfigurator – Einrichtung und Betrieb

Tablet-App für die Sitzberatung: POSE-Bogen, Ergänzungsbögen (Kleinwuchs, Schwergewicht,
Arthrodese/Prothese, Mobilität, Skoliose), Versorgung mit Regeln, Fotos, Angebot,
Einwilligung mit Unterschrift. Freigabe schickt alles **Ende-zu-Ende-verschlüsselt** ans Büro,
auch ohne Netz (Warteschlange auf dem Tablet).

| Teil | Wo | Aufgabe |
|---|---|---|
| App | `konfigurator/` → `https://ergo-plus.de/konfigurator/` | Beratung vor Ort (Joachim) |
| Vorab-Bogen | `https://ergo-plus.de/konfigurator/?modus=kunde` | Kunde füllt vor dem Termin aus |
| Eingang | `api/eingang.php` | nimmt nur Chiffretext an |
| Abholung | `api/postfach.php` | Büro holt mit Token ab, löscht danach |
| Büro | `tools/konfigurator/buero.py` | entschlüsselt, baut KV, Begründung, Arzt-Vorlage, Montage-Checkliste, POSE-JSON |
| Katalog | `konfigurator/katalog.json` | Modelle, Optionen, Regeln, Preise, Zusatzbögen |

## Datenfluss

```
Tablet ──(RSA-OAEP-3072 + AES-256-GCM, im Browser)──▶ Strato: api/postfach/*.json (unlesbar)
                                                         │  buero.py abholen (Token)
                                                         ▼
                                    Büro-Rechner / Lab-Server: privater Schlüssel
                                    → vorgaenge/EP-…/kostenvoranschlag.pdf, begruendung.pdf,
                                      aerztliche-stellungnahme.pdf, montage-checkliste.pdf,
                                      pose.json, fotos/, UEBERSICHT.md → Telegram-Meldung
```

Der Webserver, die Tablet-Warteschlange und der Transportweg sehen nie Klartext.
Klartext liegt nur (a) im Entwurf auf dem Tablet, solange noch nicht freigegeben, und
(b) im Büro nach dem Entschlüsseln. Tablet deshalb mit Code sperren.

## Einmalige Einrichtung (ca. 20 Minuten)

1. **Schlüsselpaar erzeugen** – auf dem Rechner, der später abholt (Lab-Server oder Büro-PC):
   ```bash
   pip install cryptography
   python3 tools/konfigurator/buero.py schluessel
   ```
   Legt `~/.ergo-plus/privat.pem` (passwortgeschützt) an und schreibt
   `konfigurator/oeffentlicher-schluessel.json`. **Sicherungskopie von `privat.pem` offline
   ablegen** – ohne sie sind Vorgänge nicht mehr lesbar.
2. **Abhol-Token erzeugen:** `python3 tools/konfigurator/buero.py token` – gibt zwei Zeilen
   für den Server aus.
3. **Server (Strato):** `api/einstellungen-lokal.beispiel.php` als `api/einstellungen-lokal.php`
   hochladen, die zwei Zeilen eintragen. Empfohlen: `POSTFACH_PFAD` auf einen Ordner
   **außerhalb** des Web-Verzeichnisses setzen.
4. **Öffentlichen Schlüssel** committen und mit der Seite hochladen.
5. **Katalog pflegen:** `konfigurator/katalog.json` – echte Modelle, Grenzwerte, Preise,
   `"beispielpreise": false` setzen. Danach in `konfigurator/sw.js` `VERSION` hochzählen.
6. **Telegram (optional):** `~/.ergo-plus/einstellungen.env`
   ```
   ERGO_URL=https://ergo-plus.de
   TELEGRAM_BOT_TOKEN=…
   TELEGRAM_CHAT_ID=…
   ERGO_SCHLUESSEL_PASS=…   # nur auf einem Rechner, dem man vertraut
   ```
7. **Tablet:** `https://ergo-plus.de/konfigurator/` in Safari öffnen → Teilen → „Zum
   Home-Bildschirm". Einmal mit Netz öffnen, danach läuft es offline.

## Automatisch laufen lassen (Lab-Server)

```cron
*/10 * * * *  cd /pfad/ergo-plus-website && python3 tools/konfigurator/buero.py abholen
*/15 * * * *  cd /pfad/ergo-plus-website && python3 tools/konfigurator/buero.py waechter
```

`waechter` ist die Eskalationsleiter:

| Lage | Reaktion |
|---|---|
| Vorgang liegt > 30 min ungeholt auf dem Server | Telegram, laut |
| > 4 h ungeholt | Anruf über `ERGO_ANRUF_WEBHOOK` (eigene Telefonanlage / SIP-Anbieter), sonst Telegram |
| Server nicht erreichbar | Telegram, laut („Tablets können nichts übertragen") |
| Vorgang mit Lücken (fehlende Maße, Kostenträger …) | Telegram „Kunde anrufen, fehlt …" mit Telefonnummer |

## Vorab-Link für Kunden

`https://ergo-plus.de/konfigurator/?modus=kunde&vorgang=EP-261020-ABCD` – die Vorgangsnummer
verbindet Vorab-Bogen und spätere Beratung im Büro-Ordner.

## Grenzen (ehrlich)

- KV, Begründung und Arzt-Vorlage sind **Entwürfe**: Joachim prüft vor Versand.
- Keine Anbindung an weclapp/Lexware: das Faktura-System bleibt die Quelle für echte
  Rechnungsnummern (GoBD). `daten.json`/`pose.json` sind für den späteren API-Import vorbereitet.
- Einwilligungstexte sind Entwürfe – vor dem Einsatz vom Datenschutzbeauftragten prüfen lassen.
- Ergänzungsbogen Kleinwuchs ist nach Fachwissen entworfen – mit Joachims Papierbogen abgleichen
  und in `katalog.json → zusatzboegen` anpassen (Felder, Folgefragen per `folge`).
