/* Service Worker: App-Hülle offline verfügbar halten.
 * Eingaben und Warteschlange liegen in IndexedDB, nicht hier.
 * Nach Änderungen an Dateien VERSION hochzählen, sonst sehen Tablets den alten Stand. */
const VERSION = 'konfigurator-v2';
const HUELLE = [
  './', './index.html', './app.css', './app.js', './krypto.js', './speicher.js',
  './katalog.json', './oeffentlicher-schluessel.json', './manifest.webmanifest',
  '/assets/fonts/fonts.css',
  '/assets/fonts/figtree-latin-600-normal.woff2', '/assets/fonts/figtree-latin-700-normal.woff2',
  '/assets/fonts/figtree-latin-800-normal.woff2', '/assets/fonts/noto-sans-latin-400-normal.woff2',
  '/assets/fonts/noto-sans-latin-600-normal.woff2', '/assets/fonts/noto-sans-latin-700-normal.woff2',
  '/logo-ergoplus.png', '/favicon.svg', '/apple-touch-icon.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c =>
    Promise.all(HUELLE.map(u => c.add(new Request(u, { cache: 'reload' })).catch(() => null)))
  ).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION && k.startsWith('konfigurator-')).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api/')) return; // Versand nie aus dem Cache
  // Katalog und Schlüssel: Netz zuerst (aktuelle Preise), sonst Cache.
  const netzZuerst = /katalog\.json$|oeffentlicher-schluessel\.json$/.test(url.pathname) || e.request.mode === 'navigate';
  if (netzZuerst) {
    e.respondWith(fetch(e.request).then(r => {
      if (r.ok) { const k = r.clone(); caches.open(VERSION).then(c => c.put(e.request, k)); }
      return r;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || caches.match('./index.html'))));
    return;
  }
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
