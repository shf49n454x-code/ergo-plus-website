#!/usr/bin/env node
/**
 * Site-Audit für ergo-plus.de
 *
 * Prüft alle HTML-Seiten auf Barrierefreiheit (axe-core), Ladeverhalten
 * (LCP/CLS/Transfergröße) und strukturelle Fehler (tote Links, fehlende
 * Assets, undefinierte CSS-Variablen, uneinheitliche Telefonnummern).
 *
 * Aufruf:
 *   node tools/audit/audit.js            # alles
 *   node tools/audit/audit.js --a11y     # nur Barrierefreiheit
 *   node tools/audit/audit.js --perf     # nur Ladeverhalten
 *   node tools/audit/audit.js --static   # nur strukturelle Prüfung (kein Browser)
 *   node tools/audit/audit.js --json     # Maschinenausgabe für CI
 *   node tools/audit/audit.js --out b.json  # Bericht zusätzlich in Datei
 *
 * Beendet sich mit Code 1, sobald eine Schwelle gerissen wird.
 * Diese Schwellen sind bewusst dort gesetzt, wo der Stand am 05.09.2026
 * lag: sie sollen Rückschritte melden, nicht Fortschritt einfordern.
 */
const fs = require('fs');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '../..');
const PORT = 8079;

const BUDGET = {
  a11yViolations: 0,      // axe: keine Verstöße, egal welcher Schweregrad
  lcpMs: 2500,            // Core Web Vitals "gut"
  cls: 0.1,               // Core Web Vitals "gut"
  pageKb: { 'index.html': 400, 'blog/index.html': 600, _default: 350 },
};

const args = process.argv.slice(2);
const only = (f) => args.includes(f);
const runAll = !only('--a11y') && !only('--perf') && !only('--static');
const asJson = only('--json');

const htmlFiles = () => {
  const out = [];
  for (const f of fs.readdirSync(ROOT)) if (f.endsWith('.html')) out.push(f);
  const blog = path.join(ROOT, 'blog');
  if (fs.existsSync(blog))
    for (const f of fs.readdirSync(blog)) if (f.endsWith('.html')) out.push('blog/' + f);
  return out.sort();
};

/* ── Strukturprüfung: braucht keinen Browser ─────────────────────────── */
function staticChecks(files) {
  const issues = [];
  const telTargets = new Set();

  for (const f of files) {
    const s = fs.readFileSync(path.join(ROOT, f), 'utf8');

    for (const m of s.matchAll(/href="(\/[^"#?]*)"/g)) {
      let p = m[1].replace(/^\//, '');
      if (p.endsWith('/')) p += 'index.html';
      if (p && !fs.existsSync(path.join(ROOT, p)))
        issues.push({ file: f, type: 'toter-link', detail: m[1] });
    }

    const assets = [...s.matchAll(/src="([^":]+)"/g)].map((m) => m[1]);
    for (const m of s.matchAll(/srcset="([^"]+)"/g))
      for (const cand of m[1].split(',')) assets.push(cand.trim().split(' ')[0]);
    for (const u of assets) {
      if (!u) continue;
      const p = u.startsWith('/')
        ? path.join(ROOT, u.slice(1))
        : path.resolve(ROOT, path.dirname(f), u);
      if (!fs.existsSync(p)) issues.push({ file: f, type: 'fehlendes-asset', detail: u });
    }

    const used = new Set([...s.matchAll(/var\((--[a-z0-9-]+)\)/g)].map((m) => m[1]));
    const defined = new Set([...s.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]));
    for (const v of used)
      if (!defined.has(v)) issues.push({ file: f, type: 'undefinierte-css-variable', detail: v });

    for (const m of s.matchAll(/href="tel:([+0-9]+)"/g)) telTargets.add(m[1]);

    // Google Fonts sollen selbst gehostet bleiben (Datenschutz + Ladeverhalten).
    // Der Datenschutztext darf die Domain natürlich weiterhin erwähnen.
    if (/<link[^>]+fonts\.(googleapis|gstatic)\.com/.test(s))
      issues.push({ file: f, type: 'externe-schriftart', detail: 'Google Fonts wieder eingebunden' });
  }

  // Zwei Karten mit demselben Titelbild fallen sofort auf, besonders wenn
  // sie im Raster nebeneinander oder untereinander landen. Das Raster ist
  // 3-, 2- oder 1-spaltig (Breakpoints 960px / 600px), deshalb reicht es
  // nicht, sie in der Quelltextreihenfolge auseinanderzuziehen.
  const uebersicht = path.join(ROOT, 'blog/index.html');
  if (fs.existsSync(uebersicht)) {
    const s = fs.readFileSync(uebersicht, 'utf8');
    const bilder = [...s.matchAll(/<a href="[^"]+" class="card">[\s\S]*?src="\/assets\/img\/([^"]+?)(?:-800w)?\.webp"/g)]
      .map((m) => m[1]);
    const zaehl = {};
    bilder.forEach((b, i) => (zaehl[b] = zaehl[b] || []).push(i));
    for (const [b, pos] of Object.entries(zaehl)) {
      if (pos.length < 2) continue;
      issues.push({ file: 'blog/index.html', type: 'doppeltes-titelbild',
        detail: `${b} auf Karte ${pos.map((p) => p + 1).join(' und ')}` });
    }
  }

  if (telTargets.size > 1)
    issues.push({
      file: '(mehrere)',
      type: 'uneinheitliche-telefonnummer',
      detail: [...telTargets].join(' vs. '),
    });

  return issues;
}

/* ── Browserprüfungen ────────────────────────────────────────────────── */
function serve() {
  return new Promise((resolve) => {
    const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
      '.webp': 'image/webp', '.png': 'image/png', '.svg': 'image/svg+xml',
      '.woff2': 'font/woff2', '.ico': 'image/x-icon', '.txt': 'text/plain', '.xml': 'application/xml' };
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p.endsWith('/')) p += 'index.html';
      const file = path.join(ROOT, p);
      if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        res.writeHead(404); return res.end('not found');
      }
      res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    srv.listen(PORT, () => resolve(srv));
  });
}

function loadPlaywright() {
  for (const p of ['/opt/node22/lib/node_modules/playwright', 'playwright']) {
    try { return require(p); } catch {}
  }
  return null;
}

async function browserChecks(files, want) {
  const pw = loadPlaywright();
  if (!pw) return { skipped: 'Playwright nicht gefunden — Browserprüfungen übersprungen' };

  let axeSrc = null;
  for (const p of [path.join(ROOT, 'node_modules/axe-core/axe.min.js'), '/tmp/a11y/node_modules/axe-core/axe.min.js']) {
    if (fs.existsSync(p)) { axeSrc = fs.readFileSync(p, 'utf8'); break; }
  }

  const exe = fs.existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined;
  const browser = await pw.chromium.launch(exe ? { executablePath: exe } : {});
  const srv = await serve();
  const a11y = {}, perf = {};

  for (const f of files) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    let bytes = 0;
    if (want.perf) page.on('response', async (r) => {
      try { bytes += (await r.body()).length; } catch {}
    });
    try {
      await page.goto(`http://localhost:${PORT}/${f}`, { waitUntil: 'load', timeout: 30000 });
      if (want.perf) {
        await page.waitForTimeout(900);
        const m = await page.evaluate(() => new Promise((res) => {
          let lcp = 0, cls = 0;
          new PerformanceObserver((l) => { for (const e of l.getEntries()) lcp = e.startTime; })
            .observe({ type: 'largest-contentful-paint', buffered: true });
          new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) cls += e.value; })
            .observe({ type: 'layout-shift', buffered: true });
          setTimeout(() => res({ lcp: Math.round(lcp), cls: +cls.toFixed(4) }), 350);
        }));
        perf[f] = { ...m, kb: Math.round(bytes / 1024) };
      }
      if (want.a11y && axeSrc) {
        await page.addScriptTag({ content: axeSrc });
        a11y[f] = await page.evaluate(async () => {
          const r = await axe.run(document, { resultTypes: ['violations'] });
          return r.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length,
            beispiel: (v.nodes[0] && v.nodes[0].html || '').slice(0, 110) }));
        });
      }
    } catch (e) {
      (want.a11y ? a11y : perf)[f] = [{ id: 'ladefehler', impact: 'critical', n: 1, beispiel: e.message }];
    }
    await ctx.close();
  }
  await browser.close();
  srv.close();
  return { a11y, perf, axeMissing: want.a11y && !axeSrc };
}

/* ── Auswertung ──────────────────────────────────────────────────────── */
(async () => {
  const files = htmlFiles();
  const want = { a11y: runAll || only('--a11y'), perf: runAll || only('--perf') };
  const report = { geprueft: files.length, zeitpunkt: new Date().toISOString() };
  const fails = [];

  if (runAll || only('--static')) {
    report.struktur = staticChecks(files);
    for (const i of report.struktur) fails.push(`${i.type}: ${i.file} (${i.detail})`);
  }

  if (want.a11y || want.perf) {
    const r = await browserChecks(files, want);
    if (r.skipped) report.hinweis = r.skipped;
    else {
      if (r.axeMissing) report.hinweis = 'axe-core nicht installiert (npm i -D axe-core) — Barrierefreiheit ungeprüft';
      if (want.a11y && !r.axeMissing) {
        report.barrierefreiheit = Object.fromEntries(Object.entries(r.a11y).filter(([, v]) => v.length));
        for (const [f, v] of Object.entries(report.barrierefreiheit))
          for (const x of v) fails.push(`a11y ${x.id} (${x.impact}, ${x.n}x): ${f}`);
      }
      if (want.perf) {
        report.ladeverhalten = r.perf;
        for (const [f, m] of Object.entries(r.perf)) {
          const budget = BUDGET.pageKb[f] ?? BUDGET.pageKb._default;
          if (m.lcp > BUDGET.lcpMs) fails.push(`LCP ${m.lcp}ms > ${BUDGET.lcpMs}ms: ${f}`);
          if (m.cls > BUDGET.cls) fails.push(`CLS ${m.cls} > ${BUDGET.cls}: ${f}`);
          if (m.kb > budget) fails.push(`Seitengewicht ${m.kb}KB > ${budget}KB: ${f}`);
        }
      }
    }
  }

  report.probleme = fails;

  const outIdx = args.indexOf('--out');
  if (outIdx !== -1 && args[outIdx + 1]) {
    fs.writeFileSync(args[outIdx + 1], JSON.stringify(report, null, 1));
  }

  if (asJson) {
    console.log(JSON.stringify(report, null, 1));
  } else {
    console.log(`\nSite-Audit — ${report.geprueft} Seiten geprüft`);
    if (report.hinweis) console.log(`Hinweis: ${report.hinweis}`);
    if (report.ladeverhalten) {
      const rows = Object.entries(report.ladeverhalten)
        .sort((a, b) => b[1].kb - a[1].kb).slice(0, 5);
      console.log('\nSchwerste Seiten:');
      for (const [f, m] of rows) console.log(`  ${String(m.kb).padStart(5)} KB  LCP ${String(m.lcp).padStart(5)} ms  CLS ${m.cls}  ${f}`);
    }
    if (!fails.length) console.log('\n✓ Keine Befunde. Alle Schwellen eingehalten.\n');
    else {
      console.log(`\n✗ ${fails.length} Befund(e):`);
      for (const x of fails) console.log('  - ' + x);
      console.log('');
    }
  }
  process.exit(fails.length ? 1 : 0);
})();
