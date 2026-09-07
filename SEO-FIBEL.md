# SEO-Fibel für Joachim

Eine kurze Erklärung, was "SEO" und "GEO" bei ergo-plus.de bedeuten, was wir daran gemacht haben,
und worauf du selbst achten kannst, wenn ein neuer Artikel entsteht. Kein Fachchinesisch, nur das,
was für dich als Betreiber der Seite wirklich relevant ist.

## Was ist SEO?

SEO heißt "Search Engine Optimization" – dafür sorgen, dass Google (und Bing, DuckDuckGo etc.)
unsere Seiten findet, richtig versteht und bei den passenden Suchanfragen weit oben zeigt.
Beispiel: Jemand tippt "Parkinson Stuhl Krankenkasse" bei Google ein – SEO entscheidet, ob unser
Parkinson-Artikel dabei auf Seite 1 oder Seite 5 landet.

## Was ist GEO?

GEO heißt "Generative Engine Optimization" – das Gleiche, nur für KI-Systeme statt Suchmaschinen:
ChatGPT, Claude, Perplexity, Google Gemini. Wenn jemand dort fragt "Welcher Stuhl hilft bei MS?",
soll die KI unsere Seite als Quelle kennen und zitieren können. Dafür lassen wir in der `robots.txt`
gezielt die KI-Crawler zu (GPTBot, ClaudeBot, PerplexityBot etc.) und stellen mit `llms.txt` und
`llms-full.txt` maschinenlesbare Zusammenfassungen der Seite bereit.

## Ist die Seite bei Google indexiert?

Ja, technisch ist alles sauber:

- `sitemap.xml` listet alle 11 öffentlichen Seiten (Startseite, Blog-Übersicht, 8 Artikel, FAQ,
  Über-uns) – das ist die Liste, die wir Google aktiv zum Crawlen anbieten.
- `robots.txt` blockiert nur interne/technische Ordner (`/details/`, `/originals/`,
  `/team-originals/`), alles andere ist für Google offen.
- Ob eine einzelne Seite tatsächlich im Google-Index gelandet ist und wie sie rankt, sehen nur *wir*
  über die Google Search Console (Zugang zu deinem Google-Konto) – das kann ich von hier aus nicht
  einsehen. Falls dich das im Detail interessiert (welche Klicks, welche Position bei welchem
  Suchbegriff), lohnt sich ein kurzer Blick dort rein, sonst nicht nötig.

## Was war das Problem, das wir jetzt behoben haben?

Ende August hatten wir bei den 5 Diagnose-Artikeln (ALS, Kleinwuchs, Morbus Parkinson, Multiple
Sklerose, Querschnittlähmung) vier Lücken gefunden, die Google und KI-Systemen wichtige Signale
vorenthalten haben:

| Lücke | Was das bedeutet | Was wir jetzt gemacht haben |
|---|---|---|
| **Kein Autor** | Die Artikel liefen technisch als "geschrieben von: Firma", nicht als "geschrieben von: Person mit Namen und Titel". Google gewichtet Inhalte mit erkennbarem, fachlich passendem Autor höher (Stichwort "E-E-A-T": Experience, Expertise, Authoritativeness, Trust). | Alle 8 Blog-Artikel zeigen jetzt Joachim Stolz, Geschäftsführer, als Autor – mit Verlinkung zur Über-uns-Seite. |
| **Kein sichtbares Aktualisierungsdatum** | Das Datum stand nur im unsichtbaren Code (JSON-LD), nirgends für Leser oder Google direkt auf der Seite. Ein sichtbares Datum signalisiert Aktualität. | Jeder Artikel zeigt jetzt neben dem Veröffentlichungsdatum auch "Aktualisiert: [Datum]" – aktuell identisch, weil noch keine inhaltliche Überarbeitung stattfand. |
| **Kein FAQ-Schema** | Die 5 Diagnose-Artikel hatten keine strukturierten Frage-Antwort-Daten. Google kann daraus in der Ergebnisliste aufklappbare Fragen anzeigen (mehr Platz = mehr Klicks), und KI-Chatbots können einzelne Antworten leichter herausziehen. | Jeder der 5 Artikel hat jetzt einen sichtbaren "Häufig gestellte Fragen"-Abschnitt (4 Fragen) plus das dazugehörige technische FAQ-Schema. |
| **Kaum Verlinkung zwischen den Diagnose-Artikeln** | War bereits am 22.08. behoben (siehe Commit "Interne Verlinkung"). | Kein weiterer Handlungsbedarf. |

Der Content-Kalender (`blog/.content-calendar/schedule.json`) war deshalb pausiert – jetzt ist er
wieder aktiv, die 8 geplanten neuen Artikel können geschrieben werden.

## Worauf du selbst achten kannst

Du musst den Code nicht verstehen, aber ein paar Dinge helfen, wenn ein neuer Artikel entsteht:

1. **Jeder Artikel braucht ein Datum und einen erkennbaren Autor.** Das übernehmen wir technisch,
   du musst nichts eintragen – aber sag Bescheid, wenn mal ein anderer Autor als du selbst einen
   Artikel schreibt (z. B. ein Therapeut), damit das korrekt hinterlegt wird.
2. **Titel und erster Absatz sollten die Suchfrage direkt beantworten.** "Was zahlt die Krankenkasse
   bei Parkinson?" ist eine bessere Überschrift als "Unsere Erfahrungen mit Parkinson", weil Google
   und KI-Systeme genau danach suchen.
3. **Bei neuen Diagnosen: 3–4 typische Fragen mitliefern.** Genau das haben wir jetzt bei den 5
   bestehenden Artikeln nachgeholt – bei neuen Artikeln bauen wir das gleich mit ein.
4. **Nichts erfinden.** Zahlen, Kostenträger, Produktnamen – alles muss stimmen, weil sowohl Google
   als auch potenzielle Kunden das als Fakten lesen.

## Wo finde ich was?

- `robots.txt`, `sitemap.xml` – wer crawlen darf, welche Seiten es gibt.
- `llms.txt`, `llms-full.txt` – die Zusammenfassung für KI-Systeme.
- `blog/.content-calendar/schedule.json` – Redaktionsplan, Status jedes Artikels.
- Diese Datei (`SEO-FIBEL.md`) – zum Nachschlagen, wenn wieder mal die Frage kommt "ranken wir
  eigentlich gut?".
