# Design System -- ERGO-PLUS Seating Concepts

## Product Context
- **What this is:** Marketing and information website for therapeutic seating solutions
- **Who it's for:** People with physical disabilities (MS, ALS, scoliosis, dwarfism, amputation), their families, therapists, and cost carriers (Krankenkassen)
- **Space/industry:** German healthcare / rehabilitation aids (Hilfsmittelversorgung)
- **Project type:** Marketing site with informational blog, FAQ, and company profile pages
- **Competitors:** thomashilfen.de, pohlig.net, pflege-sessel.de
- **Supplier (not a competitor):** VELA / vela-stuhl.de -- ERGO-PLUS is a VELA dealer. Never position against VELA brand terms.
- **Positioning:** Specialist, not Sanitatshaus. Human warmth over clinical sterility.

## Aesthetic Direction (seit Oktober 2026)
- **Direction:** Ruhiges Fachhaus, kein Prospekt. Die Seite liest sich wie die Unterlagen eines guten Orthopädietechnikers: genau, hell, mit viel Luft.
- **Decoration level:** Minimal. Haarlinien statt Kartenschatten, weiße Flächen statt Verläufe. Keine Blobs, keine Glas-Effekte, keine Scroll-Reveals.
- **Memorable thing:** Die Maßlinien auf der dunklen Bühne der Startseite. Der VELA TANGO steht freigestellt da, teal eingezeichnet sind Rückenlehne, Sitzhöhe und Sitztiefe, jeweils „nach Ihrer …“. Das ist die Botschaft der Firma in einem Bild: Der Stuhl wird an Ihnen gemessen. Diese Bildsprache (technische Bemaßung) darf an anderer Stelle wieder auftauchen, sparsam.
- **Mood:** Kompetent und zugewandt. Weder Krankenhausbroschüre noch Startup-Landingpage.
- **Referenzen:** godly.design, uiuxshowcase.com, recent.design (Oktober 2026, Jon): redaktionelle Gitter, große ruhige Typografie, eine einzige bewegte Stelle.

## Typography
- **Display:** Figtree 700/800, enge Laufweite (−0,018 bis −0,025 em), `text-wrap: balance`.
- **Body:** Noto Sans 400/500, 17 px mobil, 18 px ab 900 px, Zeilenhöhe 1,7, Zeilenlänge höchstens 68 Zeichen (`--text`).
- **Labels/Buttons:** Figtree 600/700, Satzschreibung. **Keine Versalien-Labels** über Überschriften.
- **Loading:** selbst gehostet über `/assets/fonts/fonts.css` (kein Google-CDN, DSGVO).
- **Scale (clamp, mobil → Desktop):** H1 36→68 px (Startseite 40→84), H2 28→42, H3 20→24, Lead 18→21, Body 17→18, Meta 14–15. Nie unter 14 px.

## Color

Alle Tokens stehen in `assets/css/site.css` unter `:root`.

| Token | Hex | Rolle |
|-------|-----|-------|
| `--ink` | #142f45 | Text, Überschriften |
| `--ink-soft` | #3d5468 | Zweitrangiger Fließtext |
| `--ink-mute` | #5b6f80 | Metadaten (AA auf Weiß und auf `--paper`) |
| `--brand` | #1a5276 | Markenblau, Zitate |
| `--brand-deep` | #0f3550 | Kontaktband, Fußzeile |
| `--act` | #117a65 | Handlung: Buttons, Links (5,3:1 auf Weiß) |
| `--act-deep` | #0d6350 | Hover |
| `--act-wash` | #e2f1ed | helle Teal-Fläche, Badges |
| `--line-teal` | #1f9b80 | Maßlinien, Schrittnummern. Nur Linien und große Ziffern, nie Fließtext (3,4:1) |
| `--paper` | #f2f6f9 | Seitengrund |
| `--surface` | #ffffff | Flächen |
| `--rule` / `--rule-soft` | #d3dfe8 / #e6edf3 | Haarlinien |
| `--note` / `--note-wash` | #8a5606 / #fdf3dc | Hinweis-Kästen |
| `--night` / `--night-2` | #0b2131 / #12324a | dunkle Bühne der Startseite, Seitenköpfe der Hauptseiten |
| `--line-hell` | #5fd6bb | Maßlinien und Links auf Dunkel |
| `--text-hell` | rgba(255,255,255,.78) | Fließtext auf Dunkel |

Die alten `--c-*`-Namen sind in `site.css` als Aliase hinterlegt, weil Inline-Styles in den Ratgeber-Artikeln sie benutzen. Für neuen Code nicht verwenden.

**Produktfreisteller haben weißen Grund** (keine Transparenz). Sie stehen deshalb immer auf Weiß mit Haarlinie, nie auf `--paper`.

## Spacing & Layout
- **Raster:** linksbündig, max. 1240 px (`--wrap`), Seitenrand `clamp(16px, 4vw, 40px)`, Abschnittsabstand `clamp(64px, 9vw, 128px)`.
- **Abschnittskopf:** H2 links (5 Spalten), Einleitung rechts (6 Spalten) ab 960 px.
- **Abschnitte wechseln** zwischen `--paper` und Weiß (`.sec` / `.sec--white`). Keine Karten-Schatten.
- **Radien:** 8 px (Buttons, Eingaben), 12 px (Bilder), 20 px (große Flächen). Keine Pillen-Buttons.
- **Nummerierung nur, wo es eine echte Reihenfolge gibt** (Ablauf: `.weg`). Nirgends sonst 01/02/03.

## Seitenstruktur (Mehrseiten seit Oktober 2026)

| Seite | Zweck |
|---|---|
| `/` | Hero mit Maßlinien, Unterschied zum Sanitätshaus, drei Einstiege, Produktübersicht, Ablauf kurz, Alltag, Ratgeber |
| `/sitzloesungen.html` | Alle Produktfamilien mit Ausführungen (Anker `#vela-tango` usw.), Technik |
| `/ablauf-und-kosten.html` | Vier Schritte, Kostenträger-Tabelle, POSE-Bogen |
| `/krankheitsbilder.html` | Krankheitsbilder mit Link zum passenden Ratgeber-Artikel |
| `/ueber-ergo-plus.html` | Unternehmen, Team (`#team`), Angaben |
| `/kontakt.html` | Kontaktwege, Formular (`?thema=mfs` wählt das Produkt vor) |
| `/blog/` | Ratgeber |

Kopf, Navigation, Brotkrumen, Kontaktband und Fußzeile setzt `tools/seiten/bauen.py` (siehe CLAUDE.md). Nie von Hand in einzelne Seiten kopieren.

Jede Unterseite endet mit „Weiterführend“ (3–4 interne Links), Autor und Stand-Datum. Ratgeber-Artikel zeigen den Autor sichtbar unter der H1.

**Bilder:** Echte Menschen und echte Produkte vor Symbolbildern. Kein Bild, das dem Text widerspricht (z. B. Rollstuhl-Stockfoto zum Amputationsartikel). Telefonnummer immer „06021 12807“ (DIN 5008), im Link `tel:+49602112807`.

## Motion
Bewegung erklärt etwas oder antwortet auf eine Handlung. Sie dekoriert nicht.
- **Startseite, Bühne:** Beim Laden setzt der Stuhl auf, die drei Maßlinien zeichnen sich ein (0,9 s, gestaffelt). Beim Scrollen bleibt der Stuhl stehen (sticky), links laufen Sitzhöhe, Sitztiefe und Rückenlehne durch, und das jeweils beschriebene Maß leuchtet auf. Ohne JavaScript sind alle drei Maße sichtbar.
- **Hauptseiten:** Das Maßband an der Unterkante des dunklen Seitenkopfs läuft einmal von links ein, Überschrift und Lead tauchen leicht auf.
- **Technik-Galerie:** seitlich blättern (Scroll-Snap, Pfeiltasten und Knöpfe). Keine automatische Bewegung.
- **Seitenwechsel:** weicher Übergang per View Transitions (0,28 s), die Kopfzeile bleibt stehen.
- Keine Scroll-Reveals einzelner Abschnitte, keine Parallax, keine Zähler.
- `prefers-reduced-motion: reduce` schaltet alles ab, auch den Seitenwechsel.

## Accessibility Notes
- WCAG AA für allen Text; `--line-teal` nie für Text unter 24 px.
- Fokus: 3 px `--act`, 3 px Abstand.
- Klickflächen ≥ 44 px, Buttons 52 px hoch.
- Schriftgröße nie unter 14 px.
- „Zum Inhalt springen“-Link auf jeder Seite, Menü per Escape schließbar.
- Prüfen mit `node tools/audit/audit.js` (axe, 0 Verstöße).

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-28 | Initial design system created | Formalized existing site design after competitive analysis of vela-stuhl.de, thomashilfen.de, pohlig.net, pflege-sessel.de |
| 2026-05-28 | Keep Figtree + Noto Sans | Already strongest typography in the competitive space. No reason to change. |
| 2026-05-28 | Teal CTA as key differentiator | No competitor uses teal for actions. Instant visual recognition. |
| 2026-05-28 | Blue-tinted shadows | Cohesive with primary palette. Warmer than pure gray shadows. |
| 2026-05-28 | Comfortable spacing density | Target audience (elderly, disabled) benefits from generous whitespace. |
| 2026-10-23 | Mehrseitig statt Onepager | Jon: „sieht zu sehr nach Landingpage“, Unterseiten sollen sich in der Sitemap gegenseitig stützen. Sechs Hauptseiten, gemeinsamer Rahmen per Skript. |
| 2026-10-23 | Maßlinien als einziges auffälliges Element | Zeigt den Kern der Firma (Anpassung am Menschen) statt einer Statistik-Kachel. Ersetzt Blobs, Verläufe und Scroll-Reveals. |
| 2026-10-23 | Haarlinien statt Kartenschatten, keine Pillen-Buttons | Weg vom SaaS-Karten-Baukasten, hin zu redaktionellem Raster (Referenzen godly.design, uiuxshowcase.com, recent.design). |
| 2026-10-23 | Figtree + Noto Sans bleiben, Teal bleibt Handlungsfarbe | Wiedererkennung; nur Größen, Laufweite und Zeilenlänge neu gesetzt. |
| 2026-10-23 | Design-Review (Senior Design Director) umgesetzt | Keine Kennzahl-Kacheln, kein anonymes Kundenzitat, keine Stock- und KI-Wirbelsäulenbilder mehr auf Haupt- und Ablaufseite. Stattdessen das echte Team auf der Startseite. Produkte und Ratgeber als Listen mit Haarlinien statt Kartenraster. Lesespalten linksbündig im Raster, Telefonnummer überall „06021 12807“. |
| 2026-10-23 | Moderner und edler (Jon: „noch edler, hochwertiger, moderner, Vollbild, Animationen“) | Startseite öffnet als dunkle Vollbild-Bühne mit freigestelltem Stuhl auf hellem Lichtkreis; das Maßnehmen wird beim Scrollen erzählt. Hauptseiten bekommen einen dunklen Kopf mit Maßband-Kante. Technik als randabfallende Galerie mit großen Renderings. Teamfotos schwarzweiß. Seitenwechsel mit View Transitions. Die Bewegung bleibt an den Inhalt gebunden. |
