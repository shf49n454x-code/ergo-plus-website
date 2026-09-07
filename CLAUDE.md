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

## Was von selbst läuft

Vier Schleifen, die ohne Zutun anlaufen. Wer hier etwas ändert, sollte
wissen, was sonst noch daran hängt.

| Schleife | Auslöser | Ergebnis |
|---|---|---|
| `.github/workflows/site-audit.yml` | jeder PR, jeder Push auf main | rot bei Barrierefreiheits-, Lade- oder Strukturfehlern |
| `.github/workflows/search-console.yml` | montags 05:00 UTC | Google-Zahlen nach `data/search-console/` |
| `.github/workflows/preview.yml` | jeder Push auf main | baut `gh-pages-preview` nach |
| Routine „SEO-Vorschlag" | montags nach dem Datenlauf | Entwurfs-PR mit besseren Titles/Descriptions |

Die letzte ist die einzige, die Inhalte anfasst — und sie öffnet immer nur
einen **Entwurf**. Gemergt wird nichts automatisch, hier nicht und
nirgends. Was sie tut und wo sie aufhört: `.claude/skills/seo-vorschlag/SKILL.md`.

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
