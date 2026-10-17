/* ERGO-PLUS Konfigurator – POSE-Bogen, Zusatzbögen, Versorgung, Angebot, Einwilligung.
 * Modi:  /konfigurator/                → Beratung vor Ort (Joachim, Tablet)
 *        /konfigurator/?modus=kunde    → Vorab-Bogen für Kundinnen und Kunden
 *        &vorgang=EP-…                 → Vorgangsnummer vorgeben (Büro verschickt Link)
 */
(function () {
  'use strict';

  const params = new URLSearchParams(location.search);
  const MODUS = params.get('modus') === 'kunde' ? 'kunde' : 'berater';
  const istKunde = MODUS === 'kunde';
  let K = null;            // Katalog
  let V = null;            // aktueller Vorgang
  let gesendet = false;    // Erfolgsansicht nach Freigabe (Text)
  let gesendetOk = false;  // true = beim Server angekommen, false = liegt in der Warteschlange

  /* ── Hilfen ─────────────────────────────────────────── */
  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const zahl = v => { const n = parseFloat(String(v ?? '').replace(',', '.')); return isFinite(n) ? n : null; };
  const eur = n => (Math.round(n * 100) / 100).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' });
  const heute = () => new Date().toISOString().slice(0, 10);
  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : 'id-' + Date.now() + '-' + Math.random().toString(16).slice(2));
  function vorgangsNr() {
    const d = new Date();
    const z = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let r = ''; const b = crypto.getRandomValues(new Uint8Array(4));
    b.forEach(x => { r += z[x % z.length]; });
    return 'EP-' + String(d.getFullYear()).slice(2) + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0') + '-' + r;
  }
  function get(pfad) { return pfad.split('.').reduce((o, k) => (o == null ? undefined : o[k]), V); }
  function set(pfad, wert) {
    const teile = pfad.split('.'); let o = V;
    teile.slice(0, -1).forEach(k => { if (o[k] == null || typeof o[k] !== 'object') o[k] = {}; o = o[k]; });
    o[teile[teile.length - 1]] = wert;
  }
  let meldungTimer, meldungAktion = null;
  function melde(text, aktion) {
    const m = $('#meldung');
    m.innerHTML = '<span>' + esc(text) + '</span>' + (aktion ? '<button type="button" id="meldung-aktion">' + esc(aktion.label) + '</button>' : '');
    meldungAktion = aktion ? aktion.fn : null;
    m.classList.toggle('mit-aktion', !!aktion); m.classList.add('zeigen');
    clearTimeout(meldungTimer); meldungTimer = setTimeout(() => { m.classList.remove('zeigen'); meldungAktion = null; }, aktion ? 6000 : 3200);
  }

  function neuerVorgang() {
    return {
      id: uuid(), vorgang: params.get('vorgang') || vorgangsNr(), modus: MODUS, schritt: 0,
      angelegt: new Date().toISOString(),
      felder: { datum: heute(), nur_kv: false, berater: istKunde ? '' : 'Joachim Stolz', lieferung_wie_privat: true },
      kostentraeger: { traeger: '', aktenzeichen: '', ansprechpartner: '', kontakt: '', vermittelt: '' },
      zusatz: { aktiv: [], werte: {} },
      versorgung: { linie: '', modell: '', optionen: [], einfach: {} },
      leistungen: { aus: {}, preis: {}, km: '' },
      fotos: [],
      einwilligung: { datenschutz: false, schweigepflicht: false, fotos: false, nachsorge: false },
      unterschrift: { bild: '', name: '', ort: '', datum: heute() },
      notiz: ''
    };
  }

  /* ── Regeln ─────────────────────────────────────────── */
  function empfehlungen() {
    const f = V.felder, z = V.zusatz.aktiv, r = new Set();
    const groesse = zahl(f.koerpergroesse), gewicht = zahl(f.gewicht), grad = zahl(f.skoliose_grad);
    if (z.includes('kleinwuchs') || (groesse && groesse < 140)) r.add('kleinwuchs');
    if (z.includes('schwergewicht') || (gewicht && gewicht > 135)) r.add('schwer');
    if (z.includes('skoliose') || (f.skoliose === 'Ja' && (grad == null || grad >= 20))) r.add('mfs');
    if (z.includes('arthrodese')) r.add('arthrodese');
    if (z.includes('mobilitaet')) r.add('aufsteh');
    if (!r.size) r.add('ergo');
    return r;
  }
  function zusatzVorschlaege() {
    const f = V.felder, s = new Set();
    if (zahl(f.koerpergroesse) && zahl(f.koerpergroesse) < 140) s.add('kleinwuchs');
    if (zahl(f.gewicht) && zahl(f.gewicht) > 135) s.add('schwergewicht');
    if (f.skoliose === 'Ja') s.add('skoliose');
    return [...s].filter(x => !V.zusatz.aktiv.includes(x));
  }
  const linie = () => K.linien.find(l => l.id === V.versorgung.linie);
  const modell = () => (linie() || { modelle: [] }).modelle.find(m => m.id === V.versorgung.modell);
  function optionSperre(o, gruppe) {
    const l = V.versorgung.linie;
    if (o.nur_fuer && !o.nur_fuer.includes(l)) return 'Nicht für diese Produktlinie';
    if (o.nicht_fuer && o.nicht_fuer.includes(l)) return 'Bei diesem Modell bereits enthalten';
    if (o.wolle && V.felder.wollallergie === 'Ja') return 'Wollallergie angegeben';
    if (gruppe.auswahl === 'mehrfach') {
      const gewaehlt = V.versorgung.optionen;
      const gegner = alleOptionen().find(x => x.schliesst_aus && x.schliesst_aus.includes(o.id) && gewaehlt.includes(x.id));
      if (gegner) return 'Schließt sich aus mit „' + gegner.name + '“';
      if (o.schliesst_aus && o.schliesst_aus.some(id => gewaehlt.includes(id))) return 'Schließt sich aus mit einer gewählten Option';
    }
    return '';
  }
  const alleOptionen = () => K.optionen.flatMap(g => g.eintraege);
  function gewaehlteOptionen() {
    const ids = [...V.versorgung.optionen, ...Object.values(V.versorgung.einfach)];
    return alleOptionen().filter(o => ids.includes(o.id));
  }
  function bereinigeOptionen() {
    // Gesperrte Optionen fallen automatisch raus (z. B. nach Linienwechsel oder Wollallergie)
    K.optionen.forEach(g => {
      if (g.auswahl === 'einfach') {
        const id = V.versorgung.einfach[g.gruppe];
        const o = g.eintraege.find(x => x.id === id);
        if (o && optionSperre(o, g)) delete V.versorgung.einfach[g.gruppe];
      } else {
        V.versorgung.optionen = V.versorgung.optionen.filter(id => {
          const o = g.eintraege.find(x => x.id === id); return !o || !optionSperre(o, g);
        });
      }
    });
    const m = modell();
    if (V.versorgung.modell && !m) V.versorgung.modell = '';
  }

  /* ── Positionen & Summen ────────────────────────────── */
  function positionen() {
    const p = [];
    const m = modell();
    if (m) p.push({ id: 'stuhl', name: m.name, netto: m.preis_netto });
    gewaehlteOptionen().forEach(o => { if (o.preis_netto) p.push({ id: o.id, name: o.name, netto: o.preis_netto }); });
    K.leistungen.forEach(l => {
      const an = V.leistungen.aus[l.id] === undefined ? l.fest : !V.leistungen.aus[l.id];
      if (!an) return;
      let netto = zahl(V.leistungen.preis[l.id]);
      if (netto == null) netto = l.je_km_netto ? (zahl(V.leistungen.km) || 0) * 2 * l.je_km_netto : l.preis_netto;
      p.push({ id: l.id, name: l.name + (l.je_km_netto && zahl(V.leistungen.km) ? ' – ' + zahl(V.leistungen.km) + ' km einfach' : ''), netto, leistung: true });
    });
    return p;
  }
  function summen() {
    const netto = positionen().reduce((s, x) => s + (x.netto || 0), 0);
    const mwst = netto * K.mwst_standard / 100;
    return { netto, mwst, brutto: netto + mwst };
  }

  /* ── Schritte ───────────────────────────────────────── */
  const SCHRITTE = [
    { id: 'vorgang', titel: 'Vorgang', nur: 'berater', render: rVorgang, pruefen: () => (V.kostentraeger.traeger ? [] : ['Kostenträger wählen']) },
    { id: 'kunde', titel: istKunde ? 'Ihre Angaben' : 'Kunde', render: rKunde, pruefen: () => {
      const f = V.felder, x = [];
      if (!f.p_name) x.push('Name fehlt');
      if (!f.p_telefon && !f.l_email) x.push('Telefon oder E-Mail fehlt');
      if (!f.p_plz) x.push('PLZ fehlt');
      return x; } },
    { id: 'arbeitsplatz', titel: 'Arbeitsplatz', render: rArbeitsplatz, pruefen: () => {
      const s = prozentSumme(); return s !== null && s !== 100 ? ['Zeitaufteilung ergibt ' + s + ' % statt 100 %'] : []; } },
    { id: 'gesundheit', titel: 'Gesundheit', render: rGesundheit, pruefen: () => (V.felder.beschwerden ? [] : ['Beschwerden beschreiben']) },
    { id: 'masse', titel: 'Maße', render: rMasse, pruefen: () => {
      const f = V.felder, x = [];
      if (!zahl(f.gewicht)) x.push('Gewicht fehlt');
      if (!zahl(f.koerpergroesse)) x.push('Körpergröße fehlt');
      ['a', 'b', 'c'].forEach(k => { if (!zahl(f['mass_' + k])) x.push('Maß ' + k.toUpperCase() + ' fehlt'); });
      return x; } },
    { id: 'umgebung', titel: 'Umgebung', render: rUmgebung, pruefen: () => [] },
    { id: 'versorgung', titel: 'Versorgung', nur: 'berater', render: rVersorgung, pruefen: () => {
      const x = [];
      if (!V.versorgung.linie) x.push('Produktlinie wählen');
      else if (!V.versorgung.modell) x.push('Modell wählen');
      const m = modell(), g = zahl(V.felder.gewicht);
      if (m && g && m.max_kg && g > m.max_kg) x.push('Gewicht über Traglast des Modells (' + m.max_kg + ' kg)');
      return x; } },
    { id: 'fotos', titel: 'Fotos', nur: 'berater', render: rFotos, pruefen: () => (V.fotos.length ? [] : ['Noch keine Fotos']) },
    { id: 'angebot', titel: 'Angebot', nur: 'berater', render: rAngebot, pruefen: () => {
      const km = K.leistungen.find(l => l.je_km_netto);
      const an = km && (V.leistungen.aus[km.id] === undefined ? km.fest : !V.leistungen.aus[km.id]);
      return an && !zahl(V.leistungen.km) ? ['Kilometer für Anfahrt eintragen'] : []; } },
    { id: 'einwilligung', titel: 'Einwilligung', render: rEinwilligung, pruefen: () => {
      const x = [];
      if (!V.einwilligung.datenschutz) x.push('Einwilligung Datenschutz fehlt');
      if (!V.unterschrift.bild) x.push('Unterschrift fehlt');
      return x; } },
    { id: 'abschluss', titel: istKunde ? 'Absenden' : 'Freigabe', render: rAbschluss, pruefen: () => [] }
  ].filter(s => !(s.nur === 'berater' && istKunde));

  const HART = ['Name fehlt', 'Einwilligung Datenschutz fehlt', 'Unterschrift fehlt'];

  /* ── Bausteine ──────────────────────────────────────── */
  function feld(pfad, label, opt = {}) {
    const id = 'f-' + pfad.replace(/\./g, '-');
    const w = get(pfad) ?? '';
    // Dezimalfelder als Text: deutsches Komma funktioniert auf jedem Tablet, keine Spinner.
    const typ = opt.typ === 'number' && opt.inputmode === 'decimal' ? 'text' : (opt.typ || 'text');
    const cls = 'feld ' + (opt.span || 's3');
    const attr = [
      opt.inputmode ? 'inputmode="' + opt.inputmode + '"' : '',
      opt.min != null ? 'min="' + opt.min + '"' : '', opt.max != null ? 'max="' + opt.max + '"' : '',
      opt.step ? 'step="' + opt.step + '"' : '', opt.auto ? 'autocomplete="' + opt.auto + '"' : 'autocomplete="off"',
      opt.hilfe ? 'aria-describedby="' + id + '-h"' : '', opt.pflicht ? 'aria-required="true"' : '',
      opt.massBuchstabe ? 'data-mass="' + opt.massBuchstabe + '"' : ''
    ].join(' ');
    const lab = '<label for="' + id + '"' + (opt.pflicht ? ' class="pflicht"' : '') + '>' + esc(label) + '</label>';
    let eingabe;
    if (typ === 'textarea') eingabe = '<textarea id="' + id + '" data-pfad="' + pfad + '" ' + attr + '>' + esc(w) + '</textarea>';
    else eingabe = '<input type="' + typ + '" id="' + id + '" data-pfad="' + pfad + '" value="' + esc(w) + '" ' + attr + '>';
    if (opt.einheit) eingabe = '<div class="mit-einheit">' + eingabe + '<span class="e" aria-hidden="true">' + esc(opt.einheit) + '</span></div>';
    return '<div class="' + cls + '">' + lab + eingabe +
      (opt.hilfe ? '<span class="hilfe" id="' + id + '-h">' + esc(opt.hilfe) + '</span>' : '') + '</div>';
  }
  function wahl(pfad, label, werte, opt = {}) {
    const w = get(pfad);
    const name = 'w-' + pfad.replace(/\./g, '-');
    return '<fieldset class="feld ' + (opt.span || 's3') + '"><legend class="label">' + esc(label) + '</legend><div class="segmente">' +
      werte.map(v => '<label class="chip"><input type="radio" name="' + name + '" data-pfad="' + pfad + '" data-neu="1" value="' + esc(v) + '"' +
        (w === v ? ' checked' : '') + '><span class="haken" aria-hidden="true"></span>' + esc(v) + '</label>').join('') + '</div></fieldset>';
  }
  function auswahl(pfad, label, werte, opt = {}) {
    const id = 'f-' + pfad.replace(/\./g, '-'); const w = get(pfad) ?? '';
    return '<div class="feld ' + (opt.span || 's3') + '"><label for="' + id + '"' + (opt.pflicht ? ' class="pflicht"' : '') + '>' + esc(label) + '</label>' +
      '<select id="' + id + '" data-pfad="' + pfad + '" data-neu="1"><option value="">Bitte wählen</option>' +
      werte.map(v => '<option' + (w === v ? ' selected' : '') + '>' + esc(v) + '</option>').join('') + '</select></div>';
  }
  function kopf(eyebrow, titel, text) {
    return '<div class="schritt-kopf"><div class="eyebrow">' + esc(eyebrow) + '</div><h1 id="schritt-titel">' + esc(titel) + '</h1>' + (text ? '<p>' + text + '</p>' : '') + '</div>';
  }
  const sie = (a, b) => (istKunde ? a : b);

  /* ── Schritt-Ansichten ──────────────────────────────── */
  function rVorgang() {
    return kopf('Schritt 1', 'Vorgang & Kostenträger', 'Wer zahlt, wer hat vermittelt – damit Antrag und Fristen sofort richtig laufen.') +
      '<section class="karte"><h2>Vorgang</h2><div class="raster">' +
      feld('felder.datum', 'Datum', { typ: 'date', span: 's2' }) +
      feld('felder.berater', 'Beraten durch', { span: 's2', auto: 'name' }) +
      '<div class="feld s2"><span class="label">Art</span><div class="segmente"><label class="chip"><input type="checkbox" data-pfad="felder.nur_kv" data-neu="1"' + (V.felder.nur_kv ? ' checked' : '') + '><span class="haken" aria-hidden="true"></span>Nur Kostenvoranschlag</label></div></div>' +
      '</div></section>' +
      '<section class="karte"><h2>Kostenträger</h2><div class="raster">' +
      auswahl('kostentraeger.traeger', 'Kostenträger', K.kostentraeger, { span: 's3', pflicht: true }) +
      feld('kostentraeger.aktenzeichen', 'Aktenzeichen / Kundennummer', { span: 's3' }) +
      feld('kostentraeger.ansprechpartner', 'Ansprechpartner beim Kostenträger', { span: 's3' }) +
      feld('kostentraeger.kontakt', 'Telefon / E-Mail Ansprechpartner', { span: 's3' }) +
      auswahl('kostentraeger.vermittelt', 'Vermittelt durch', ['Integrationsamt (Technischer Berater)', 'Rentenversicherung (Reha-Fachberater)', 'Schwerbehindertenvertretung', 'VELA-Gebietsvertreter', 'Arzt / Therapeut', 'Sanitätshaus / Partner', 'Bestandskunde / Empfehlung', 'Website / Google', 'Sonstiges'], { span: 's6' }) +
      '</div></section>';
  }

  function rKunde() {
    const f = V.felder;
    return kopf(sie('Schritt 1', 'Schritt 2'), sie('Ihre Kontaktdaten', 'Kunde & Lieferadresse'),
      sie('Damit wir Sie für die Beratung erreichen und den Stuhl an die richtige Adresse liefern.', '')) +
      '<section class="karte"><h2>Privatadresse</h2><div class="raster">' +
      feld('felder.p_name', 'Vor- und Nachname', { span: 's6', pflicht: true, auto: 'name' }) +
      feld('felder.p_strasse', 'Straße und Hausnummer', { span: 's4', auto: 'street-address' }) +
      feld('felder.p_plz', 'PLZ', { span: 's2', pflicht: true, inputmode: 'numeric', auto: 'postal-code' }) +
      feld('felder.p_stadt', 'Ort', { span: 's3', auto: 'address-level2' }) +
      feld('felder.p_telefon', 'Telefon', { span: 's3', typ: 'tel', auto: 'tel', hilfe: 'Telefon oder E-Mail – eins genügt.' }) +
      feld('felder.l_email', 'E-Mail', { span: 's6', typ: 'email', auto: 'email', hilfe: 'Telefon oder E-Mail – eins genügt.' }) +
      '</div></section>' +
      '<section class="karte"><h2>Lieferung</h2><div class="segmente" style="margin-bottom:16px">' +
      '<label class="chip"><input type="checkbox" data-pfad="felder.lieferung_wie_privat" data-neu="1"' + (f.lieferung_wie_privat ? ' checked' : '') + '><span class="haken" aria-hidden="true"></span>Lieferung an die Privatadresse</label></div>' +
      (f.lieferung_wie_privat ? '' : '<div class="raster folge">' +
        feld('felder.l_firma', 'Firma / Arbeitgeber', { span: 's6', auto: 'organization' }) +
        feld('felder.l_strasse', 'Straße und Hausnummer', { span: 's4' }) +
        feld('felder.l_plz', 'PLZ', { span: 's2', inputmode: 'numeric' }) +
        feld('felder.l_stadt', 'Ort', { span: 's3' }) +
        feld('felder.l_telefon', 'Telefon am Arbeitsplatz', { span: 's3', typ: 'tel' }) + '</div>') +
      '<details style="margin-top:16px"><summary>Fax-Nummern (optional)</summary><div class="raster" style="margin-top:8px">' +
      feld('felder.p_fax', 'Fax privat', { span: 's3', typ: 'tel' }) + feld('felder.l_fax', 'Fax Arbeitsplatz', { span: 's3', typ: 'tel' }) + '</div></details>' +
      '</section>';
  }

  function prozentSumme() {
    const k = ['pc_prozent', 'schreiben_prozent', 'telefon_prozent', 'anders_prozent'].map(x => zahl(V.felder[x]));
    if (k.every(x => x === null)) return null;
    return k.reduce((s, x) => s + (x || 0), 0);
  }
  function rArbeitsplatz() {
    const s = prozentSumme();
    return kopf(sie('Schritt 2', 'Schritt 3'), 'Arbeitsplatz', sie('Wie verbringen Sie einen normalen Arbeitstag?', 'Wofür wird der Stuhl genutzt?')) +
      '<section class="karte"><div class="raster">' +
      feld('felder.beruf', 'Berufsbezeichnung', { span: 's6', auto: 'organization-title' }) +
      '</div></section><section class="karte"><h2>Zeitaufteilung am Tag <span class="hilfe' + (s !== null && s !== 100 ? ' warn' : '') + '" id="prozent-summe" aria-live="polite">' + (s === null ? '' : '– Summe ' + s + ' %' + (s !== 100 ? ' (soll 100 %)' : '')) + '</span></h2><div class="raster">' +
      feld('felder.pc_prozent', 'Computer', { span: 's2', typ: 'number', inputmode: 'numeric', einheit: '%', min: 0, max: 100 }) +
      feld('felder.schreiben_prozent', 'Schreiben', { span: 's2', typ: 'number', inputmode: 'numeric', einheit: '%', min: 0, max: 100 }) +
      feld('felder.telefon_prozent', 'Telefon', { span: 's2', typ: 'number', inputmode: 'numeric', einheit: '%', min: 0, max: 100 }) +
      feld('felder.anders_prozent', 'Anderes', { span: 's2', typ: 'number', inputmode: 'numeric', einheit: '%', min: 0, max: 100 }) +
      feld('felder.anders_text', 'Was genau?', { span: 's4' }) +
      '</div></section>';
  }

  function rZusatzFelder(def) {
    return def.felder.map(fd => {
      const pfad = 'zusatz.werte.' + fd.id;
      let html;
      if (fd.typ === 'jn') html = wahl(pfad, fd.label, ['Ja', 'Nein'], { span: 's3' });
      else if (fd.typ === 'auswahl') html = auswahl(pfad, fd.label, fd.werte, { span: 's3' });
      else if (fd.typ === 'zahl') html = feld(pfad, fd.label, { span: 's3', typ: 'number', inputmode: 'decimal', einheit: fd.einheit, step: '0.5' });
      else html = feld(pfad, fd.label, { span: 's6', typ: fd.typ === 'text' ? 'text' : 'text' });
      if (fd.folge && get(pfad) === fd.folge.wert) {
        html += '<div class="raster folge">' + rZusatzFelder({ felder: fd.folge.felder }) + '</div>';
      }
      return html;
    }).join('');
  }
  function rGesundheit() {
    const f = V.felder;
    const vorschlag = zusatzVorschlaege();
    const zb = K.zusatzboegen;
    return kopf(sie('Schritt 3', 'Schritt 4'), sie('Beschwerden & Besonderheiten', 'Gesundheit & Besonderheiten'),
      sie('Ihre Angaben helfen uns, den Stuhl genau auf Sie abzustimmen. Sie werden verschlüsselt übertragen.', 'Besonderheiten antippen – passende Zusatzfragen klappen auf.')) +
      '<section class="karte"><div class="raster">' +
      feld('felder.beschwerden', sie('Beschreiben Sie kurz Ihre Beschwerden', 'Beschwerden / Diagnose'), { typ: 'textarea', span: 's6' }) +
      feld('felder.klinik_von', 'Klinikaufenthalt von', { typ: 'date', span: 's2' }) +
      feld('felder.klinik_bis', 'Klinikaufenthalt bis', { typ: 'date', span: 's2' }) +
      feld('felder.krank_tage', 'Krankheitstage (Rücken, letztes Jahr)', { typ: 'number', span: 's2', inputmode: 'numeric', min: 0, max: 365 }) +
      wahl('felder.skoliose', 'Diagnostizierte Skoliose?', ['Ja', 'Nein']) +
      wahl('felder.wollallergie', 'Allergisch gegen Wolle?', ['Ja', 'Nein']) +
      (f.skoliose === 'Ja' ? '<div class="raster folge">' + feld('felder.skoliose_grad', 'Skoliose: wie viel Grad?', { typ: 'number', span: 's2', inputmode: 'numeric', einheit: '°', min: 0, max: 180 }) + '</div>' : '') +
      '</div></section>' +
      '<section class="karte"><h2>' + sie('Trifft etwas davon auf Sie zu?', 'Ergänzungsbögen') + '</h2>' +
      (vorschlag.length ? '<div class="hinweis info"><span>Nach den bisherigen Angaben passt: <b>' + vorschlag.map(v => esc(zb[v].titel.replace('Ergänzung ', ''))).join(', ') + '</b></span></div>' : '') +
      '<div class="zusatz-schalter">' + Object.entries(zb).map(([id, d]) =>
        '<label class="chip"><input type="checkbox" data-zusatz="' + id + '"' + (V.zusatz.aktiv.includes(id) ? ' checked aria-controls="zb-' + id + '"' : '') + ' aria-expanded="' + V.zusatz.aktiv.includes(id) + '"><span class="haken" aria-hidden="true"></span>' + esc(d.titel.replace('Ergänzung ', '')) + '</label>').join('') + '</div>' +
      V.zusatz.aktiv.map(id => {
        const d = zb[id]; if (!d) return '';
        return '<div class="zusatz" id="zb-' + id + '"><h3>' + esc(d.titel) + '</h3>' + (d.hinweis && !istKunde ? '<p class="hilfe">' + esc(d.hinweis) + '</p>' : '<p class="hilfe">Bitte so weit wie möglich ausfüllen.</p>') +
          '<div class="raster">' + rZusatzFelder(d) + '</div></div>';
      }).join('') + '</section>';
  }

  const SKIZZE = '<svg viewBox="0 0 200 240" role="img" aria-label="Skizze der Messpunkte A bis H im Sitzen">' +
    '<g stroke="#1a5276" stroke-width="6" stroke-linecap="round" fill="none"><circle cx="88" cy="38" r="14" fill="#1a5276" stroke="none"/><path d="M88 54 L88 120"/><path d="M88 74 L124 96 L124 120"/><path d="M88 120 L134 122"/><path d="M134 122 L134 196"/><path d="M134 196 L152 196"/></g>' +
    '<g stroke="#8899aa" stroke-width="1.5"><line x1="60" y1="196" x2="196" y2="196"/><line x1="60" y1="120" x2="92" y2="120"/><line x1="158" y1="88" x2="196" y2="88"/><line x1="186" y1="88" x2="186" y2="196" stroke-dasharray="3 3"/></g>' +
    '<g font-family="Figtree, Arial" font-size="14" font-weight="800" fill="#c0392b">' +
    '<text data-b="a" x="104" y="116">A</text><text data-b="b" x="140" y="162">B</text><text data-b="c" x="100" y="136">C</text><text data-b="d" x="172" y="150">D</text><text data-b="e" x="66" y="90">E</text><text data-b="f" x="146" y="212">F</text><text data-b="h" x="112" y="86">H</text></g></svg>';

  function rMasse() {
    const f = V.felder, hinweise = [];
    const g = zahl(f.gewicht), k = zahl(f.koerpergroesse);
    if (g && g > 135) hinweise.push('Über 135 kg: Schwerlast-Modell und Ergänzung Schwergewicht prüfen.');
    if (k && k < 140) hinweise.push('Unter 1,40 m: Ergänzung Kleinwuchs ausfüllen.');
    if (k && (k < 80 || k > 230)) hinweise.push('Körpergröße bitte prüfen (' + k + ' cm).');
    const a = zahl(f.mass_a), b = zahl(f.mass_b);
    if (k && a && b && (a + b) > k * 0.7) hinweise.push('A + B wirken im Verhältnis zur Körpergröße hoch – bitte nachmessen.');
    return kopf(sie('Schritt 4', 'Schritt 5'), 'Maße', sie('Bitte im Sitzen messen, ohne Schuhe (außer F). Eine zweite Person hilft.', 'Im Sitzen messen, ohne Schuhe (außer F).')) +
      hinweise.map(h => '<div class="hinweis warn"><span>' + esc(h) + '</span></div>').join('') +
      '<section class="karte"><h2>Person</h2><div class="raster">' +
      feld('felder.alter', 'Alter', { typ: 'number', span: 's2', inputmode: 'numeric', min: 0, max: 120, einheit: 'J.' }) +
      feld('felder.gewicht', 'Gewicht', { typ: 'number', span: 's2', inputmode: 'numeric', min: 0, max: 350, einheit: 'kg', pflicht: true }) +
      feld('felder.koerpergroesse', 'Körpergröße', { typ: 'number', span: 's2', inputmode: 'decimal', min: 0, max: 250, einheit: 'cm', pflicht: true }) +
      wahl('felder.geschlecht', 'Geschlecht', ['Männlich', 'Weiblich', 'Divers'], { span: 's6' }) +
      '</div></section>' +
      '<section class="karte"><h2>Körpermaße</h2><div class="masse"><div class="raster">' +
      [['a', 'A – Hüftgelenk bis Kniegelenk'], ['b', 'B – Kniegelenk bis Boden'], ['c', 'C – Gesäß bis Kniekehle'], ['d', 'D – Boden bis Oberkante Tisch'],
       ['e', 'E – Sitzfläche bis Schulter'], ['h', 'H – Sitzfläche bis Ellenbogen (90°)'], ['f', 'F – Absatzhöhe Schuhe']]
        .map(([x, l]) => feld('felder.mass_' + x, l, { typ: 'number', span: 's3', inputmode: 'decimal', step: '0.5', min: 0, max: 150, einheit: 'cm', massBuchstabe: x, pflicht: ['a', 'b', 'c'].includes(x) })).join('') +
      wahl('felder.lws', 'G – Krümmung der unteren Lendenwirbelsäule', ['flach', 'medium', 'stark gewölbt'], { span: 's6' }) +
      '</div><div class="skizze">' + SKIZZE + '<p>Tippen Sie in ein Maßfeld – der passende Buchstabe wird hervorgehoben.</p></div></div></section>';
  }

  function rUmgebung() {
    const boden = V.felder.boden || [];
    return kopf(sie('Schritt 5', 'Schritt 6'), 'Arbeitsumgebung & Wünsche', '') +
      '<section class="karte"><fieldset><legend>Fußboden am Arbeitsplatz</legend><div class="segmente">' +
      ['Hochfloriger Teppich', 'Teppichfliesen', 'PVC', 'Parkett', 'Kacheln', 'Beton'].map(b =>
        '<label class="chip"><input type="checkbox" data-liste="felder.boden" value="' + esc(b) + '"' + (boden.includes(b) ? ' checked' : '') + '><span class="haken" aria-hidden="true"></span>' + esc(b) + '</label>').join('') +
      '</div></fieldset><div class="raster" style="margin-top:16px">' +
      feld('felder.boden_andere', 'Anderer Bodenbelag', { span: 's3' }) +
      feld('felder.polsterfarbe', 'Gewünschte Polsterfarbe', { span: 's3', hilfe: 'Alle Polsterstoffe mit mindestens 75.000 Scheuertouren.' }) +
      feld('felder.erfahren', sie('Wie haben Sie von uns erfahren?', 'Wie von ERGO-PLUS erfahren?'), { span: 's6' }) +
      (istKunde ? feld('notiz', 'Möchten Sie uns noch etwas mitteilen?', { typ: 'textarea', span: 's6' }) : feld('notiz', 'Interne Notiz (nur Büro)', { typ: 'textarea', span: 's6' })) +
      '</div></section>';
  }

  function rVersorgung() {
    const emp = empfehlungen();
    const l = linie(), g = zahl(V.felder.gewicht);
    let html = kopf('Schritt 7', 'Versorgung konfigurieren', 'Empfehlung ergibt sich aus Maßen und Ergänzungsbögen. Nicht passende Optionen sind gesperrt.') +
      (K.beispielpreise ? '<div class="hinweis warn"><span><b>Beispielkatalog.</b> ' + esc(K.hinweis) + '</span></div>' : '') +
      '<section class="karte"><fieldset><legend>Produktlinie</legend><div class="linien">' +
      [...K.linien].sort((x, y) => emp.has(y.id) - emp.has(x.id)).map(x => '<label class="linie"><input type="radio" name="linie" data-pfad="versorgung.linie" data-neu="1" value="' + x.id + '"' + (V.versorgung.linie === x.id ? ' checked' : '') + '>' +
        (emp.has(x.id) ? '<span class="empf">Empfohlen</span>' : '') + '<span class="t">' + esc(x.name) + '</span><span class="k">' + esc(x.kurz) + '</span></label>').join('') +
      '</div></fieldset></section>';
    if (!l) return html;
    html += '<section class="karte"><fieldset><legend>Modell</legend><div class="optionen">' +
      l.modelle.map(m => {
        const zuSchwer = g && m.max_kg && g > m.max_kg;
        return '<label class="option"><input type="radio" name="modell" data-pfad="versorgung.modell" data-neu="1" value="' + m.id + '"' + (V.versorgung.modell === m.id ? ' checked' : '') + (zuSchwer ? ' disabled' : '') + '>' +
          '<span><span class="t">' + esc(m.name) + '</span><span class="p" style="display:block">Traglast bis ' + m.max_kg + ' kg · ' + eur(m.preis_netto * (1 + K.mwst_standard / 100)) + ' brutto</span>' +
          (zuSchwer ? '<span class="grund" style="display:block">Gewicht ' + g + ' kg liegt über der Traglast</span>' : '') + '</span></label>';
      }).join('') + '</div></fieldset></section>';
    K.optionen.forEach(gr => {
      html += '<section class="karte"><fieldset><legend>' + esc(gr.gruppe) + (gr.auswahl === 'einfach' ? ' <span class="hilfe">(eine Auswahl)</span>' : '') + '</legend><div class="optionen">';
      gr.eintraege.forEach(o => {
        const sperre = optionSperre(o, gr);
        const an = gr.auswahl === 'einfach' ? V.versorgung.einfach[gr.gruppe] === o.id : V.versorgung.optionen.includes(o.id);
        const typ = gr.auswahl === 'einfach' ? 'radio' : 'checkbox';
        html += '<label class="option"><input type="' + typ + '" name="opt-' + esc(gr.gruppe) + '" ' + (gr.auswahl === 'einfach' ? 'data-einfach="' + esc(gr.gruppe) + '"' : 'data-option="1"') +
          ' value="' + o.id + '"' + (an ? ' checked' : '') + (sperre ? ' disabled' : '') + '><span><span class="t">' + esc(o.name) + '</span>' +
          '<span class="p" style="display:block">' + (o.preis_netto ? '+ ' + eur(o.preis_netto * (1 + K.mwst_standard / 100)) + ' brutto' : 'ohne Aufpreis') + '</span>' +
          (sperre ? '<span class="grund" style="display:block">' + esc(sperre) + '</span>' : '') + '</span></label>';
      });
      html += '</div></fieldset></section>';
    });
    return html;
  }

  function rFotos() {
    const labels = ['Sitzposition seitlich', 'Sitzposition frontal', 'Rücken / Haltung', 'Arbeitsplatz', 'Alter Stuhl', 'Sonstiges'];
    return kopf('Schritt 8', 'Fotos', 'Werden komprimiert, verschlüsselt und mit dem Vorgang übertragen. Max. 10 Fotos.') +
      '<section class="karte"><div class="foto-neu">' +
      '<label class="btn primaer klein">Foto aufnehmen<input type="file" accept="image/*" capture="environment" data-foto="1" aria-label="Foto mit Kamera aufnehmen"></label>' +
      '<label class="btn sekundaer klein">Aus Galerie<input type="file" accept="image/*" multiple data-foto="1" aria-label="Fotos aus der Galerie wählen"></label>' +
      '<div class="feld" style="min-width:240px"><label for="foto-label">Beschriftung für nächstes Foto</label><select id="foto-label">' + labels.map(x => '<option>' + x + '</option>').join('') + '</select></div>' +
      '</div>' + (V.fotos.length ? '<div class="foto-raster">' + V.fotos.map(f =>
        '<figure class="foto"><img src="' + f.bild + '" alt="' + esc(f.label) + '"><figcaption class="fl">' + esc(f.label) + '</figcaption><button type="button" class="weg" data-foto-weg="' + f.id + '" aria-label="Foto ' + esc(f.label) + ' entfernen">×</button></figure>').join('') + '</div>'
        : '<p class="hilfe">Noch keine Fotos. Seitlich und frontal in Sitzposition helfen bei Antrag und Montage am meisten.</p>') + '</section>';
  }

  function rAngebot() {
    const s = summen(), p = positionen();
    const m = modell(), f = 1 + K.mwst_standard / 100;
    const de = n => n.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const zeilen = K.leistungen.map(l => {
      const an = V.leistungen.aus[l.id] === undefined ? l.fest : !V.leistungen.aus[l.id];
      const preis = V.leistungen.preis[l.id] ?? '';
      const basis = l.je_km_netto ? (zahl(V.leistungen.km) || 0) * 2 * l.je_km_netto : l.preis_netto;
      const netto = zahl(preis) ?? basis;
      return '<tr><td><label style="display:flex;gap:12px;align-items:center;cursor:pointer"><input type="checkbox" class="an" data-leistung="' + l.id + '"' + (an ? ' checked' : '') + '><span>' + esc(l.name) + '</span></label>' +
        (l.je_km_netto ? '<div class="km"><label for="km">Entfernung einfach</label><input type="text" id="km" inputmode="decimal" data-pfad="leistungen.km" value="' + esc(V.leistungen.km) + '"><span>km × 2 × ' + eur(l.je_km_netto) + '</span></div>' : '') +
        '</td><td class="z"><label class="sr" for="lp-' + l.id + '">Preis netto ' + esc(l.name) + '</label><input type="text" id="lp-' + l.id + '" inputmode="decimal" data-pfad="leistungen.preis.' + l.id + '" placeholder="' + de(basis) + '" value="' + esc(preis) + '"' + (an ? '' : ' disabled') + '></td>' +
        '<td class="z" data-brutto="' + l.id + '">' + (an ? eur(netto * f) : '–') + '</td></tr>';
    }).join('');
    return kopf('Schritt 9', 'Angebot', 'Dienstleistungen sind standardmäßig enthalten. Netto-Preise überschreibbar, Summen brutto.') +
      (K.beispielpreise ? '<div class="hinweis warn"><span><b>Beispielpreise.</b> Vor dem ersten echten Angebot in katalog.json pflegen.</span></div>' : '') +
      '<section class="karte"><h2>Hilfsmittel</h2><table class="posten"><thead><tr><th scope="col">Position</th><th scope="col" class="z">Netto</th><th scope="col" class="z">Brutto</th></tr></thead><tbody>' +
      (m ? p.filter(x => !x.leistung).map(x => '<tr><td>' + esc(x.name) + '</td><td class="z">' + eur(x.netto) + '</td><td class="z">' + eur(x.netto * f) + '</td></tr>').join('') : '<tr><td colspan="3" class="hilfe">Noch kein Modell gewählt (Schritt Versorgung).</td></tr>') +
      '</tbody></table></section>' +
      '<section class="karte"><h2>Dienstleistungen</h2><table class="posten"><thead><tr><th scope="col">Leistung</th><th scope="col" class="z">Netto €</th><th scope="col" class="z">Brutto</th></tr></thead><tbody>' + zeilen + '</tbody>' +
      '<tfoot><tr><td>Summe netto</td><td></td><td class="z" id="sum-netto">' + eur(s.netto) + '</td></tr><tr><td>MwSt ' + K.mwst_standard + ' %</td><td></td><td class="z" id="sum-mwst">' + eur(s.mwst) + '</td></tr>' +
      '<tr class="gesamt"><td>Gesamt brutto</td><td></td><td class="z" id="sum-brutto">' + eur(s.brutto) + '</td></tr></tfoot></table></section>';
  }

  function rEinwilligung() {
    const e = V.einwilligung;
    const punkt = (k, t, d, pflicht) => '<label class="einwilligung"><input type="checkbox" data-pfad="einwilligung.' + k + '" data-neu="1"' + (e[k] ? ' checked' : '') + (pflicht ? ' aria-required="true"' : '') + '><span><span class="t' + (pflicht ? ' pflicht' : '') + '">' + t + '</span><span class="d" style="display:block">' + d + '</span></span></label>';
    if (!V.unterschrift.name) V.unterschrift.name = V.felder.p_name || '';
    return kopf(sie('Schritt 6', 'Schritt 10'), 'Einwilligung & Unterschrift', '') +
      '<div class="hinweis info"><span><b>Textentwurf.</b> Formulierungen vor dem Einsatz von Datenschutzbeauftragtem oder Anwalt prüfen lassen.</span></div>' +
      '<section class="karte"><h2>Einwilligungen</h2>' +
      punkt('datenschutz', 'Verarbeitung meiner Gesundheitsdaten', 'Ich willige ein, dass ERGO-PLUS Seating Concepts GmbH meine Angaben einschließlich Gesundheitsdaten (Art. 9 Abs. 2 lit. a DSGVO) zur Beratung, Angebotserstellung, Antragstellung und Versorgung verarbeitet. Widerruf jederzeit für die Zukunft möglich.', true) +
      punkt('schweigepflicht', 'Weitergabe an Kostenträger und Reha-Partner', 'ERGO-PLUS darf die für den Antrag nötigen Angaben an den Kostenträger und den abrechnenden Reha-Partner übermitteln und Rückfragen beantworten.', false) +
      punkt('fotos', 'Fotos für Antrag und Fertigung', 'Die Fotos dürfen für Antrag, Fertigung und Einstellung des Stuhls genutzt werden – nicht für Werbung.', false) +
      punkt('nachsorge', 'Erinnerung an Wartung und Neuversorgung', 'ERGO-PLUS darf mich per E-Mail oder Telefon an Service-Termine und an eine mögliche Neuversorgung erinnern. Abmeldung jederzeit.', false) +
      '</section><section class="karte"><h2>Unterschrift</h2><div class="raster" style="margin-bottom:16px">' +
      feld('unterschrift.name', 'Name in Druckschrift', { span: 's2' }) + feld('unterschrift.ort', 'Ort', { span: 's2' }) + feld('unterschrift.datum', 'Datum', { span: 's2', typ: 'date' }) +
      '</div><div class="unterschrift"><canvas id="unterschrift" aria-label="Unterschriftsfeld – mit Finger oder Stift unterschreiben" role="img"></canvas><span class="x" aria-hidden="true">×</span><span class="linie-u" aria-hidden="true"></span></div>' +
      '<div class="unterschrift-aktionen"><span class="hilfe">' + (V.unterschrift.bild ? 'Unterschrift erfasst.' : 'Mit Finger oder Stift unterschreiben.') + '</span><button type="button" class="btn sekundaer klein" id="unterschrift-weg">Löschen</button></div></section>';
  }

  function alleFehlenden() {
    return SCHRITTE.flatMap((s, i) => s.pruefen().map(t => ({ t, i, s })));
  }
  function zfKopf(titel, schrittId) {
    const i = SCHRITTE.findIndex(s => s.id === schrittId);
    return '<h2>' + esc(titel) + (i >= 0 ? '<button type="button" class="link-btn" data-gehe="' + i + '" aria-label="' + esc(titel) + ' ändern">Ändern</button>' : '') + '</h2>';
  }
  function zfZeilen(paare) {
    return '<dl>' + paare.filter(([, w]) => w !== '' && w != null && !(Array.isArray(w) && !w.length)).map(([k, w]) => '<dt>' + esc(k) + '</dt><dd>' + esc(Array.isArray(w) ? w.join(', ') : w) + '</dd>').join('') + '</dl>';
  }
  function rAbschluss() {
    if (gesendet) {
      const symbol = gesendetOk
        ? '<div class="erfolg-symbol"><svg viewBox="0 0 24 24" fill="none" stroke="#0d6350" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg></div>'
        : '<div class="erfolg-symbol wartet"><svg viewBox="0 0 24 24" fill="none" stroke="#8a5606" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></div>';
      const titel = gesendetOk ? sie('Vielen Dank – Ihr Bogen ist angekommen', 'Freigegeben und angekommen') : 'Gespeichert – wird gesendet';
      return '<section class="karte freigabe">' + symbol +
        '<h1 id="schritt-titel" class="erfolg-titel">' + titel + '</h1>' +
        '<p id="erfolg-text">' + esc(gesendet) + '</p>' +
        '<div class="segmente" style="justify-content:center"><button type="button" class="btn sekundaer" id="btn-drucken">Zusammenfassung drucken</button>' +
        (istKunde ? '' : '<button type="button" class="btn primaer" id="btn-neu2">Neuer Vorgang</button>') + '</div></section>';
    }
    const fehlend = alleFehlenden();
    const hart = fehlend.filter(x => HART.includes(x.t));
    const f = V.felder, s = summen(), l = linie(), m = modell();
    const zusatz = V.zusatz.aktiv.map(id => {
      const d = K.zusatzboegen[id];
      const werte = (function sammeln(felder) { return felder.flatMap(fd => [[fd.label, V.zusatz.werte[fd.id] ? V.zusatz.werte[fd.id] + (fd.einheit ? ' ' + fd.einheit : '') : ''], ...(fd.folge ? sammeln(fd.folge.felder) : [])]); })(d.felder);
      return '<div class="zf-block">' + zfKopf(d.titel, 'gesundheit') + zfZeilen(werte) + '</div>';
    }).join('');
    return kopf(sie('Letzter Schritt', 'Schritt 11'), sie('Prüfen & absenden', 'Prüfen & freigeben'),
      sie('Ihr Bogen wird verschlüsselt an ERGO-PLUS übertragen. Ohne Netz wird er automatisch nachgesendet.', 'Nach der Freigabe: verschlüsselter Versand, Angebot und Antragsunterlagen entstehen im Büro automatisch.')) +
      (fehlend.length ? '<section class="karte"><h2>Noch offen</h2><ul class="pruefliste">' + fehlend.map(x =>
        '<li><span>' + esc(x.t) + '</span><button type="button" class="link-btn" data-gehe="' + x.i + '">' + esc(x.s.titel) + ' öffnen</button></li>').join('') + '</ul></section>' : '<div class="hinweis ok"><span><b>Alles vollständig.</b></span></div>') +
      '<section class="karte">' +
      '<div class="zf-block">' + zfKopf('Kunde', 'kunde') + zfZeilen([['Name', f.p_name], ['Adresse', [f.p_strasse, [f.p_plz, f.p_stadt].filter(Boolean).join(' ')].filter(Boolean).join(', ')], ['Telefon', f.p_telefon], ['E-Mail', f.l_email], ['Beruf', f.beruf],
        ['Lieferung', f.lieferung_wie_privat ? 'an Privatadresse' : [f.l_firma, f.l_strasse, [f.l_plz, f.l_stadt].filter(Boolean).join(' ')].filter(Boolean).join(', ')]]) + '</div>' +
      (istKunde ? '' : '<div class="zf-block">' + zfKopf('Kostenträger', 'vorgang') + zfZeilen([['Kostenträger', V.kostentraeger.traeger], ['Aktenzeichen', V.kostentraeger.aktenzeichen], ['Vermittelt durch', V.kostentraeger.vermittelt]]) + '</div>') +
      '<div class="zf-block">' + zfKopf('Gesundheit & Maße', 'masse') + zfZeilen([['Beschwerden', f.beschwerden], ['Skoliose', f.skoliose ? f.skoliose + (f.skoliose_grad ? ' (' + f.skoliose_grad + '°)' : '') : ''], ['Wollallergie', f.wollallergie],
        ['Gewicht / Größe', [f.gewicht && f.gewicht + ' kg', f.koerpergroesse && f.koerpergroesse + ' cm'].filter(Boolean).join(' / ')],
        ['Maße A–H (cm)', ['a', 'b', 'c', 'd', 'e', 'f', 'h'].map(x => f['mass_' + x] ? x.toUpperCase() + ' ' + f['mass_' + x] : '').filter(Boolean).join(' · ')], ['LWS', f.lws]]) + '</div>' +
      zusatz +
      (istKunde ? '' : '<div class="zf-block">' + zfKopf('Versorgung', 'versorgung') + zfZeilen([['Linie', l && l.name], ['Modell', m && m.name], ['Optionen', gewaehlteOptionen().map(o => o.name)], ['Fotos', V.fotos.length ? V.fotos.length + ' Stück' : '']]) + '</div>' +
        '<div class="zf-block">' + zfKopf('Angebot', 'angebot') + zfZeilen([['Summe netto', eur(s.netto)], ['Gesamt brutto', eur(s.brutto)]]) + '</div>') +
      '</section>' +
      '<section class="karte freigabe">' +
      (hart.length ? '<p class="fehlertext">Zum Absenden fehlt noch: ' + esc(hart.map(x => x.t).join(', ')) + '</p>' : '') +
      '<button type="button" class="btn primaer gross" id="btn-freigeben"' + (hart.length ? ' disabled' : '') + '>' + sie('Verschlüsselt absenden', 'Freigeben & senden') + '</button>' +
      '<button type="button" class="link-btn" id="btn-drucken">Zusammenfassung drucken</button></section>';
  }

  /* ── Rendering & Ereignisse ─────────────────────────── */
  function renderListe() {
    const ol = $('#schritt-liste');
    ol.innerHTML = SCHRITTE.map((s, i) => {
      const fehlt = s.pruefen().length > 0, besucht = i < V.schritt;
      const cls = besucht ? (fehlt ? 'fehlt' : 'fertig') : '';
      return '<li class="' + cls + '"' + (i === V.schritt ? ' aria-current="step"' : '') + '><button type="button" data-gehe="' + i + '"><span class="nr" aria-hidden="true">' + (besucht && !fehlt ? '✓' : i + 1) + '</span>' + esc(s.titel) +
        (besucht && fehlt ? '<span class="hilfe" style="margin-left:auto">offen</span>' : '') + '</button></li>';
    }).join('');
    $('#fortschritt').style.width = ((V.schritt + 1) / SCHRITTE.length * 100) + '%';
    $('#btn-zurueck').disabled = V.schritt === 0;
    const letzter = V.schritt === SCHRITTE.length - 1;
    $('#btn-weiter').style.visibility = letzter ? 'hidden' : '';
    const ab = SCHRITTE.findIndex(s => s.id === 'versorgung');
    $('#leiste-info').textContent = 'Schritt ' + (V.schritt + 1) + ' von ' + SCHRITTE.length +
      (!istKunde && ab >= 0 && V.schritt >= ab && modell() ? ' · Gesamt ' + eur(summen().brutto) + ' brutto' : '');
    // Nach der Freigabe ist der Vorgang abgeschlossen: nichts mehr ändern, nur drucken oder neu.
    $('.leiste').hidden = !!gesendet;
    ol.querySelectorAll('button').forEach(b => { b.disabled = !!gesendet; });
    $('#vorgang-nr').textContent = V.vorgang;
  }

  function render(fokusErhalten) {
    let fokus = null;
    if (fokusErhalten && document.activeElement) {
      const a = document.activeElement;
      fokus = { pfad: a.dataset.pfad, wert: a.value, zusatz: a.dataset.zusatz, liste: a.dataset.liste, einfach: a.dataset.einfach, option: a.dataset.option, leistung: a.dataset.leistung };
    }
    const scrollY = window.scrollY;
    $('#schritt-buehne').innerHTML = SCHRITTE[V.schritt].render();
    renderListe();
    if (SCHRITTE[V.schritt].id === 'einwilligung') unterschriftAktivieren();
    if (fokus) {
      let sel = null;
      if (fokus.zusatz) sel = '[data-zusatz="' + fokus.zusatz + '"]';
      else if (fokus.leistung) sel = '[data-leistung="' + fokus.leistung + '"]';
      else if (fokus.liste || fokus.einfach || fokus.option || (fokus.pfad && document.querySelector('input[type=radio][data-pfad="' + fokus.pfad + '"]'))) {
        sel = '[value="' + CSS.escape(fokus.wert) + '"]' + (fokus.pfad ? '[data-pfad="' + fokus.pfad + '"]' : '');
      } else if (fokus.pfad) sel = '[data-pfad="' + fokus.pfad + '"]';
      const el = sel && $(sel);
      if (el) el.focus({ preventScroll: true });
      window.scrollTo(0, scrollY);
    }
  }

  function gehe(i) {
    if (gesendet) return;
    V.schritt = Math.max(0, Math.min(SCHRITTE.length - 1, i));
    render(false); sichern();
    window.scrollTo({ top: 0 });
    $('#inhalt').focus({ preventScroll: true });
  }

  let sicherTimer;
  function sichern() {
    clearTimeout(sicherTimer);
    sicherTimer = setTimeout(() => { ErgoSpeicher.entwurfSichern(V).catch(() => {}); }, 300);
  }

  function nachAenderung(el) {
    const id = SCHRITTE[V.schritt].id;
    if (id === 'arbeitsplatz') { const s = prozentSumme(); const e = $('#prozent-summe'); if (e) { e.textContent = s === null ? '' : '– Summe ' + s + ' %' + (s !== 100 ? ' (soll 100 %)' : ''); e.classList.toggle('warn', s !== null && s !== 100); } }
    if (id === 'angebot') {
      const s = summen();
      $('#sum-netto').textContent = eur(s.netto); $('#sum-mwst').textContent = eur(s.mwst); $('#sum-brutto').textContent = eur(s.brutto);
      const f = 1 + K.mwst_standard / 100;
      K.leistungen.forEach(l => {
        const basis = l.je_km_netto ? (zahl(V.leistungen.km) || 0) * 2 * l.je_km_netto : l.preis_netto;
        const i = $('#lp-' + l.id); if (i && l.je_km_netto) i.placeholder = basis.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const z = document.querySelector('[data-brutto="' + l.id + '"]');
        const an = V.leistungen.aus[l.id] === undefined ? l.fest : !V.leistungen.aus[l.id];
        if (z) z.textContent = an ? eur((zahl(V.leistungen.preis[l.id]) ?? basis) * f) : '–';
      });
    }
    renderListe();
  }

  document.addEventListener('input', e => {
    const el = e.target;
    if (el.dataset.pfad && el.type !== 'radio' && el.type !== 'checkbox') { set(el.dataset.pfad, el.value); sichern(); nachAenderung(el); }
  });
  document.addEventListener('focusin', e => {
    const b = e.target.dataset && e.target.dataset.mass;
    document.querySelectorAll('.skizze text').forEach(t => t.setAttribute('fill', t.dataset.b === b ? '#117a65' : '#c0392b'));
  });
  document.addEventListener('change', async e => {
    const el = e.target;
    if (el.dataset.foto) return fotosHinzu(el);
    if (el.dataset.zusatz) {
      const a = V.zusatz.aktiv, id = el.dataset.zusatz;
      V.zusatz.aktiv = el.checked ? [...new Set([...a, id])] : a.filter(x => x !== id);
      sichern(); render(true); if (el.checked) melde(K.zusatzboegen[id].titel + ' geöffnet'); return;
    }
    if (el.dataset.liste) {
      const liste = new Set(get(el.dataset.liste) || []); el.checked ? liste.add(el.value) : liste.delete(el.value);
      set(el.dataset.liste, [...liste]); sichern(); renderListe(); return;
    }
    if (el.dataset.einfach) { V.versorgung.einfach[el.dataset.einfach] = el.value; bereinigeOptionen(); sichern(); render(true); return; }
    if (el.dataset.option) {
      const o = new Set(V.versorgung.optionen); el.checked ? o.add(el.value) : o.delete(el.value);
      V.versorgung.optionen = [...o]; bereinigeOptionen(); sichern(); render(true); return;
    }
    if (el.dataset.leistung) { V.leistungen.aus[el.dataset.leistung] = !el.checked; sichern(); render(true); return; }
    if (el.dataset.pfad && (el.type === 'radio' || el.type === 'checkbox' || el.tagName === 'SELECT')) {
      set(el.dataset.pfad, el.type === 'checkbox' ? el.checked : el.value);
      if (el.dataset.pfad === 'versorgung.linie') { V.versorgung.modell = ''; const l = linie(); if (l && l.modelle.length === 1) V.versorgung.modell = l.modelle[0].id; if (l && l.zusatzbogen && !V.zusatz.aktiv.includes(l.zusatzbogen)) V.zusatz.aktiv.push(l.zusatzbogen); }
      bereinigeOptionen(); sichern();
      if (el.dataset.neu) render(true); else nachAenderung(el);
      return;
    }
    // Werte, die Hinweise/Empfehlungen auslösen: nach dem Verlassen des Feldes neu zeichnen,
    // erst wenn der Fokus beim nächsten Feld angekommen ist – so geht er nicht verloren.
    if (['felder.gewicht', 'felder.koerpergroesse', 'felder.mass_a', 'felder.mass_b'].includes(el.dataset.pfad)) {
      setTimeout(() => render(true), 0);
    }
  });
  document.addEventListener('click', async e => {
    const t = e.target.closest('button'); if (!t) return;
    if (t.dataset.gehe !== undefined) return gehe(+t.dataset.gehe);
    if (t.dataset.fotoWeg) {
      const pos = V.fotos.findIndex(f => f.id === t.dataset.fotoWeg); const weg = V.fotos[pos];
      V.fotos.splice(pos, 1); sichern(); render(false);
      return melde('Foto „' + weg.label + '“ entfernt', { label: 'Rückgängig', fn: () => { V.fotos.splice(pos, 0, weg); sichern(); render(false); } });
    }
    switch (t.id) {
      case 'btn-weiter': return gehe(V.schritt + 1);
      case 'btn-zurueck': return gehe(V.schritt - 1);
      case 'btn-freigeben': return freigeben(t);
      case 'btn-drucken': return drucken();
      case 'btn-neu': case 'btn-neu2': return neu();
      case 'unterschrift-weg': V.unterschrift.bild = ''; sichern(); render(false); return;
      case 'sync-chip': ErgoVersand.senden(); return syncInfo();
      case 'meldung-aktion': if (meldungAktion) { const fn = meldungAktion; meldungAktion = null; $('#meldung').classList.remove('zeigen'); fn(); } return;
    }
  });

  async function neu() {
    const offen = !gesendet && (V.felder.p_name || V.fotos.length);
    if (offen && !window.confirm('Aktuellen Vorgang verwerfen? Nicht freigegebene Angaben gehen verloren.')) return;
    gesendet = false; gesendetOk = false; V = neuerVorgang();
    if (params.get('vorgang')) { V.vorgang = vorgangsNr(); history.replaceState(null, '', location.pathname + (istKunde ? '?modus=kunde' : '')); }
    await ErgoSpeicher.entwurfLoeschen(); render(false); melde('Neuer Vorgang ' + V.vorgang);
  }

  /* ── Fotos ──────────────────────────────────────────── */
  function verkleinern(datei) {
    // FileReader statt blob:-URL – die Content-Security-Policy der Seite erlaubt nur data:-Bilder.
    return new Promise((resolve, reject) => {
      const leser = new FileReader();
      leser.onerror = () => reject(new Error('Bild unlesbar'));
      leser.onload = () => {
        const img = new Image();
        img.onload = () => {
          const max = 1600, f = Math.min(1, max / Math.max(img.width, img.height));
          const c = document.createElement('canvas'); c.width = Math.round(img.width * f); c.height = Math.round(img.height * f);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          resolve(c.toDataURL('image/jpeg', 0.8));
        };
        img.onerror = () => reject(new Error('Bild unlesbar'));
        img.src = leser.result;
      };
      leser.readAsDataURL(datei);
    });
  }
  async function fotosHinzu(input) {
    const label = ($('#foto-label') || {}).value || 'Foto';
    const dateien = [...input.files].slice(0, Math.max(0, 10 - V.fotos.length));
    for (const d of dateien) {
      try { V.fotos.push({ id: uuid(), label, bild: await verkleinern(d) }); } catch (e) { melde('Ein Bild konnte nicht gelesen werden'); }
    }
    if (input.files.length > dateien.length) melde('Maximal 10 Fotos');
    sichern(); render(false);
  }

  /* ── Unterschrift ───────────────────────────────────── */
  function unterschriftAktivieren() {
    const c = $('#unterschrift'); if (!c) return;
    const dpr = window.devicePixelRatio || 1, r = c.getBoundingClientRect();
    c.width = r.width * dpr; c.height = r.height * dpr;
    const ctx = c.getContext('2d'); ctx.scale(dpr, dpr); ctx.lineWidth = 2.6; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#1a2a3a';
    if (V.unterschrift.bild) { const i = new Image(); i.onload = () => ctx.drawImage(i, 0, 0, r.width, r.height); i.src = V.unterschrift.bild; }
    let zeichnet = false, letzte = null;
    const pos = ev => { const b = c.getBoundingClientRect(); return [ev.clientX - b.left, ev.clientY - b.top]; };
    c.addEventListener('pointerdown', ev => { zeichnet = true; letzte = pos(ev); c.setPointerCapture(ev.pointerId); ev.preventDefault(); });
    c.addEventListener('pointermove', ev => {
      if (!zeichnet) return; const p = pos(ev);
      ctx.beginPath(); ctx.moveTo(letzte[0], letzte[1]); ctx.lineTo(p[0], p[1]); ctx.stroke(); letzte = p;
    });
    const ende = () => {
      if (!zeichnet) return; zeichnet = false;
      V.unterschrift.bild = c.toDataURL('image/png'); sichern(); renderListe();
      const h = $('.unterschrift-aktionen .hilfe'); if (h) h.textContent = 'Unterschrift erfasst.';
    };
    c.addEventListener('pointerup', ende); c.addEventListener('pointercancel', ende); c.addEventListener('pointerleave', ende);
  }

  /* ── Freigabe ───────────────────────────────────────── */
  function nutzlast() {
    const l = linie(), m = modell(), s = summen();
    return {
      format: 'ergo-vorgang/1', id: V.id, vorgang: V.vorgang, modus: MODUS, angelegt: V.angelegt, freigegeben: new Date().toISOString(),
      pose: Object.assign({}, V.felder),
      zusatz: { aktiv: V.zusatz.aktiv, werte: V.zusatz.werte },
      kostentraeger: V.kostentraeger,
      versorgung: istKunde ? null : {
        linie: l ? { id: l.id, name: l.name } : null, modell: m || null, optionen: gewaehlteOptionen().map(o => ({ id: o.id, name: o.name, preis_netto: o.preis_netto })),
        empfehlung: [...empfehlungen()]
      },
      angebot: istKunde ? null : { positionen: positionen(), summen: s, mwst: K.mwst_standard, beispielpreise: !!K.beispielpreise, katalog_stand: K.stand },
      fotos: V.fotos.map(f => ({ label: f.label, bild: f.bild })),
      einwilligung: V.einwilligung, unterschrift: V.unterschrift, notiz: V.notiz,
      offen: alleFehlenden().map(x => x.t),
      geraet: { ua: navigator.userAgent, sprache: navigator.language }
    };
  }
  async function freigeben(btn) {
    btn.disabled = true; btn.textContent = 'Wird verschlüsselt …';
    try {
      const umschlag = await ErgoKrypto.verschluesseln(nutzlast(), { id: V.id, vorgang: V.vorgang, modus: MODUS });
      await ErgoSpeicher.einreihen(umschlag);
      await ErgoSpeicher.entwurfLoeschen();
      const druckKopie = V;
      await ErgoVersand.senden();
      const z = await ErgoVersand.zustand();
      const angekommen = (await ErgoSpeicher.protokoll()).some(p => p.id === umschlag.id);
      gesendetOk = angekommen;
      gesendet = angekommen
        ? sie('Vorgang ' + V.vorgang + ' ist sicher bei ERGO-PLUS angekommen. Wir melden uns bei Ihnen.', 'Vorgang ' + V.vorgang + ' ist im Büro angekommen. Angebot und Antragsunterlagen werden vorbereitet.')
        : sie('Gerade ist keine Verbindung da. Ihr Bogen ist verschlüsselt gespeichert und wird automatisch gesendet, sobald das Gerät wieder online ist. Bitte die Seite bis dahin nicht über die Browser-Einstellungen löschen.',
              'Kein Netz – Vorgang ' + V.vorgang + ' liegt verschlüsselt in der Warteschlange (' + z.offen + ') und geht automatisch raus, sobald Netz da ist.');
      V = druckKopie; render(false);
    } catch (e) {
      btn.disabled = false; btn.textContent = sie('Verschlüsselt absenden', 'Freigeben & senden');
      if (String(e.message) === 'kein-schluessel') melde('Verschlüsselung nicht eingerichtet – Büro informieren (Schlüssel fehlt).');
      else melde('Freigabe fehlgeschlagen: ' + e.message);
    }
  }

  /* ── Versandstatus ──────────────────────────────────── */
  function syncAnzeige(z) {
    if (gesendet && !gesendetOk && !z.offen && !z.sendet) {
      gesendetOk = true;
      gesendet = sie('Ihr Bogen ist jetzt sicher bei ERGO-PLUS angekommen. Wir melden uns bei Ihnen.', 'Vorgang ' + V.vorgang + ' ist nachträglich im Büro angekommen.');
      if (SCHRITTE[V.schritt].id === 'abschluss') render(false);
    }
    const chip = $('#sync-chip'), txt = $('#sync-text');
    if (z.sendet) { chip.dataset.zustand = 'sendet'; txt.textContent = 'Sendet …'; }
    else if (z.offen) { chip.dataset.zustand = z.online ? 'fehler' : 'wartet'; txt.textContent = z.offen + (z.offen === 1 ? ' Vorgang wartet' : ' Vorgänge warten'); }
    else { chip.dataset.zustand = 'ok'; txt.textContent = z.online ? 'Alles übertragen' : 'Offline – bereit'; }
    chip.setAttribute('aria-label', 'Übertragungsstatus: ' + txt.textContent + (z.fehler ? '. ' + z.fehler : ''));
  }
  async function syncInfo() {
    const z = await ErgoVersand.zustand();
    melde(z.offen ? (z.fehler || 'Wird gesendet, sobald Netz da ist') : 'Keine offenen Vorgänge');
  }

  /* ── Druck ──────────────────────────────────────────── */
  function drucken() {
    const f = V.felder, l = linie(), m = modell(), s = summen();
    const zeile = (k, w) => (w ? '<tr><td>' + esc(k) + '</td><td>' + esc(w) + '</td></tr>' : '');
    $('#druck').innerHTML = '<h1>ERGO-PLUS · POSE-Bogen ' + esc(V.vorgang) + '</h1><p>' + esc(f.datum) + '</p>' +
      '<h2>Kunde</h2><table>' + zeile('Name', f.p_name) + zeile('Adresse', [f.p_strasse, f.p_plz, f.p_stadt].filter(Boolean).join(' ')) + zeile('Telefon', f.p_telefon) + zeile('E-Mail', f.l_email) + zeile('Beruf', f.beruf) + '</table>' +
      '<h2>Gesundheit</h2><table>' + zeile('Beschwerden', f.beschwerden) + zeile('Skoliose', f.skoliose && f.skoliose + ' ' + (f.skoliose_grad || '')) + zeile('Wollallergie', f.wollallergie) + '</table>' +
      '<h2>Maße</h2><table>' + zeile('Gewicht', f.gewicht && f.gewicht + ' kg') + zeile('Körpergröße', f.koerpergroesse && f.koerpergroesse + ' cm') +
      ['a', 'b', 'c', 'd', 'e', 'f', 'h'].map(x => zeile('Maß ' + x.toUpperCase(), f['mass_' + x] && f['mass_' + x] + ' cm')).join('') + zeile('LWS', f.lws) + '</table>' +
      V.zusatz.aktiv.map(id => { const d = K.zusatzboegen[id]; return '<h2>' + esc(d.titel) + '</h2><table>' + d.felder.map(fd => zeile(fd.label, V.zusatz.werte[fd.id])).join('') + '</table>'; }).join('') +
      (istKunde ? '' : '<h2>Versorgung</h2><table>' + zeile('Linie', l && l.name) + zeile('Modell', m && m.name) + zeile('Optionen', gewaehlteOptionen().map(o => o.name).join(', ')) + zeile('Gesamt brutto', eur(s.brutto)) + '</table>') +
      (V.unterschrift.bild ? '<h2>Unterschrift</h2><img class="u" src="' + V.unterschrift.bild + '" alt=""><p>' + esc(V.unterschrift.name) + ', ' + esc(V.unterschrift.ort) + ' ' + esc(V.unterschrift.datum) + '</p>' : '');
    window.print();
  }

  /* ── Start ──────────────────────────────────────────── */
  async function start() {
    if (istKunde) { $('#modus-chip').textContent = 'Vorab-Bogen'; document.title = 'POSE-Bogen – Vorab ausfüllen | ERGO-PLUS'; $('#btn-neu').hidden = true; }
    try { K = await (await fetch('katalog.json', { cache: 'no-cache' })).json(); }
    catch (e) { const c = await caches.match('katalog.json'); K = c ? await c.json() : null; }
    if (!K) { $('#schritt-buehne').innerHTML = '<div class="hinweis fehler"><span>Katalog konnte nicht geladen werden. Bitte einmal mit Netz öffnen.</span></div>'; return; }
    let entwurf = null;
    try { entwurf = await ErgoSpeicher.entwurfLaden(); } catch (e) { /* privater Modus */ }
    V = entwurf && entwurf.modus === MODUS && (!params.get('vorgang') || entwurf.vorgang === params.get('vorgang')) ? entwurf : neuerVorgang();
    if (V.schritt >= SCHRITTE.length) V.schritt = 0;
    render(false);
    if (entwurf && entwurf === V && (V.felder.p_name || V.schritt > 0)) melde('Entwurf ' + V.vorgang + ' wiederhergestellt');
    ErgoVersand.beobachten(syncAnzeige);
    ErgoVersand.senden();
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
  }
  start();
})();
