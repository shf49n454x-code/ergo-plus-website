/* Lokaler Speicher (IndexedDB) und Versand-Warteschlange.
 *
 * entwurf       – der gerade bearbeitete Vorgang (Klartext, nur auf diesem Gerät)
 * warteschlange – freigegebene, bereits VERSCHLÜSSELTE Vorgänge, die noch nicht beim Server sind
 * protokoll     – was wann erfolgreich übertragen wurde (ohne Inhalte)
 *
 * Kein Netz? Dann bleibt der Umschlag in der Warteschlange und wird gesendet,
 * sobald wieder Verbindung besteht – beim Wechsel auf online, beim Öffnen der
 * App und alle 30 Sekunden. Der Server erkennt Wiederholungen an der ID,
 * doppelt ankommen kann also nichts.
 */
(function () {
  'use strict';
  const DB_NAME = 'ergo-konfigurator';
  const ENDPUNKT = '/api/eingang.php';
  let dbPromise = null;

  function db() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const d = req.result;
        d.createObjectStore('entwurf');
        d.createObjectStore('warteschlange', { keyPath: 'id' });
        d.createObjectStore('protokoll', { keyPath: 'id' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return dbPromise;
  }

  async function tx(store, mode, fn) {
    const d = await db();
    return new Promise((resolve, reject) => {
      const t = d.transaction(store, mode);
      const s = t.objectStore(store);
      let ergebnis;
      Promise.resolve(fn(s)).then(r => { ergebnis = r; });
      t.oncomplete = () => resolve(ergebnis && ergebnis.result !== undefined ? ergebnis.result : ergebnis);
      t.onerror = () => reject(t.error);
      t.onabort = () => reject(t.error);
    });
  }

  const Speicher = {
    async entwurfLaden() { return tx('entwurf', 'readonly', s => s.get('aktuell')); },
    async entwurfSichern(daten) { return tx('entwurf', 'readwrite', s => { s.put(daten, 'aktuell'); }); },
    async entwurfLoeschen() { return tx('entwurf', 'readwrite', s => { s.delete('aktuell'); }); },
    async einreihen(umschlag) { return tx('warteschlange', 'readwrite', s => { s.put(umschlag); }); },
    async warteschlange() { return tx('warteschlange', 'readonly', s => s.getAll()); },
    async protokoll() { return tx('protokoll', 'readonly', s => s.getAll()); }
  };

  /* ── Versand ─────────────────────────────────────────── */
  let laeuft = false;
  const hoerer = new Set();
  let letzterFehler = null;

  async function zustand() {
    const offen = await Speicher.warteschlange();
    return { offen: offen.length, sendet: laeuft, fehler: letzterFehler, online: navigator.onLine };
  }
  async function melden() { const z = await zustand(); hoerer.forEach(h => h(z)); }

  async function senden() {
    if (laeuft) return;
    const offen = await Speicher.warteschlange();
    if (!offen.length) { letzterFehler = null; return melden(); }
    if (!navigator.onLine) return melden();
    laeuft = true; await melden();
    for (const umschlag of offen) {
      try {
        const antwort = await fetch(ENDPUNKT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(umschlag),
          cache: 'no-store'
        });
        const json = await antwort.json().catch(() => ({}));
        if (antwort.ok && json.ok) {
          await tx('warteschlange', 'readwrite', s => { s.delete(umschlag.id); });
          await tx('protokoll', 'readwrite', s => {
            s.put({ id: umschlag.id, vorgang: umschlag.vorgang, modus: umschlag.modus, gesendet: new Date().toISOString() });
          });
          letzterFehler = null;
        } else if (antwort.status >= 400 && antwort.status < 500 && antwort.status !== 429) {
          letzterFehler = json.meldung || ('Server lehnt ab (' + antwort.status + ')');
        } else {
          letzterFehler = 'Server nicht erreichbar – neuer Versuch folgt';
        }
      } catch (e) {
        letzterFehler = 'Kein Netz – wird automatisch nachgesendet';
      }
    }
    laeuft = false;
    await melden();
  }

  window.addEventListener('online', senden);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) senden(); });
  setInterval(senden, 30000);

  window.ErgoSpeicher = Speicher;
  window.ErgoVersand = {
    senden, zustand,
    beobachten(fn) { hoerer.add(fn); zustand().then(fn); }
  };
})();
