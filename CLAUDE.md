# ERGO-PLUS Seating Concepts

Static HTML website for a German therapeutic seating company.

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

## Prüfen vor dem Merge

Vor jedem Merge und nach jedem Design- oder Content-Eingriff:

```bash
node tools/audit/audit.js
```

Barrierefreiheit (axe-core, 0 Verstöße), Ladeverhalten (LCP/CLS/Gewicht)
und strukturelle Fehler in einem Lauf. Exit-Code 1, wenn eine Schwelle
gerissen wird. Details und die Regeln dahinter: `.claude/skills/site-audit/SKILL.md`.

Nicht schätzen, ob etwas schnell oder barrierefrei ist — messen.

## Seiten anlegen und ändern (seit Oktober 2026 mehrseitig)

Kopf, Navigation, Brotkrumen, Kontaktband, Fußzeile, Cookie-Hinweis und die
Adressen von `site.css`/`site.js` stehen auf jeder Seite zwischen Markern
(`<!-- SEITE:NAV -->` … `<!-- /SEITE:NAV -->` usw.). Sie werden nie von Hand
geändert, sondern von:

```bash
python3 tools/seiten/bauen.py          # setzt alle Rahmen, stempelt CSS/JS, baut sitemap.xml
python3 tools/seiten/bilder_pruefen.py # Bilder: Datei, width/height, Seitenverhältnis, alt
```

Danach laufen lassen, wenn: CSS oder JS geändert, Seite angelegt, H1 geändert,
Navigation geändert. Neue Seite = Eintrag in `SEITEN` in `bauen.py` plus die vier
Marker (Vorlage: `kontakt.html`). Beide Skripte laufen in `site-audit.yml` mit,
`bauen.py --pruefen` wird rot, wenn der Lauf vergessen wurde.

Gestaltung: `DESIGN.md`. Warum es so gebaut ist: `LEARNINGS.md` (aus jonpride.de).
Ausnahme: `pose-bogen.html` hat eine eigene Oberfläche und keinen gemeinsamen Rahmen.

## Was von selbst läuft

Fünf Schleifen, die ohne Zutun anlaufen. Wer hier etwas ändert, sollte
wissen, was sonst noch daran hängt.

| Schleife | Auslöser | Ergebnis |
|---|---|---|
| `.github/workflows/site-audit.yml` | jeder PR, jeder Push auf main | rot bei Barrierefreiheits-, Lade- oder Strukturfehlern |
| `.github/workflows/search-console.yml` | montags 05:00 UTC | Google-Zahlen nach `data/search-console/`, dazu je Sitemap-Adresse der Index-Status (`INDEX.md`) |
| `.github/workflows/erreichbarkeit.yml` | täglich 06:17 UTC | rot (Mail von GitHub), wenn ergo-plus.de nicht antwortet, das Zertifikat fehlt oder eine Platzhalterseite kommt; Commit nur bei Zustandswechsel |
| `.github/workflows/preview.yml` | jeder Push auf main | baut `gh-pages-preview` nach |
| Routine „SEO-Vorschlag" | montags nach dem Datenlauf | Entwurfs-PR mit besseren Titles/Descriptions |

Die letzte ist die einzige, die Inhalte anfasst — und sie öffnet immer nur
einen **Entwurf**. Gemergt wird nichts automatisch, hier nicht und
nirgends. Was sie tut und wo sie aufhört: `.claude/skills/seo-vorschlag/SKILL.md`.

Damit keine dieser Schleifen still ausfallen kann:

| Datei | wofür |
|---|---|
| `data/search-console/LETZTER-LAUF.md` | was der letzte Datenlauf getan hat — auch wenn er gescheitert ist |
| `data/search-console/VERSUCHE.md` | was geändert wurde und was daraus wurde |
| Audit-Prüfung „Alter der Daten" | wird rot, wenn seit zehn Tagen nichts abgeholt wurde |
| `data/search-console/INDEX.md` | welche Sitemap-Adressen Google im Index hat und warum die anderen fehlen |
| `data/erreichbarkeit/ERREICHBARKEIT.md` | letzter Zustandswechsel der Live-Seite |

**Vor jedem Upload auf den Server:** `python3 tools/erreichbarkeit/pruefen.py` muss grün sein. Die `.htaccess` setzt HSTS für ein Jahr; geht sie live, während https nicht funktioniert, sperrt sie Besucher und Google ein Jahr lang aus.

Ein grüner Lauf heißt nicht, dass etwas passiert ist. Genau dieser
Trugschluss hat hier schon dreimal Zeit gekostet.

## Konfigurator (Tablet-App + verschlüsselter Eingang)

`konfigurator/`, `api/`, `tools/konfigurator/` – Einrichtung und Betrieb: `tools/konfigurator/README.md`.
Regeln: Gesundheitsdaten nie im Klartext an den Server, nie per Mail. Der private Schlüssel gehört
nie ins Repo. Nach Änderungen an Konfigurator-Dateien `VERSION` in `konfigurator/sw.js` hochzählen.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming -> invoke /office-hours
- Strategy/scope -> invoke /plan-ceo-review
- Architecture -> invoke /plan-eng-review
- Design system/plan review -> invoke /design-consultation or /plan-design-review
- Full review pipeline -> invoke /autoplan
- Bugs/errors -> invoke /investigate
- QA/testing site behavior -> invoke /qa or /qa-only
- Code review/diff check -> invoke /review
- Visual polish -> invoke /design-review
- Ship/deploy/PR -> invoke /ship or /land-and-deploy
- Save progress -> invoke /context-save
- Resume context -> invoke /context-restore
- Author a backlog-ready spec/issue -> invoke /spec
- Search-Console-Zahlen auswerten, Titles/Descriptions verbessern -> invoke /seo-vorschlag
