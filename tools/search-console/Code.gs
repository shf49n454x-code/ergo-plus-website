/**
 * Search-Console-Daten automatisch in eine Google-Tabelle schreiben.
 *
 * Läuft als Google Apps Script auf Googles Servern — also dort, wo der
 * Zugriff auf die Search-Console-API ohnehin erlaubt ist. Einmal
 * einrichten, danach aktualisiert sich die Tabelle von selbst.
 *
 * Einrichtung: siehe README.md im selben Ordner.
 */

// ── Einstellungen ────────────────────────────────────────────────────
const CONFIG = {
  // Genau so, wie die Property in der Search Console heißt.
  // Domain-Property:  'sc-domain:ergo-plus.de'
  // URL-Property:     'https://ergo-plus.de/'
  siteUrl: 'sc-domain:ergo-plus.de',

  // Wie viele Tage zurück. Search Console hält rund 16 Monate vor.
  tageZurueck: 90,

  // Search Console hinkt zwei bis drei Tage hinterher. Die letzten Tage
  // sind sonst unvollständig und sehen wie ein Einbruch aus.
  tageAuslassen: 3,

  // Zeilen je Blatt. Die API liefert höchstens 25.000 pro Anfrage,
  // das Skript blättert bei Bedarf weiter.
  maxZeilen: 5000,
};

const API = 'https://www.googleapis.com/webmasters/v3/sites';

// ── Einstiegspunkt ───────────────────────────────────────────────────
/**
 * Diese Funktion läuft beim Zeit-Trigger. Sie schreibt vier Blätter:
 * Suchanfragen, Seiten, Anfrage×Seite und Verlauf.
 */
function searchConsoleAktualisieren() {
  const bis = new Date();
  bis.setDate(bis.getDate() - CONFIG.tageAuslassen);
  const von = new Date(bis);
  von.setDate(von.getDate() - CONFIG.tageZurueck);

  const zeitraum = { start: alsDatum(von), ende: alsDatum(bis) };
  const tabelle = SpreadsheetApp.getActiveSpreadsheet();

  schreibeBlatt(tabelle, 'Suchanfragen', ['query'], zeitraum,
    ['Suchanfrage', 'Klicks', 'Impressionen', 'CTR %', 'Position']);

  schreibeBlatt(tabelle, 'Seiten', ['page'], zeitraum,
    ['Seite', 'Klicks', 'Impressionen', 'CTR %', 'Position']);

  // Diese Kombination ist die wertvollste: sie zeigt, welche Seite für
  // welche Anfrage rankt — daraus lässt sich ableiten, wo ein besserer
  // Titel oder ein zusätzlicher Absatz wirklich etwas bringt.
  schreibeBlatt(tabelle, 'Anfrage x Seite', ['query', 'page'], zeitraum,
    ['Suchanfrage', 'Seite', 'Klicks', 'Impressionen', 'CTR %', 'Position']);

  schreibeBlatt(tabelle, 'Verlauf', ['date'], zeitraum,
    ['Datum', 'Klicks', 'Impressionen', 'CTR %', 'Position']);

  const info = tabelle.getSheetByName('Stand') || tabelle.insertSheet('Stand');
  info.clear();
  info.getRange(1, 1, 5, 2).setValues([
    ['Property', CONFIG.siteUrl],
    ['Zeitraum', zeitraum.start + ' bis ' + zeitraum.ende],
    ['Zuletzt aktualisiert', new Date()],
    ['Hinweis', 'Search Console hinkt 2-3 Tage hinterher; die letzten ' +
                CONFIG.tageAuslassen + ' Tage sind bewusst ausgelassen.'],
    ['Erzeugt von', 'tools/search-console/Code.gs im Website-Repo'],
  ]);
  info.getRange(1, 1, 5, 1).setFontWeight('bold');
  info.autoResizeColumns(1, 2);
}

// ── Abruf und Ausgabe ────────────────────────────────────────────────
function schreibeBlatt(tabelle, name, dimensionen, zeitraum, kopf) {
  const zeilen = holeAlleZeilen(dimensionen, zeitraum);

  const blatt = tabelle.getSheetByName(name) || tabelle.insertSheet(name);
  blatt.clear();
  blatt.getRange(1, 1, 1, kopf.length).setValues([kopf]).setFontWeight('bold');
  blatt.setFrozenRows(1);

  if (!zeilen.length) {
    blatt.getRange(2, 1).setValue('Keine Daten für diesen Zeitraum.');
    return;
  }

  const daten = zeilen.map((r) => r.keys.concat([
    r.clicks,
    r.impressions,
    Math.round(r.ctr * 1000) / 10,      // als Prozent mit einer Nachkommastelle
    Math.round(r.position * 10) / 10,
  ]));

  blatt.getRange(2, 1, daten.length, kopf.length).setValues(daten);
  blatt.autoResizeColumns(1, kopf.length);
  // Nach Impressionen sortieren, nicht nach Klicks: Seiten mit vielen
  // Impressionen und wenig Klicks sind die eigentlichen Baustellen.
  const spalteImpressionen = dimensionen.length + 2;
  blatt.getRange(2, 1, daten.length, kopf.length)
       .sort({ column: spalteImpressionen, ascending: false });
}

function holeAlleZeilen(dimensionen, zeitraum) {
  const alle = [];
  let start = 0;
  const schritt = Math.min(CONFIG.maxZeilen, 25000);

  while (alle.length < CONFIG.maxZeilen) {
    const antwort = frageAPI({
      startDate: zeitraum.start,
      endDate: zeitraum.ende,
      dimensions: dimensionen,
      rowLimit: schritt,
      startRow: start,
    });
    const zeilen = (antwort && antwort.rows) || [];
    alle.push.apply(alle, zeilen);
    if (zeilen.length < schritt) break;   // nichts mehr da
    start += schritt;
  }
  return alle.slice(0, CONFIG.maxZeilen);
}

function frageAPI(koerper) {
  const url = API + '/' + encodeURIComponent(CONFIG.siteUrl) +
              '/searchAnalytics/query';
  const antwort = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(koerper),
    muteHttpExceptions: true,
  });

  const code = antwort.getResponseCode();
  if (code !== 200) {
    // Klartext statt Google-Rohfehler — sonst sucht man lange.
    const hinweis = code === 403
      ? 'Kein Zugriff auf die Property. Stimmt CONFIG.siteUrl genau mit ' +
        'der Search Console überein, und ist das ausführende Google-Konto ' +
        'dort als Nutzer eingetragen?'
      : code === 404
      ? 'Property nicht gefunden. Domain-Property braucht das Präfix ' +
        '"sc-domain:", URL-Property die vollständige URL mit Schrägstrich.'
      : 'Search Console antwortet mit HTTP ' + code + '.';
    throw new Error(hinweis + '\n\nAntwort: ' + antwort.getContentText());
  }
  return JSON.parse(antwort.getContentText());
}

function alsDatum(d) {
  return Utilities.formatDate(d, 'UTC', 'yyyy-MM-dd');
}

// ── Einmalige Einrichtung ────────────────────────────────────────────
/**
 * Einmal von Hand ausführen: legt den wöchentlichen Trigger an
 * (montags früh) und füllt die Tabelle sofort zum ersten Mal.
 */
function triggerEinrichten() {
  ScriptApp.getProjectTriggers()
    .filter((t) => t.getHandlerFunction() === 'searchConsoleAktualisieren')
    .forEach((t) => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger('searchConsoleAktualisieren')
    .timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(6).create();

  searchConsoleAktualisieren();
  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Eingerichtet. Aktualisiert sich ab jetzt montags gegen 6 Uhr.',
    'Search Console', 10);
}
