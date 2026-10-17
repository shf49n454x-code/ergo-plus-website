/* Ende-zu-Ende-Verschlüsselung für Vorgänge.
 *
 * Hybrid: pro Vorgang ein frischer AES-256-GCM-Schlüssel verschlüsselt die
 * Daten, dieser Schlüssel wird mit dem öffentlichen RSA-OAEP-Schlüssel
 * (3072 bit, SHA-256) von ERGO-PLUS eingepackt. Entpacken kann nur, wer den
 * privaten Schlüssel hat – der liegt ausschließlich im Büro
 * (tools/konfigurator/buero.py), nie auf dem Webserver, nie auf dem Tablet.
 *
 * Folge: Server, Tablet-Warteschlange und Transportweg sehen nur Chiffretext.
 */
(function () {
  'use strict';
  const FORMAT = 'ergo-umschlag/1';

  function b64(buf) {
    const bytes = new Uint8Array(buf);
    let s = '';
    for (let i = 0; i < bytes.length; i += 0x8000) {
      s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    }
    return btoa(s);
  }

  let schluesselCache = null;

  async function oeffentlicherSchluessel() {
    if (schluesselCache) return schluesselCache;
    const antwort = await fetch('oeffentlicher-schluessel.json', { cache: 'no-cache' })
      .catch(() => caches.match('oeffentlicher-schluessel.json'));
    if (!antwort || !antwort.ok) throw new Error('kein-schluessel');
    const jwk = await antwort.json();
    if (!jwk || jwk.kty !== 'RSA' || !jwk.n) throw new Error('kein-schluessel');
    const key = await crypto.subtle.importKey(
      'jwk', { kty: 'RSA', n: jwk.n, e: jwk.e, alg: 'RSA-OAEP-256', ext: true },
      { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['wrapKey']);
    schluesselCache = { key, kid: jwk.kid || 'unbekannt' };
    return schluesselCache;
  }

  async function verschluesseln(objekt, meta) {
    const { key: rsa, kid } = await oeffentlicherSchluessel();
    const aes = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt']);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const klartext = new TextEncoder().encode(JSON.stringify(objekt));
    const aad = new TextEncoder().encode(meta.id);
    const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv, additionalData: aad }, aes, klartext);
    const wrapped = await crypto.subtle.wrapKey('raw', aes, rsa, { name: 'RSA-OAEP' });
    return {
      format: FORMAT,
      alg: 'RSA-OAEP-256+A256GCM',
      kid,
      id: meta.id,
      vorgang: meta.vorgang,
      modus: meta.modus,
      erstellt: new Date().toISOString(),
      schluessel: b64(wrapped),
      iv: b64(iv),
      daten: b64(ct)
    };
  }

  window.ErgoKrypto = { verschluesseln, oeffentlicherSchluessel, FORMAT };
})();
