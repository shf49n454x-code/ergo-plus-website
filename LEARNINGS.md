# Learnings aus jonpride.de

Jons Fotografenseite jonpride.de hat 2026 denselben Weg hinter sich: vom
Onepager zu vielen verlinkten Seiten. Was dort schiefging und wie es
abgestellt wurde, steht hier, damit es bei ERGO-PLUS nicht noch einmal passiert.
Spalte „hier“ sagt, ob es bei ERGO-PLUS schon umgesetzt ist.

## Seitenrahmen und Struktur

| Learning | Warum | hier |
|---|---|---|
| Gemeinsame Teile (Navigation, Fußzeile, Brotkrumen) stehen zwischen Markern und werden von einem Skript gesetzt, nie von Hand kopiert. | Auf jonpride.de liefen handkopierte Navigationen auseinander, eine Unterseite verlinkte monatelang ins Leere. | ja, `tools/seiten/bauen.py` |
| Das Skript hat einen Prüfmodus (`--pruefen`), der in der CI rot wird, wenn jemand den Lauf vergisst. | Ein Skript, das man vergessen kann, wird vergessen. | ja, Schritt in `site-audit.yml` |
| Brotkrumen entstehen aus der Zuordnung Seite → Elternseite, sichtbar und als `BreadcrumbList`. Ändert sich eine H1 oder kommt eine Seite dazu: Skript laufen lassen. | Sonst stimmt der Pfad still nicht mehr. | ja, `SEITEN` in `bauen.py` |
| Kein Onepager. Wer auf einer Unterseite landet, muss weiterklicken können: volle Navigation, „Weiterführend“-Links, Kontaktband. | Ein Besuch, der nach einer Seite endet, zählt als Absprung. | ja |
| Sitemap wird erzeugt, nicht gepflegt. `lastmod` aus dem letzten Commit der Datei, `noindex`-Seiten und 404 fliegen raus. | Handgepflegte Sitemaps vergessen neue Seiten. | ja, in `bauen.py` |
| Alte Sprungmarken (`/#contact`) weiterleiten, nicht brechen. | Links in Mails, Lesezeichen und Google-Snippets zeigen noch darauf. | ja, `assets/js/site.js` |

## Bilder

| Learning | Warum | hier |
|---|---|---|
| Jedes `<img>`: Datei vorhanden, `width`/`height` gesetzt, Seitenverhältnis passt zur Datei, `alt` vorhanden. Automatisch geprüft. | Ein falsches Seitenverhältnis wirft keinen Fehler, das Bild steht nur verzerrt da. Fiel dort jedes Mal erst Besuchern auf. | ja, `tools/seiten/bilder_pruefen.py` (mit WebP). Fand beim ersten Lauf direkt einen echten Fehler im MFS-Artikel. |
| CSS und JS bekommen einen Fingerabdruck in der Adresse (`?v=hash`). | Assets werden lange zwischengespeichert. Ohne neue Adresse sieht ein wiederkehrender Besucher neues HTML mit altem CSS. Genau so waren dort Bilder auf dem Handy gestreckt. | ja, `bauen.py` stempelt `site.css` und `site.js` |
| Ein festes `height` am Bildcontainer ist verdächtig. Höhe aus `aspect-ratio` ableiten. | Mit `object-fit: cover` wird sonst jedes Bild auf ein fremdes Format beschnitten. | ja, im neuen CSS |
| Große Bilder brauchen `srcset` mit passender `sizes`-Angabe. `sizes` beschreibt die Anzeigebreite, nicht die Fensterbreite. | Dort war das Hauptfoto auf dem Handy pixelig, weil `sizes="100vw"` bei einem formatfüllenden Bild falsch war. | ja, 800er-Stufen erzeugt |
| Nach jeder Bildänderung bei 375 px ansehen. | Die Fehler zeigen sich fast immer zuerst auf dem Handy. | ja, Screenshots im PR |
| KI-erzeugte Bilder per IPTC `TrainedAlgorithmicMedia` kennzeichnen. | Transparenz und künftige Kennzeichnungspflichten. | **offen**: die `hf_…`-Bilder (HiggsField) sind noch nicht gekennzeichnet |

## Prüfen und Ausliefern

| Learning | Warum | hier |
|---|---|---|
| „Deploy grün“ heißt nur, dass ein paar Adressen 200 liefern. Nach dem Hochladen jede Seite der Sitemap im Browser bei 375 und 1440 px ansehen: Konsolenfehler, Bilder, horizontales Scrollen. | Dort lief die Seite grün und sah trotzdem kaputt aus. | teilweise: `audit.js` prüft im Browser bei Desktop-Breite; mobile Durchsicht bisher von Hand |
| Kein Loop und keine Routine veröffentlicht. Entwurf ablegen, melden, Jon sagt „go“. | Einmal ungeprüft live ist teurer als jeder gesparte Klick. | ja, steht schon in CLAUDE.md |
| Selbst betreiben vor anbinden. Formulare laufen über den eigenen Server, nicht über Formsubmit oder Google Forms. | Jeder fremde Dienst ist ein weiterer Ort mit Kundendaten und ein weiterer AVV. | ja, `kontakt.php` und verschlüsselter Konfigurator-Eingang |

## Inhalt und Auffindbarkeit (SEO/GEO)

| Learning | Warum | hier |
|---|---|---|
| Jede Inhaltsseite hat einen benannten Autor und ein sichtbares Stand-Datum. | Ohne erkennbare Autorschaft sinkt die Zitierfähigkeit in KI-Antworten. | ja auf den neuen Seiten, Ratgeber hatten es schon |
| Jede Seite gehört zu einem Cluster und verlinkt ihre Nachbarn. | Mehrseitige Belegstrukturen werden deutlich häufiger zitiert als Einzelseiten. | ja: Krankheitsbilder → Ratgeber → Sitzlösungen → Ablauf |
| JSON-LD nur für das, was auf der Seite sichtbar ist. | Unsichtbares FAQ-Markup auf der Startseite ist ein Qualitätsproblem, kein Gewinn. | ja, FAQPage nur noch auf `/faq.html` |
| Ein Kontextdokument mit nur gemessenen Werten (Bewertungen, Positionen, Klicks). Was nicht gemessen ist, bleibt `TODO`, wird nicht geschätzt. | Sonst beantwortet ein Modell die Frage irgendeiner Firma, nicht dieser. | teilweise: `data/search-console/` |
| Vor einem Umbau eine Baseline ziehen, danach vergleichen. | Ohne Baseline gibt es später keinen Vergleich, nur Behauptungen. | **offen**: Search-Console-Zahlen vor dem Hochladen sichern (laufen montags automatisch) |
