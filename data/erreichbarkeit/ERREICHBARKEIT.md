# Erreichbarkeit

**24.10.2026 05:25 UTC** — **gestört**

| Prüfung | Ergebnis | Hinweis |
|---|---|---|
| TLS ergo-plus.de | **FEHLER** | TLS-Fehler: TLSV1_ALERT_INTERNAL_ERROR |
| TLS www.ergo-plus.de | **FEHLER** | TLS-Fehler: TLSV1_ALERT_INTERNAL_ERROR |
| Weiterleitung http://ergo-plus.de/ | **FEHLER** | 200 nach (keine); erwartet 301 nach https://ergo-plus.de/ |
| Weiterleitung http://www.ergo-plus.de/ | **FEHLER** | 200 nach (keine); erwartet 301 nach https://ergo-plus.de/ |
| Weiterleitung https://www.ergo-plus.de/ | **FEHLER** | URLError: <urlopen error [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error (_ssl.c:1010)> |
| Startseite | **FEHLER** | URLError: <urlopen error [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error (_ssl.c:1010)> |
| robots.txt | **FEHLER** | URLError: <urlopen error [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error (_ssl.c:1010)> |
| Sitemap | **FEHLER** | URLError: <urlopen error [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error (_ssl.c:1010)> |

---

Erzeugt von `tools/erreichbarkeit/pruefen.py`, täglich über `.github/workflows/erreichbarkeit.yml`.
